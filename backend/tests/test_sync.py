import uuid

from tests.conftest import add_scorer, make_tournament, register

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def uid():
    return uuid.uuid4().hex


def op(kind, match_id, **payload):
    return {"id": uid(), "type": kind, "match_id": match_id, "payload": payload}


def setup(client, auth, **rules):
    """Torneo de 4 equipos con jugadores; devuelve un planillero asignado al primer partido."""
    tid, teams = make_tournament(client, auth, 4, **rules)
    players = {}
    for t in teams:
        for i in (1, 2):
            r = client.post(f"/api/teams/{t}/players", json={"name": f"J{t}-{i}", "dni": f"{t}0000{i}0"}, headers=auth)
            players.setdefault(t, []).append(r.json()["id"])
    st = client.post(f"/api/tournaments/{tid}/stages/groups", json={"n_groups": 1, "seed": 1}, headers=auth).json()
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    m = ms[0]
    sc = add_scorer(client, auth, tid, [m["id"]])
    return tid, m, players, sc, ms


def send(client, h, ops):
    r = client.post("/api/sync", json={"ops": ops}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["results"]


def detail(client, h, mid):
    return client.get(f"/api/matches/{mid}", headers=h).json()


def test_lote_completo_se_aplica_en_orden(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    home, away = m["home_team_id"], m["away_team_id"]
    mid = m["id"]
    ops = [
        op("lineup.mark", mid, player_id=pl[home][0]),
        op("lineup.mark", mid, player_id=pl[away][0]),
        op("event.add", mid, player_id=pl[home][0], type="goal", minute=12, client_id="ev-" + uid()),
        op("event.add", mid, player_id=pl[away][0], type="yellow", minute=30, client_id="ev-" + uid()),
        op("comment.add", mid, text="Llovizna en el segundo tiempo"),
        op("match.finish", mid),
    ]
    res = send(client, sc, ops)
    assert [r["status"] for r in res] == ["ok"] * 6
    d = detail(client, sc, mid)
    assert (d["home_goals"], d["away_goals"], d["status"]) == (1, 0, "finished")
    assert len(d["events"]) == 2 and d["comments"][0]["text"].startswith("Llovizna")


def test_reenviar_el_mismo_lote_no_duplica(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    mid, home = m["id"], m["home_team_id"]
    ops = [
        op("lineup.mark", mid, player_id=pl[home][0]),
        op("event.add", mid, player_id=pl[home][0], type="goal", client_id="ev-" + uid()),
        op("comment.add", mid, text="una vez"),
    ]
    first = send(client, sc, ops)
    again = send(client, sc, ops)
    assert [r["status"] for r in again] == ["ok"] * 3 and all(r["duplicate"] for r in again)
    assert not any(r["duplicate"] for r in first)
    d = detail(client, sc, mid)
    assert len(d["events"]) == 1 and len(d["comments"]) == 1 and d["home_goals"] == 1


def test_una_rechazada_no_frena_las_demas(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    mid, home = m["id"], m["home_team_id"]
    ops = [
        op("lineup.mark", mid, player_id=pl[home][0]),
        op("event.add", mid, player_id=pl[home][1], type="goal"),  # no está en la lista de buena fe
        op("comment.add", mid, text="sigue funcionando"),
    ]
    res = send(client, sc, ops)
    assert [r["status"] for r in res] == ["ok", "rejected", "ok"]
    assert res[1]["code"] == 422 and "buena fe" in res[1]["message"]
    # reenviar devuelve el mismo rechazo sin reintentarlo
    again = send(client, sc, [ops[1]])
    assert again[0]["status"] == "rejected" and again[0]["duplicate"] and again[0]["code"] == 422


def test_gana_el_servidor_si_el_organizador_cerro_el_partido(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    mid, home = m["id"], m["home_team_id"]
    client.post(f"/api/matches/{mid}/finish", headers=auth)  # el organizador lo cerró mientras tanto
    res = send(client, sc, [op("lineup.mark", mid, player_id=pl[home][0]), op("comment.add", mid, text="tarde")])
    assert [(r["status"], r["code"]) for r in res] == [("rejected", 403), ("ok", 200)]  # comentar siempre se puede
    assert detail(client, auth, mid)["status"] == "finished"


def test_suspendido_no_se_puede_marcar_presente(client, auth):
    tid, m, pl, sc, ms = setup(client, auth)
    home = m["home_team_id"]
    p = pl[home][0]
    # expulsión del jugador en este partido -> suspendido en el siguiente del equipo
    client.put(f"/api/matches/{m['id']}/lineup/{p}", headers=auth)
    client.post(f"/api/matches/{m['id']}/events", json={"player_id": p, "type": "red"}, headers=auth)
    client.post(f"/api/matches/{m['id']}/finish", headers=auth)
    nxt = next(x for x in ms if x["id"] != m["id"] and home in (x["home_team_id"], x["away_team_id"]))
    client.put(f"/api/matches/{nxt['id']}/assignments", json={"user_ids": [client.get("/api/auth/me", headers=sc).json()["id"]]}, headers=auth)
    res = send(client, sc, [op("lineup.mark", nxt["id"], player_id=p)])
    assert res[0]["status"] == "rejected" and res[0]["code"] == 409 and "suspendido" in res[0]["message"]


def test_borrar_evento_por_client_id_y_borrar_inexistente(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    mid, home = m["id"], m["home_team_id"]
    cid = "ev-" + uid()
    send(client, sc, [op("lineup.mark", mid, player_id=pl[home][0]),
                      op("event.add", mid, player_id=pl[home][0], type="goal", client_id=cid)])
    assert detail(client, sc, mid)["home_goals"] == 1
    res = send(client, sc, [op("event.delete", mid, client_id=cid), op("event.delete", mid, client_id="nunca-existio")])
    assert [r["status"] for r in res] == ["ok", "ok"]
    d = detail(client, sc, mid)
    assert d["events"] == [] and d["home_goals"] == 0


def test_cierre_de_partido_de_grupos_sin_goles(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    # partido de grupos: el empate no necesita penales
    res = send(client, sc, [op("match.finish", m["id"])])
    assert res[0]["status"] == "ok"
    d = detail(client, sc, m["id"])
    assert (d["home_goals"], d["away_goals"], d["status"]) == (0, 0, "finished")


def test_payload_invalido_se_rechaza_y_no_corta(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    mid = m["id"]
    res = send(client, sc, [op("event.add", mid, type="goal"), op("comment.add", mid, text="ok")])
    assert [(r["status"], r["code"]) for r in res] == [("rejected", 422), ("ok", 200)]


def test_operacion_de_otro_usuario_con_mismo_id(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    o = op("comment.add", m["id"], text="mio")
    assert send(client, sc, [o])[0]["status"] == "ok"
    res = send(client, auth, [o])  # el organizador reutiliza el id
    assert res[0]["status"] == "rejected" and res[0]["code"] == 409
    assert len(detail(client, auth, m["id"])["comments"]) == 1


def test_planillero_no_asignado_y_validaciones(client, auth):
    tid, m, pl, sc, ms = setup(client, auth)
    otro = next(x for x in ms if x["id"] != m["id"])
    res = send(client, sc, [op("comment.add", otro["id"], text="no me toca")])
    assert res[0]["status"] == "rejected" and res[0]["code"] == 403
    assert client.post("/api/sync", json={"ops": []}).status_code == 401
    assert client.post("/api/sync", json={"ops": [op("comment.add", m["id"], text="x")] * 101}, headers=sc).status_code == 422
    assert client.post("/api/sync", json={"ops": [{"id": "corto", "type": "comment.add", "match_id": 1}]}, headers=sc).status_code == 422
    assert client.post("/api/sync", json={"ops": [op("evil.type", m["id"])]}, headers=sc).status_code == 422


def test_bundle(client, auth):
    tid, m, pl, sc, ms = setup(client, auth)
    b = client.get(f"/api/matches/{m['id']}/bundle", headers=sc).json()
    assert b["detail"]["id"] == m["id"] and b["lineup"]["match_id"] == m["id"]
    assert len(b["lineup"]["home"]["players"]) == 2
    otro = next(x for x in ms if x["id"] != m["id"])
    assert client.get(f"/api/matches/{otro['id']}/bundle", headers=sc).status_code == 403


def test_foto_con_client_id_no_se_duplica(client, auth):
    tid, m, pl, sc, _ = setup(client, auth)
    url = f"/api/matches/{m['id']}/sheets"
    cid = "sh-" + uid()
    for _ in range(2):
        r = client.post(url, files={"file": ("p.png", PNG, "image/png")}, data={"client_id": cid}, headers=sc)
        assert r.status_code == 201
    assert len(detail(client, sc, m["id"])["sheets"]) == 1
