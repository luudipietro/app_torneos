from tests.conftest import make_tournament, register


def test_auth_y_acceso_protegido(client):
    assert client.get("/api/tournaments").status_code == 401
    h = register(client)
    assert client.get("/api/auth/me", headers=h).json()["email"] == "org@test.com"
    dup = client.post("/api/auth/register", json={"email": "ORG@test.com", "name": "x", "password": "password123"})
    assert dup.status_code == 409
    assert client.post("/api/auth/login", json={"email": "org@test.com", "password": "mala"}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "org@test.com", "password": "password123"})
    assert ok.status_code == 200


def test_aislamiento_entre_usuarios(client, auth):
    tid, _ = make_tournament(client, auth, 2)
    otro = register(client, "otro@test.com")
    assert client.get(f"/api/tournaments/{tid}", headers=otro).status_code == 404
    assert client.get("/api/tournaments", headers=otro).json() == []
    assert client.post(f"/api/tournaments/{tid}/teams", json={"name": "X"}, headers=otro).status_code == 404


def test_equipos_y_jugadores(client, auth):
    tid, teams = make_tournament(client, auth, 2)
    assert client.post(f"/api/tournaments/{tid}/teams", json={"name": "Equipo 1"}, headers=auth).status_code == 409
    p = {"name": "Juan", "dni": "30111222", "number": 9}
    r = client.post(f"/api/teams/{teams[0]}/players", json=p, headers=auth)
    assert r.status_code == 201
    # mismo DNI en otro equipo del torneo: rechazado
    assert client.post(f"/api/teams/{teams[1]}/players", json=p, headers=auth).status_code == 409
    pid = r.json()["id"]
    assert client.patch(f"/api/players/{pid}", json={"number": 10}, headers=auth).json()["number"] == 10
    assert len(client.get(f"/api/teams/{teams[0]}/players", headers=auth).json()) == 1
    assert client.delete(f"/api/players/{pid}", headers=auth).status_code == 204


def test_layouts_para_64(client, auth):
    tid, _ = make_tournament(client, auth, 64)
    lays = client.get(f"/api/tournaments/{tid}/layouts", headers=auth).json()
    assert {"n_groups": 16, "sizes": [4] * 16, "balanced": True} in lays
    assert client.post(f"/api/tournaments/{tid}/teams", json={"name": "extra"}, headers=auth).status_code == 422


def test_torneo_de_64_grupos_y_fixture(client, auth):
    tid, teams = make_tournament(client, auth, 64)
    r = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 16, "seed": 1}, headers=auth)
    assert r.status_code == 201
    st = r.json()
    assert len(st["groups"]) == 16 and all(len(g["team_ids"]) == 4 for g in st["groups"])
    assert sorted(i for g in st["groups"] for i in g["team_ids"]) == sorted(teams)
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    assert len(ms) == 16 * 6
    # ya hay sorteo: no se puede repetir ni tocar equipos
    assert client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 8}, headers=auth).status_code == 409
    assert client.delete(f"/api/teams/{teams[0]}", headers=auth).status_code == 409


def test_resultados_y_tabla(client, auth):
    tid, teams = make_tournament(client, auth, 4)
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 1, "seed": 3}, headers=auth).json()
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    assert len(ms) == 6
    # el equipo local del primer partido gana todo lo que juega de local; resto 0-0
    for i, m in enumerate(ms):
        hg = 2 if i == 0 else 0
        client.put(f"/api/matches/{m['id']}/result", json={"home_goals": hg, "away_goals": 0}, headers=auth)
    tabla = client.get(f"/api/stages/{st['id']}/standings", headers=auth).json()[0]["rows"]
    assert tabla[0]["team_id"] == ms[0]["home_team_id"]
    assert tabla[0]["points"] == 5  # 1 victoria + 2 empates
    assert sum(r["played"] for r in tabla) == 12
    # con resultados ya no se puede borrar la etapa
    assert client.delete(f"/api/stages/{st['id']}", headers=auth).status_code == 409


def test_reglamento_puntos_personalizados(client, auth):
    tid, _ = make_tournament(client, auth, 2, win=2, draw=1, loss=0)
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 1}, headers=auth).json()
    m = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()[0]
    client.put(f"/api/matches/{m['id']}/result", json={"home_goals": 1, "away_goals": 0}, headers=auth)
    tabla = client.get(f"/api/stages/{st['id']}/standings", headers=auth).json()[0]["rows"]
    assert tabla[0]["points"] == 2


def test_borrar_etapa_sin_resultados_permite_rehacer(client, auth):
    tid, _ = make_tournament(client, auth, 8)
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 2}, headers=auth).json()
    assert client.delete(f"/api/stages/{st['id']}", headers=auth).status_code == 204
    assert client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 4, "double_round": True}, headers=auth).status_code == 201


def test_grupos_demasiado_chicos(client, auth):
    tid, _ = make_tournament(client, auth, 5)
    assert client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 3}, headers=auth).status_code == 422
