from tests.conftest import add_scorer, make_tournament, register

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def setup(client, auth, **rules):
    """4 equipos en 1 grupo (3 partidos c/u). Devuelve datos del primer equipo y sus partidos."""
    tid, teams = make_tournament(client, auth, 4, **rules)
    players = {}
    for t in teams:
        for i in (1, 2):
            r = client.post(
                f"/api/teams/{t}/players",
                json={"name": f"J{t}-{i}", "dni": f"{t}0000{i}0", "number": i},
                headers=auth,
            )
            players.setdefault(t, []).append(r.json()["id"])
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 1, "seed": 1}, headers=auth).json()
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    team = ms[0]["home_team_id"]
    mine = sorted((m for m in ms if team in (m["home_team_id"], m["away_team_id"])), key=lambda m: m["round"])
    return tid, team, players, mine


def lineup(client, auth, mid):
    return client.get(f"/api/matches/{mid}/lineup", headers=auth).json()


def side_of(lu, team):
    return lu["home"] if lu["home"]["team_id"] == team else lu["away"]


def row_of(lu, team, player):
    return next(x for x in side_of(lu, team)["players"] if x["player_id"] == player)


def play(client, auth, mid, player, card=None):
    """Marca presente, registra tarjeta (opcional) y cierra el partido."""
    assert client.put(f"/api/matches/{mid}/lineup/{player}", headers=auth).status_code == 200
    if card:
        r = client.post(f"/api/matches/{mid}/events", json={"player_id": player, "type": card}, headers=auth)
        assert r.status_code == 201, r.text
    assert client.post(f"/api/matches/{mid}/finish", headers=auth).status_code == 200


def test_marcar_presentes_y_verificador(client, auth):
    tid, team, pl, ms = setup(client, auth)
    p, mid = pl[team][0], ms[0]["id"]
    lu = client.put(f"/api/matches/{mid}/lineup/{p}", headers=auth).json()
    row = row_of(lu, team, p)
    assert row["present"] and row["verified_by"] == "Org" and row["verified_at"]
    assert side_of(lu, team)["present_count"] == 1
    assert client.put(f"/api/matches/{mid}/lineup/{p}", headers=auth).status_code == 200  # idempotente
    lu = client.delete(f"/api/matches/{mid}/lineup/{p}", headers=auth).json()
    assert side_of(lu, team)["present_count"] == 0


def test_roja_suspende_el_proximo_partido_y_luego_vuelve(client, auth):
    tid, team, pl, ms = setup(client, auth)
    p = pl[team][0]
    play(client, auth, ms[0]["id"], p, card="red")
    sus = client.get(f"/api/tournaments/{tid}/suspensions", headers=auth).json()
    assert [(s["player_id"], s["reason"], s["remaining"]) for s in sus] == [(p, "red", 1)]
    r = client.put(f"/api/matches/{ms[1]['id']}/lineup/{p}", headers=auth)
    assert r.status_code == 409 and "suspendido" in r.json()["detail"]
    row = row_of(lineup(client, auth, ms[1]["id"]), team, p)
    assert row["suspension"] == {"remaining": 1, "reason": "red"}
    # el compañero sí puede jugar; cumplida la fecha, vuelve
    play(client, auth, ms[1]["id"], pl[team][1])
    assert client.get(f"/api/tournaments/{tid}/suspensions", headers=auth).json() == []
    assert client.put(f"/api/matches/{ms[2]['id']}/lineup/{p}", headers=auth).status_code == 200


def test_acumulacion_de_amarillas_configurable(client, auth):
    tid, team, pl, ms = setup(client, auth, yellows_for_suspension=2)
    p = pl[team][0]
    play(client, auth, ms[0]["id"], p, card="yellow")
    row = row_of(lineup(client, auth, ms[1]["id"]), team, p)
    assert row["yellows"] == 1 and row["suspension"] is None
    play(client, auth, ms[1]["id"], p, card="yellow")
    r = client.put(f"/api/matches/{ms[2]['id']}/lineup/{p}", headers=auth)
    assert r.status_code == 409 and "amarillas" in r.json()["detail"]


def test_jugador_no_habilitado(client, auth):
    tid, team, pl, ms = setup(client, auth)
    p = pl[team][0]
    assert client.patch(f"/api/players/{p}", json={"enabled": False}, headers=auth).json()["enabled"] is False
    r = client.put(f"/api/matches/{ms[0]['id']}/lineup/{p}", headers=auth)
    assert r.status_code == 409 and "habilitado" in r.json()["detail"]


def test_eventos_solo_para_presentes(client, auth):
    tid, team, pl, ms = setup(client, auth)
    mid = ms[0]["id"]

    def ev(p):
        return client.post(f"/api/matches/{mid}/events", json={"player_id": p, "type": "goal"}, headers=auth)

    client.put(f"/api/matches/{mid}/lineup/{pl[team][0]}", headers=auth)
    assert ev(pl[team][1]).status_code == 422  # no está en la lista de su equipo
    assert ev(pl[team][0]).status_code == 201
    # no se puede sacar de la lista a quien tiene incidencias
    assert client.delete(f"/api/matches/{mid}/lineup/{pl[team][0]}", headers=auth).status_code == 409


def test_require_lineup_obligatorio(client, auth):
    tid, team, pl, ms = setup(client, auth, require_lineup=True)
    r = client.post(f"/api/matches/{ms[0]['id']}/events", json={"player_id": pl[team][0], "type": "goal"}, headers=auth)
    assert r.status_code == 422


def test_alta_en_cancha_y_permisos_de_planillero(client, auth):
    tid, team, pl, ms = setup(client, auth)
    mid = ms[0]["id"]
    sc = add_scorer(client, auth, tid, [mid])
    body = {"team_id": team, "name": "Refuerzo", "dni": "40111222", "number": 11}
    lu = client.post(f"/api/matches/{mid}/lineup/new-player", json=body, headers=sc)
    assert lu.status_code == 201
    row = next(x for x in side_of(lu.json(), team)["players"] if x["name"] == "Refuerzo")
    assert row["present"] and row["enabled"]
    assert client.post(f"/api/matches/{mid}/lineup/new-player", json=body, headers=sc).status_code == 409  # DNI repetido
    # el planillero marca presentes pero no puede tocar un partido cerrado
    assert client.put(f"/api/matches/{mid}/lineup/{pl[team][0]}", headers=sc).status_code == 200
    client.post(f"/api/matches/{mid}/finish", headers=auth)
    assert client.put(f"/api/matches/{mid}/lineup/{pl[team][1]}", headers=sc).status_code == 403


def test_alta_en_cancha_deshabilitada_por_reglamento(client, auth):
    tid, team, pl, ms = setup(client, auth, allow_onsite_players=False)
    sc = add_scorer(client, auth, tid, [ms[0]["id"]])
    body = {"team_id": team, "name": "X", "dni": "40111222"}
    url = f"/api/matches/{ms[0]['id']}/lineup/new-player"
    assert client.post(url, json=body, headers=sc).status_code == 403
    assert client.post(url, json=body, headers=auth).status_code == 201


def test_foto_de_jugador(client, auth):
    tid, team, pl, ms = setup(client, auth)
    p = pl[team][0]
    r = client.post(f"/api/players/{p}/photo", files={"file": ("f.png", PNG, "image/png")}, headers=auth)
    assert r.status_code == 200 and r.json()["photo_url"] == f"/api/players/{p}/photo"
    assert client.get(f"/api/players/{p}/photo", headers=auth).content == PNG
    assert client.get(f"/api/players/{p}/photo").status_code == 401
    assert client.get(f"/api/players/{p}/photo", headers=register(client, "ext@test.com")).status_code == 404
    assert row_of(lineup(client, auth, ms[0]["id"]), team, p)["has_photo"]
    bad = client.post(f"/api/players/{p}/photo", files={"file": ("f.png", b"nada", "image/png")}, headers=auth)
    assert bad.status_code == 415
