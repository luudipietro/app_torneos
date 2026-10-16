from tests.conftest import add_scorer, make_tournament, register


def invite(client, h, tid, email, role="scorer"):
    return client.post(f"/api/tournaments/{tid}/members", json={"email": email, "role": role}, headers=h)


def two_matches(client, h, n=4):
    tid, _ = make_tournament(client, h, n)
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 1, "seed": 1}, headers=h).json()
    return tid, client.get(f"/api/stages/{st['id']}/matches", headers=h).json()


def test_invitar_a_usuario_existente(client, auth):
    tid, _ = make_tournament(client, auth, 2)
    sc = register(client, "plan@test.com")
    r = invite(client, auth, tid, "PLAN@test.com")
    assert r.status_code == 201
    assert [(m["email"], m["role"]) for m in r.json()["members"]] == [("org@test.com", "admin"), ("plan@test.com", "scorer")] \
        or {m["email"] for m in r.json()["members"]} == {"org@test.com", "plan@test.com"}
    assert r.json()["invitations"] == []
    assert invite(client, auth, tid, "plan@test.com").status_code == 409
    mine = client.get("/api/tournaments", headers=sc).json()
    assert [(t["id"], t["my_role"]) for t in mine] == [(tid, "scorer")]


def test_invitacion_pendiente_se_acepta_al_registrarse(client, auth):
    tid, _ = make_tournament(client, auth, 2)
    r = invite(client, auth, tid, "nuevo@test.com")
    assert r.status_code == 201 and [i["email"] for i in r.json()["invitations"]] == ["nuevo@test.com"]
    assert invite(client, auth, tid, "nuevo@test.com").status_code == 409
    nuevo = register(client, "nuevo@test.com")
    t = client.get(f"/api/tournaments/{tid}", headers=nuevo).json()
    assert t["my_role"] == "scorer"
    assert client.get(f"/api/tournaments/{tid}/members", headers=auth).json()["invitations"] == []


def test_cancelar_invitacion(client, auth):
    tid, _ = make_tournament(client, auth, 2)
    inv = invite(client, auth, tid, "nuevo@test.com").json()["invitations"][0]
    r = client.delete(f"/api/tournaments/{tid}/invitations/{inv['id']}", headers=auth)
    assert r.json()["invitations"] == []
    nuevo = register(client, "nuevo@test.com")
    assert client.get(f"/api/tournaments/{tid}", headers=nuevo).status_code == 404


def test_solo_el_organizador_gestiona_miembros(client, auth):
    tid, ms = two_matches(client, auth)
    sc = add_scorer(client, auth, tid, [ms[0]["id"]])
    assert invite(client, sc, tid, "otro@test.com").status_code == 403
    assert client.get(f"/api/tournaments/{tid}/members", headers=sc).status_code == 403
    ext = register(client, "ext@test.com")
    assert invite(client, ext, tid, "otro@test.com").status_code == 404
    assert client.put(f"/api/matches/{ms[0]['id']}/assignments", json={"user_ids": []}, headers=sc).status_code == 403


def test_planillero_solo_accede_a_sus_partidos(client, auth):
    tid, ms = two_matches(client, auth)
    a, b = ms[0]["id"], ms[1]["id"]
    sc = add_scorer(client, auth, tid, [a])
    assert client.get(f"/api/matches/{a}", headers=sc).status_code == 200
    for method, url, body in [
        ("get", f"/api/matches/{b}", None),
        ("get", f"/api/matches/{b}/lineup", None),
        ("post", f"/api/matches/{b}/comments", {"text": "hola"}),
        ("put", f"/api/matches/{b}/result", {"home_goals": 1, "away_goals": 0}),
        ("post", f"/api/matches/{b}/finish", None),
    ]:
        r = getattr(client, method)(url, headers=sc, **({"json": body} if body else {}))
        assert r.status_code == 403, (url, r.status_code)
    # resultado rápido en el asignado
    assert client.put(f"/api/matches/{a}/result", json={"home_goals": 1, "away_goals": 0}, headers=sc).status_code == 200
    # el organizador sigue viendo todo
    assert client.get(f"/api/matches/{b}", headers=auth).status_code == 200


def test_mis_partidos_y_asignaciones_visibles(client, auth):
    tid, ms = two_matches(client, auth)
    sc = add_scorer(client, auth, tid, [ms[0]["id"], ms[2]["id"]])
    mine = client.get(f"/api/tournaments/{tid}/my-matches", headers=sc).json()
    assert sorted(m["id"] for m in mine) == sorted([ms[0]["id"], ms[2]["id"]])
    assert client.get(f"/api/tournaments/{tid}/my-matches", headers=auth).json() == []
    stage_id = ms[0]["stage_id"]
    listed = client.get(f"/api/stages/{stage_id}/matches", headers=auth).json()
    me = client.get("/api/auth/me", headers=sc).json()["id"]
    assert {m["id"] for m in listed if me in m["assignee_ids"]} == {ms[0]["id"], ms[2]["id"]}


def test_asignar_reemplaza_y_valida_miembros(client, auth):
    tid, ms = two_matches(client, auth)
    sc = add_scorer(client, auth, tid, [ms[0]["id"]])
    me = client.get("/api/auth/me", headers=sc).json()["id"]
    ext_id = client.get("/api/auth/me", headers=register(client, "ext@test.com")).json()["id"]
    url = f"/api/matches/{ms[0]['id']}/assignments"
    assert client.put(url, json={"user_ids": [ext_id]}, headers=auth).status_code == 422
    assert client.put(url, json={"user_ids": [me, me]}, headers=auth).json()["assignee_ids"] == [me]
    assert client.put(url, json={"user_ids": []}, headers=auth).json()["assignee_ids"] == []
    assert client.get(f"/api/matches/{ms[0]['id']}", headers=sc).status_code == 403
    bad = client.post(f"/api/tournaments/{tid}/assignments", json={"user_id": me, "match_ids": [99999]}, headers=auth)
    assert bad.status_code == 404


def test_quitar_miembro_limpia_asignaciones(client, auth):
    tid, ms = two_matches(client, auth)
    sc = add_scorer(client, auth, tid, [ms[0]["id"]])
    me = client.get("/api/auth/me", headers=sc).json()["id"]
    org = client.get("/api/auth/me", headers=auth).json()["id"]
    assert client.delete(f"/api/tournaments/{tid}/members/{org}", headers=auth).status_code == 409
    r = client.delete(f"/api/tournaments/{tid}/members/{me}", headers=auth)
    assert [m["email"] for m in r.json()["members"]] == ["org@test.com"]
    assert client.get(f"/api/tournaments/{tid}", headers=sc).status_code == 404
    assert client.get(f"/api/stages/{ms[0]['stage_id']}/matches", headers=auth).json()[0]["assignee_ids"] == []


def test_coorganizador(client, auth):
    tid, ms = two_matches(client, auth)
    co = register(client, "co@test.com")
    assert invite(client, auth, tid, "co@test.com", role="admin").status_code == 201
    assert client.post(f"/api/tournaments/{tid}/teams", json={"name": "Nuevo"}, headers=co).status_code in (201, 409)
    assert client.get(f"/api/matches/{ms[0]['id']}", headers=co).status_code == 200
    assert invite(client, auth, tid, "x@test.com", role="superuser").status_code == 422
