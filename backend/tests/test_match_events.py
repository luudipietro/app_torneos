from tests.conftest import add_scorer, make_tournament, register

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def setup_match(client, auth):
    """Torneo de 2 equipos con 2 jugadores cada uno y su único partido."""
    tid, teams = make_tournament(client, auth, 2)
    players = {}
    for t in teams:
        for i in (1, 2):
            r = client.post(f"/api/teams/{t}/players", json={"name": f"J{t}{i}", "dni": f"{t}000{i}00"}, headers=auth)
            players.setdefault(t, []).append(r.json()["id"])
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 1}, headers=auth).json()
    m = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()[0]
    return tid, st, m, players


def test_goles_calculan_resultado_y_tarjetas_no(client, auth):
    tid, st, m, pl = setup_match(client, auth)
    home, away = m["home_team_id"], m["away_team_id"]
    ev = lambda p, t, minute=None: client.post(f"/api/matches/{m['id']}/events", json={"player_id": p, "type": t, "minute": minute}, headers=auth)
    assert ev(pl[home][0], "goal", 10).status_code == 201
    assert ev(pl[home][1], "penalty_goal", 50).status_code == 201
    d = ev(pl[away][0], "own_goal", 70).json()  # gol en contra del visitante -> suma al local
    assert (d["home_goals"], d["away_goals"], d["status"]) == (3, 0, "in_progress")
    d = ev(pl[away][1], "yellow", 80).json()
    assert d["home_goals"] == 3 and len(d["events"]) == 4
    assert [e["minute"] for e in d["events"]] == [10, 50, 70, 80]
    # borrar un gol recalcula
    d = client.delete(f"/api/matches/{m['id']}/events/{d['events'][0]['id']}", headers=auth).json()
    assert d["home_goals"] == 2


def test_jugador_ajeno_al_partido_y_resultado_manual_bloqueado(client, auth):
    tid, st, m, pl = setup_match(client, auth)
    otro_tid, otros = make_tournament(client, auth, 2)
    ajeno = client.post(f"/api/teams/{otros[0]}/players", json={"name": "X", "dni": "99999999"}, headers=auth).json()["id"]
    r = client.post(f"/api/matches/{m['id']}/events", json={"player_id": ajeno, "type": "goal"}, headers=auth)
    assert r.status_code == 422
    bad = client.post(f"/api/matches/{m['id']}/events", json={"player_id": pl[m["home_team_id"]][0], "type": "foo"}, headers=auth)
    assert bad.status_code == 422
    client.post(f"/api/matches/{m['id']}/events", json={"player_id": pl[m["home_team_id"]][0], "type": "goal"}, headers=auth)
    r = client.put(f"/api/matches/{m['id']}/result", json={"home_goals": 5, "away_goals": 0}, headers=auth)
    assert r.status_code == 409


def test_cierre_tabla_y_permisos(client, auth):
    tid, st, m, pl = setup_match(client, auth)
    home = m["home_team_id"]
    client.post(f"/api/matches/{m['id']}/events", json={"player_id": pl[home][0], "type": "goal"}, headers=auth)
    # en juego todavía no cuenta en la tabla
    rows = client.get(f"/api/stages/{st['id']}/standings", headers=auth).json()[0]["rows"]
    assert sum(r["played"] for r in rows) == 0
    assert client.post(f"/api/matches/{m['id']}/finish", headers=auth).json()["status"] == "finished"
    rows = client.get(f"/api/stages/{st['id']}/standings", headers=auth).json()[0]["rows"]
    assert rows[0]["team_id"] == home and rows[0]["points"] == 3

    sc = add_scorer(client, auth, tid, [m["id"]])
    url = f"/api/matches/{m['id']}/events"
    assert client.post(url, json={"player_id": pl[home][1], "type": "goal"}, headers=sc).status_code == 403
    assert client.post(f"/api/matches/{m['id']}/comments", json={"text": "hola"}, headers=sc).status_code == 201
    assert client.post(f"/api/matches/{m['id']}/reopen", headers=sc).status_code == 403
    assert client.post(f"/api/matches/{m['id']}/reopen", headers=auth).status_code == 200
    assert client.post(url, json={"player_id": pl[home][1], "type": "goal"}, headers=sc).status_code == 201
    # ajeno al torneo: ni lo ve
    ext = register(client, "ext@test.com")
    assert client.get(f"/api/matches/{m['id']}", headers=ext).status_code == 404


def test_planilla_foto(client, auth):
    tid, st, m, pl = setup_match(client, auth)
    url = f"/api/matches/{m['id']}/sheets"
    r = client.post(url, files={"file": ("planilla.png", PNG, "image/png")}, headers=auth)
    assert r.status_code == 201
    sid = r.json()["sheets"][0]["id"]
    f = client.get(f"/api/sheets/{sid}/file", headers=auth)
    assert f.status_code == 200 and f.content == PNG and f.headers["content-type"] == "image/png"
    assert client.get(f"/api/sheets/{sid}/file").status_code == 401
    # contenido que no es imagen aunque el cliente diga que sí
    bad = client.post(url, files={"file": ("x.png", b"<html>no</html>", "image/png")}, headers=auth)
    assert bad.status_code == 415
    big = client.post(url, files={"file": ("x.png", b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024), "image/png")}, headers=auth)
    assert big.status_code == 413
    ext = register(client, "ext@test.com")
    assert client.get(f"/api/sheets/{sid}/file", headers=ext).status_code == 404
    d = client.delete(f"/api/sheets/{sid}", headers=auth).json()
    assert d["sheets"] == []


def test_comentarios(client, auth):
    tid, st, m, pl = setup_match(client, auth)
    d = client.post(f"/api/matches/{m['id']}/comments", json={"text": "  Se suspendió 5 min por lluvia  "}, headers=auth).json()
    c = d["comments"][0]
    assert c["text"] == "Se suspendió 5 min por lluvia" and c["author"] == "Org"
    assert client.post(f"/api/matches/{m['id']}/comments", json={"text": ""}, headers=auth).status_code == 422
    d = client.delete(f"/api/matches/{m['id']}/comments/{c['id']}", headers=auth).json()
    assert d["comments"] == []
