import json

from tests.conftest import add_scorer, make_tournament, register


def setup(client, auth, n_teams=4, n_groups=1):
    tid, teams = make_tournament(client, auth, n_teams)
    pl = {}
    for t in teams:
        for i in (1, 2):
            r = client.post(f"/api/teams/{t}/players", json={"name": f"J{t}-{i}", "dni": f"{t}0000{i}0", "number": i}, headers=auth)
            pl.setdefault(t, []).append(r.json()["id"])
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": n_groups, "seed": 1}, headers=auth).json()
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    return tid, teams, pl, st, ms


def ev(client, h, mid, player, kind, minute=None):
    r = client.post(f"/api/matches/{mid}/events", json={"player_id": player, "type": kind, "minute": minute}, headers=h)
    assert r.status_code == 201, r.text


def play_stats_match(client, auth, ms, pl):
    """Un partido con goles, penal, gol en contra y las tres tarjetas. Local 3 - Visitante 1."""
    m = ms[0]
    mid, h, a = m["id"], m["home_team_id"], m["away_team_id"]
    ev(client, auth, mid, pl[h][0], "goal", 10)
    ev(client, auth, mid, pl[h][0], "penalty_goal", 20)
    ev(client, auth, mid, pl[a][0], "goal", 30)
    ev(client, auth, mid, pl[a][1], "own_goal", 40)  # en contra del visitante: suma al local
    ev(client, auth, mid, pl[a][0], "yellow", 50)
    ev(client, auth, mid, pl[h][1], "red", 60)
    ev(client, auth, mid, pl[a][1], "second_yellow", 70)
    assert client.post(f"/api/matches/{mid}/finish", headers=auth).status_code == 200
    return m


def test_estadisticas(client, auth):
    tid, teams, pl, st, ms = setup(client, auth)
    m = play_stats_match(client, auth, ms, pl)
    h, a = m["home_team_id"], m["away_team_id"]
    other = next(x for x in ms if {x["home_team_id"], x["away_team_id"]}.isdisjoint({h, a}))
    client.put(f"/api/matches/{other['id']}/result", json={"home_goals": 0, "away_goals": 0}, headers=auth)

    s = client.get(f"/api/tournaments/{tid}/stats", headers=auth).json()
    assert (s["matches_played"], s["total_goals"], s["goals_per_match"]) == (2, 4, 2.0)

    # goleadores: el gol en contra no suma al jugador
    assert [(r["player_id"], r["goals"], r["penalties"], r["rank"]) for r in s["scorers"]] == [(pl[h][0], 2, 1, 1), (pl[a][0], 1, 0, 2)]

    # tarjetas: la doble amarilla cuenta como roja y no como amarilla; primero las rojas
    cards = {c["player_id"]: (c["yellow"], c["red"]) for c in s["cards"]}
    assert cards == {pl[h][1]: (0, 1), pl[a][0]: (1, 0), pl[a][1]: (0, 1)}
    assert s["cards"][-1]["player_id"] == pl[a][0]

    # valla menos vencida: los dos del 0-0 empatan en el 1°; el local recibió 1 y el visitante 3
    d = {r["team_id"]: r for r in s["defense"]}
    assert [d[other["home_team_id"]]["rank"], d[other["away_team_id"]]["rank"]] == [1, 1]
    assert (d[h]["goals_against"], d[h]["average"], d[h]["clean_sheets"], d[h]["rank"]) == (1, 1.0, 0, 3)
    assert (d[a]["goals_against"], d[a]["rank"]) == (3, 4)

    # fair play: amarilla = 1, roja = 3
    fp = {r["team_id"]: r["points"] for r in s["fair_play"]}
    assert fp[h] == 3 and fp[a] == 4 and fp[other["home_team_id"]] == 0
    assert s["fair_play"][-1]["team_id"] == a  # el más sancionado, último

    # suspendidos: los expulsados no pueden jugar el próximo partido
    assert {(x["player_id"], x["reason"]) for x in s["suspensions"]} == {(pl[h][1], "red"), (pl[a][1], "red")}


def test_estadisticas_sin_partidos_y_permisos(client, auth):
    tid, *_ = setup(client, auth)
    s = client.get(f"/api/tournaments/{tid}/stats", headers=auth).json()
    assert s["matches_played"] == 0 and s["goals_per_match"] == 0 and s["scorers"] == [] and s["defense"] == []
    assert len(s["fair_play"]) == 4
    assert client.get(f"/api/tournaments/{tid}/stats").status_code == 401
    assert client.get(f"/api/tournaments/{tid}/stats", headers=register(client, "ext@test.com")).status_code == 404


def test_fecha_y_cancha(client, auth):
    tid, teams, pl, st, ms = setup(client, auth)
    mid = ms[0]["id"]
    sc = add_scorer(client, auth, tid, [mid])
    body = {"scheduled_at": "2026-11-07T16:30:00", "venue": "  Cancha 2 "}
    assert client.put(f"/api/matches/{mid}/schedule", json=body, headers=sc).status_code == 403
    r = client.put(f"/api/matches/{mid}/schedule", json=body, headers=auth).json()
    assert (r["scheduled_at"], r["venue"]) == ("2026-11-07T16:30:00", "Cancha 2")
    r = client.put(f"/api/matches/{mid}/schedule", json={}, headers=auth).json()
    assert (r["scheduled_at"], r["venue"]) == (None, None)


# ---------- vista pública ----------
def enable(client, auth, tid, **kw):
    r = client.put(f"/api/tournaments/{tid}/public", json={"enabled": True, **kw}, headers=auth)
    assert r.status_code == 200
    return r.json()["token"]


def test_link_publico_activar_desactivar_y_renovar(client, auth):
    tid, *_ = setup(client, auth)
    assert client.get(f"/api/tournaments/{tid}/public", headers=auth).json() == {"enabled": False, "token": None}
    t1 = enable(client, auth, tid)
    assert len(t1) >= 16
    assert enable(client, auth, tid) == t1  # activar de nuevo no cambia el link
    assert client.get(f"/api/public/{t1}").status_code == 200  # sin login
    t2 = enable(client, auth, tid, regenerate=True)
    assert t2 != t1 and client.get(f"/api/public/{t1}").status_code == 404
    assert client.put(f"/api/tournaments/{tid}/public", json={"enabled": False}, headers=auth).json() == {"enabled": False, "token": None}
    assert client.get(f"/api/public/{t2}").status_code == 404
    assert client.get("/api/public/inventado").status_code == 404


def test_solo_el_organizador_maneja_el_link(client, auth):
    tid, teams, pl, st, ms = setup(client, auth)
    sc = add_scorer(client, auth, tid, [ms[0]["id"]])
    body = {"enabled": True}
    assert client.put(f"/api/tournaments/{tid}/public", json=body, headers=sc).status_code == 403
    assert client.get(f"/api/tournaments/{tid}/public", headers=sc).status_code == 403
    assert client.put(f"/api/tournaments/{tid}/public", json=body, headers=register(client, "ext@test.com")).status_code == 404


def test_vista_publica_completa_y_sin_datos_privados(client, auth):
    tid, teams, pl, st, ms = setup(client, auth)
    play_stats_match(client, auth, ms, pl)
    mid = ms[0]["id"]
    client.post(f"/api/matches/{mid}/comments", json={"text": "comentario interno"}, headers=auth)
    client.put(f"/api/matches/{mid}/schedule", json={"scheduled_at": "2026-11-07T16:30:00", "venue": "Cancha 1"}, headers=auth)
    token = enable(client, auth, tid)
    r = client.get(f"/api/public/{token}")
    assert r.status_code == 200 and "max-age" in r.headers["cache-control"]
    pub = r.json()
    assert pub["name"] == "Copa" and len(pub["teams"]) == 4 and pub["cups"] == []
    (g,) = pub["groups"]
    assert len(g["standings"]) == 4 and len(g["matches"]) == 6
    played = next(m for m in g["matches"] if m["id"] == mid)
    assert (played["home_goals"], played["away_goals"], played["venue"], played["scheduled_at"]) == (3, 1, "Cancha 1", "2026-11-07T16:30:00")
    assert pub["stats"]["scorers"][0]["goals"] == 2

    # nada privado: ni DNI, ni comentarios, ni emails, ni fotos
    blob = json.dumps(pub)
    for secret in ["comentario interno", "org@test.com", "dni", "birth", "photo", "password"] + [f"{t}0000{i}0" for t in teams for i in (1, 2)]:
        assert secret not in blob, secret

    d = client.get(f"/api/public/{token}/matches/{mid}").json()
    assert [(e["type"], e["minute"]) for e in d["events"]][:2] == [("goal", 10), ("penalty_goal", 20)]
    assert d["events"][0]["player_name"].startswith("J")
    assert set(d["events"][0]) == {"minute", "type", "player_name", "team_id"}
    assert "comments" not in d and "sheets" not in d["match"]


def test_vista_publica_con_llaves(client, auth):
    tid, teams, pl, st, ms = setup(client, auth, n_teams=8, n_groups=2)
    for m in ms:
        client.put(f"/api/matches/{m['id']}/result", json={"home_goals": 1, "away_goals": 0}, headers=auth)
    cups = [{"name": "Copa de Oro", "positions": [1, 2], "extra": []}]
    assert client.post(f"/api/tournaments/{tid}/stages/knockout", json={"cups": cups}, headers=auth).status_code == 201
    pub = client.get(f"/api/public/{enable(client, auth, tid)}").json()
    (cup,) = pub["cups"]
    assert cup["name"] == "Copa de Oro" and cup["rounds"] == 2
    assert len(cup["matches"]) == 4 and cup["matches"][-1]["is_third_place"]
    assert len(pub["groups"]) == 2


def test_partido_de_otro_torneo_no_se_ve(client, auth):
    tid, teams, pl, st, ms = setup(client, auth)
    tid2, *_, ms2 = setup(client, auth)
    token = enable(client, auth, tid)
    assert client.get(f"/api/public/{token}/matches/{ms[0]['id']}").status_code == 200
    assert client.get(f"/api/public/{token}/matches/{ms2[0]['id']}").status_code == 404
    assert client.get(f"/api/public/{token}/matches/999999").status_code == 404


def test_vista_publica_de_torneo_sin_sorteo(client, auth):
    tid, _ = make_tournament(client, auth, 4)
    pub = client.get(f"/api/public/{enable(client, auth, tid)}").json()
    assert pub["groups"] == [] and pub["cups"] == [] and pub["groups_name"] is None and len(pub["teams"]) == 4
