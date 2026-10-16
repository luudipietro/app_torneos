from tests.conftest import add_scorer, make_tournament

ORO = {"name": "Copa de Oro", "positions": [1, 2], "extra": []}


def setup(client, auth, n_teams, n_groups, **rules):
    tid, teams = make_tournament(client, auth, n_teams, **rules)
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": n_groups, "seed": 5}, headers=auth).json()
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    return tid, teams, st, ms


def play_groups(client, auth, ms):
    for m in ms:  # gana siempre el local: resultado determinístico
        r = client.put(f"/api/matches/{m['id']}/result", json={"home_goals": 1, "away_goals": 0}, headers=auth)
        assert r.status_code == 200, r.text


def knock(client, auth, tid, cups=(ORO,), **kw):
    return client.post(f"/api/tournaments/{tid}/stages/knockout", json={"cups": list(cups), **kw}, headers=auth)


def matches(client, auth, stage_id):
    ms = client.get(f"/api/stages/{stage_id}/matches", headers=auth).json()
    return sorted(ms, key=lambda m: (m["is_third_place"], m["round"], m["id"]))


def win(client, auth, m, home=True, pens=None):
    """Cierra un partido de llave: gana el local (o el visitante)."""
    body = {"home_goals": 2, "away_goals": 1} if home else {"home_goals": 0, "away_goals": 1}
    if pens:
        body = {"home_goals": 1, "away_goals": 1, "home_pens": pens[0], "away_pens": pens[1]}
    return client.put(f"/api/matches/{m['id']}/result", json=body, headers=auth)


def test_sugerencias(client, auth):
    tid, *_ = setup(client, auth, 12, 3)
    labels = [p["label"] for p in client.get(f"/api/tournaments/{tid}/knockout/plans", headers=auth).json()]
    assert "Los 2 primeros de cada grupo" in labels
    assert "Los 2 primeros de cada grupo + los 2 mejores 3º" in labels  # 6 clasificados -> 8


def test_preview_y_no_se_puede_crear_con_grupos_sin_cerrar(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    body = {"cups": [ORO]}
    p = client.post(f"/api/tournaments/{tid}/knockout/preview", json=body, headers=auth).json()
    assert p["unplayed"] == 12 and p["cups"][0]["size"] == 4 and len(p["cups"][0]["entrants"]) == 4
    r = knock(client, auth, tid)
    assert r.status_code == 409 and "12" in r.json()["detail"]


def test_llave_de_4_con_tercer_puesto_y_avance(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    r = knock(client, auth, tid)
    assert r.status_code == 201
    (stage,) = r.json()
    assert stage["type"] == "knockout" and stage["config"]["size"] == 4
    km = matches(client, auth, stage["id"])
    semis, final, third = km[:2], km[2], km[3]
    assert [m["round"] for m in km] == [1, 1, 2, 2] and third["is_third_place"]
    assert all(m["home_team_id"] and m["away_team_id"] and m["is_knockout"] for m in semis)
    assert final["home_team_id"] is None and third["home_team_id"] is None
    # los cuatro son distintos y cada semifinal mezcla grupos distintos
    four = {t for m in semis for t in (m["home_team_id"], m["away_team_id"])}
    assert len(four) == 4
    win(client, auth, semis[0], home=True)
    win(client, auth, semis[1], home=False)
    km = matches(client, auth, stage["id"])
    final, third = km[2], km[3]
    assert final["home_team_id"] == semis[0]["home_team_id"] and final["away_team_id"] == semis[1]["away_team_id"]
    assert third["home_team_id"] == semis[0]["away_team_id"] and third["away_team_id"] == semis[1]["home_team_id"]
    assert win(client, auth, final).status_code == 200
    assert win(client, auth, third).status_code == 200


def test_empate_en_llave_exige_penales(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    (stage,) = knock(client, auth, tid).json()
    semis = matches(client, auth, stage["id"])[:2]
    url = f"/api/matches/{semis[0]['id']}/result"
    assert client.put(url, json={"home_goals": 1, "away_goals": 1}, headers=auth).status_code == 422
    assert client.put(url, json={"home_goals": 1, "away_goals": 1, "home_pens": 3, "away_pens": 3}, headers=auth).status_code == 422
    r = win(client, auth, semis[0], pens=(3, 5))
    assert r.status_code == 200 and (r.json()["home_pens"], r.json()["away_pens"]) == (3, 5)
    final = matches(client, auth, stage["id"])[2]
    assert final["home_team_id"] == semis[0]["away_team_id"]  # ganó el visitante por penales


def test_partido_sin_equipos_definidos_no_se_cierra(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    (stage,) = knock(client, auth, tid).json()
    final = matches(client, auth, stage["id"])[2]
    assert client.post(f"/api/matches/{final['id']}/finish", headers=auth).status_code == 409


def test_reabrir_semifinal_vacia_el_lugar_en_la_final(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    (stage,) = knock(client, auth, tid).json()
    semis = matches(client, auth, stage["id"])[:2]
    win(client, auth, semis[0])
    assert matches(client, auth, stage["id"])[2]["home_team_id"] == semis[0]["home_team_id"]
    assert client.post(f"/api/matches/{semis[0]['id']}/reopen", headers=auth).status_code == 200
    final = matches(client, auth, stage["id"])[2]
    assert final["home_team_id"] is None
    # si la final ya empezó, no se puede cambiar la semifinal
    win(client, auth, semis[0])
    win(client, auth, semis[1])
    final = matches(client, auth, stage["id"])[2]
    assert win(client, auth, final).status_code == 200  # la final queda cerrada
    assert client.post(f"/api/matches/{semis[0]['id']}/reopen", headers=auth).status_code == 409


def test_copa_de_oro_y_plata(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    plata = {"name": "Copa de Plata", "positions": [3, 4], "extra": []}
    r = knock(client, auth, tid, cups=[ORO, plata])
    assert r.status_code == 201
    oro_stage, plata_stage = r.json()
    assert [s["name"] for s in (oro_stage, plata_stage)] == ["Copa de Oro", "Copa de Plata"]
    in_oro = {t for m in matches(client, auth, oro_stage["id"]) for t in (m["home_team_id"], m["away_team_id"]) if t}
    in_plata = {t for m in matches(client, auth, plata_stage["id"]) for t in (m["home_team_id"], m["away_team_id"]) if t}
    assert len(in_oro) == len(in_plata) == 4 and in_oro.isdisjoint(in_plata)
    assert in_oro | in_plata == set(teams)  # nadie queda afuera
    assert client.get(f"/api/tournaments/{tid}/stages", headers=auth).json()[-1]["name"] == "Copa de Plata"


def test_mejores_terceros_y_byes(client, auth):
    # 9 equipos, 3 grupos de 3: los 2 primeros + el mejor 3º = 7 clasificados -> llave de 8 con 1 bye
    tid, teams, st, ms = setup(client, auth, 9, 3)
    play_groups(client, auth, ms)
    cup = {"name": "Copa de Oro", "positions": [1, 2], "extra": [{"position": 3, "count": 1}]}
    prev = client.post(f"/api/tournaments/{tid}/knockout/preview", json={"cups": [cup]}, headers=auth).json()["cups"][0]
    assert (prev["size"], prev["byes"], len(prev["entrants"])) == (8, 1, 7)
    assert [e["position"] for e in prev["entrants"]].count(3) == 1
    (stage,) = knock(client, auth, tid, cups=[cup]).json()
    km = matches(client, auth, stage["id"])
    assert len([m for m in km if not m["is_third_place"]]) == 6  # n-1 partidos
    r2 = [m for m in km if m["round"] == 2 and not m["is_third_place"]]
    # el cabeza de serie con bye ya está en su partido de la segunda ronda
    assert sum(1 for m in r2 for t in (m["home_team_id"], m["away_team_id"]) if t) == 1


def test_validaciones_y_permisos(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    url = f"/api/tournaments/{tid}/stages/knockout"
    assert client.post(url, json={"cups": []}, headers=auth).status_code == 422
    assert knock(client, auth, tid, cups=[{"name": "X", "positions": [], "extra": []}]).status_code == 422
    assert knock(client, auth, tid, cups=[{"name": "X", "positions": [1], "extra": [{"position": 2, "count": 9}]}]).status_code == 422
    assert knock(client, auth, tid, cups=[ORO, {**ORO}]).status_code == 422  # nombre repetido
    sc = add_scorer(client, auth, tid, [ms[0]["id"]])
    assert knock(client, sc, tid).status_code == 403
    assert client.get(f"/api/tournaments/{tid}/knockout/plans", headers=sc).status_code == 403
    assert knock(client, auth, tid).status_code == 201
    assert knock(client, auth, tid).status_code == 409  # ya hay llaves


def test_borrar_llaves_para_rehacer(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    (stage,) = knock(client, auth, tid).json()
    # no se puede borrar la fase de grupos con llaves armadas
    assert client.delete(f"/api/stages/{st['id']}", headers=auth).status_code == 409
    assert client.delete(f"/api/stages/{stage['id']}", headers=auth).status_code == 204
    plata = {"name": "Copa de Plata", "positions": [3, 4], "extra": []}
    assert knock(client, auth, tid, cups=[ORO, plata]).status_code == 201


def test_planillero_asignado_cierra_partido_de_llave(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    play_groups(client, auth, ms)
    (stage,) = knock(client, auth, tid).json()
    semi = matches(client, auth, stage["id"])[0]
    sc = add_scorer(client, auth, tid, [semi["id"]])
    r = client.put(f"/api/matches/{semi['id']}/result", json={"home_goals": 3, "away_goals": 0}, headers=sc)
    assert r.status_code == 200
    final = matches(client, auth, stage["id"])[2]
    assert final["home_team_id"] == semi["home_team_id"]
