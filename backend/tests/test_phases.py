import pytest

from domain.phases import plan_phases
from domain.qualification import CupSpec, entrants_from_tables, suggest_cup_plans
from tests.test_knockout_api import knock, matches, play_groups, setup, win
from tests.test_qualification import tables

PLAYOFF = CupSpec("Reclasificación", (2, 3), max_rounds=1)
ORO = CupSpec("Copa de Oro", (1,), from_winners=("Reclasificación",))
PLATA = CupSpec("Copa de Plata", (4,), from_losers=("Reclasificación",))


def ents(n_groups=4, size=4):
    return entrants_from_tables(tables(n_groups, size))


def test_plan_del_torneo_de_ejemplo():
    play, oro, plata = plan_phases(ents(), [PLAYOFF, ORO, PLATA])
    assert (play.size, play.rounds, play.total_rounds, len(play.matches)) == (8, 1, 3, 4)
    for p in (oro, plata):
        assert p.size == 8 and p.rounds == 3 and len(p.matches) == 7 + 1  # con 3er puesto
        assert sum(s.team is not None for s in p.slots) == 4 and sum(s.source is not None for s in p.slots) == 4
    assert {s.team.position for s in oro.slots if s.team} == {1}
    assert {s.team.position for s in plata.slots if s.team} == {4}
    assert {(s.source[0], s.source[2]) for s in oro.slots if s.source} == {("Reclasificación", "winner")}
    # en la primera ronda de Oro cada primero se cruza con un ganador del reclasificatorio
    for m in [m for m in oro.matches if m.round == 1]:
        kinds = {oro.slots[m.home.value - 1].team is None, oro.slots[m.away.value - 1].team is None}
        assert kinds == {True, False}


def test_validaciones():
    with pytest.raises(ValueError, match="no existe"):
        plan_phases(ents(), [ORO])
    with pytest.raises(ValueError, match="círculo"):
        plan_phases(ents(), [CupSpec("A", (1,), from_winners=("B",)), CupSpec("B", (2,), from_winners=("A",))])
    with pytest.raises(ValueError, match="ya entran"):
        plan_phases(ents(), [PLAYOFF, ORO, CupSpec("Otra", (4,), from_winners=("Reclasificación",))])
    with pytest.raises(ValueError, match="potencia de 2"):
        plan_phases(ents(3, 4), [PLAYOFF, ORO])  # 6 equipos en una sola ronda
    with pytest.raises(ValueError, match="entre 1 y"):
        plan_phases(ents(), [CupSpec("X", (1, 2), max_rounds=5)])
    with pytest.raises(ValueError, match="distinto"):
        plan_phases(ents(), [CupSpec("X", (1,)), CupSpec("X", (2,))])


def test_sin_tercer_puesto_en_fases_cortadas_y_override():
    play, oro, _ = plan_phases(ents(), [PLAYOFF, ORO, PLATA], third_place=True)
    assert not any(m.third_place for m in play.matches) and any(m.third_place for m in oro.matches)
    _, oro2 = plan_phases(ents(), [PLAYOFF, CupSpec("Copa de Oro", (1,), from_winners=("Reclasificación",), third_place=False)])
    assert not any(m.third_place for m in oro2.matches)


def test_sugerencia_incluye_el_formato():
    labels = [p.label for p in suggest_cup_plans(4, 4)]
    assert "Primero directo a Oro · 2º vs 3º define Oro y Plata" in labels
    assert all("2º vs 3º" not in p.label for p in suggest_cup_plans(3, 4))


def test_api_torneo_completo_con_reclasificacion(client, auth):
    tid, teams, st, ms = setup(client, auth, 16, 4)
    play_groups(client, auth, ms)
    cups = [
        {"name": "Reclasificación", "positions": [2, 3], "max_rounds": 1},
        {"name": "Copa de Oro", "positions": [1], "from_winners": ["Reclasificación"]},
        {"name": "Copa de Plata", "positions": [4], "from_losers": ["Reclasificación"]},
    ]
    prev = client.post(f"/api/tournaments/{tid}/knockout/preview", json={"cups": cups}, headers=auth).json()
    oro_prev = prev["cups"][1]
    assert [c["rounds"] for c in prev["cups"]] == [1, 3, 3] and prev["cups"][0]["total_rounds"] == 3
    assert sum(e["team_id"] is None for e in oro_prev["entrants"]) == 4
    assert any((e["label"] or "").startswith("Ganador del partido 1 de Reclasificación (") for e in oro_prev["entrants"])

    r = knock(client, auth, tid, cups=cups, third_place=True)
    assert r.status_code == 201, r.text
    s_play, s_oro, s_plata = r.json()
    assert s_play["config"]["limited"] and not s_play["config"]["third_place"] and s_oro["config"]["third_place"]
    play = matches(client, auth, s_play["id"])
    assert len(play) == 4 and all(m["home_team_id"] and m["away_team_id"] for m in play)
    oro = matches(client, auth, s_oro["id"])
    assert all((m["home_team_id"] is None) != (m["away_team_id"] is None) for m in oro if m["round"] == 1)

    winners, losers = [], []
    for i, m in enumerate(play):
        assert win(client, auth, m, home=bool(i % 2)).status_code == 200
        winners.append(m["home_team_id"] if i % 2 else m["away_team_id"])
        losers.append(m["away_team_id"] if i % 2 else m["home_team_id"])
    oro = matches(client, auth, s_oro["id"])
    plata = matches(client, auth, s_plata["id"])
    in_oro = {t for m in oro if m["round"] == 1 for t in (m["home_team_id"], m["away_team_id"])}
    in_plata = {t for m in plata if m["round"] == 1 for t in (m["home_team_id"], m["away_team_id"])}
    assert set(winners) <= in_oro and len(in_oro) == 8 and None not in in_oro
    assert set(losers) <= in_plata and len(in_plata) == 8 and None not in in_plata
    assert not (in_oro & in_plata)
    # cada copa sigue su camino hasta la final
    for stage_id in (s_oro["id"], s_plata["id"]):
        for rnd in (1, 2, 3):
            for m in [x for x in matches(client, auth, stage_id) if x["round"] == rnd and not x["is_third_place"]]:
                assert win(client, auth, m).status_code == 200
        final = [m for m in matches(client, auth, stage_id) if m["round"] == 3 and not m["is_third_place"]][0]
        assert final["status"] == "finished"


def test_api_errores_de_fase(client, auth):
    tid, teams, st, ms = setup(client, auth, 12, 3)
    body = {"cups": [{"name": "A", "positions": [1, 2, 3], "max_rounds": 1}]}
    r = client.post(f"/api/tournaments/{tid}/knockout/preview", json=body, headers=auth)
    assert r.status_code == 422 and "potencia de 2" in r.json()["detail"]
    body = {"cups": [{"name": "A", "positions": [1], "from_winners": ["B"]}]}
    assert client.post(f"/api/tournaments/{tid}/knockout/preview", json=body, headers=auth).status_code == 422


def _pairs(plan):
    return [
        (plan.slots[m.home.value - 1].code, plan.slots[m.away.value - 1].code)
        for m in sorted(plan.matches, key=lambda m: m.key) if m.round == 1
    ]


NAMES = {1: "Grupo A", 2: "Grupo B", 3: "Grupo C", 4: "Grupo D"}


def test_cruce_estilo_mundial():
    (p,) = plan_phases(ents(4, 4), [CupSpec("Oro", (1, 2), pairing="cross")], group_names=NAMES)
    assert _pairs(p) == [("1A", "2B"), ("1C", "2D"), ("1B", "2A"), ("1D", "2C")]
    (p2,) = plan_phases(ents(2, 4), [CupSpec("Oro", (1, 2), pairing="cross")], group_names={1: "Grupo A", 2: "Grupo B"})
    assert _pairs(p2) == [("1A", "2B"), ("1B", "2A")]
    (p3,) = plan_phases(ents(4, 4), [CupSpec("Reclas", (2, 3), pairing="cross")], group_names=NAMES)
    assert _pairs(p3) == [("2A", "3B"), ("2C", "3D"), ("2B", "3A"), ("2D", "3C")]
    with pytest.raises(ValueError, match="dos puestos"):
        plan_phases(ents(4, 4), [CupSpec("Oro", (1,), pairing="cross")])
    with pytest.raises(ValueError, match="potencia de 2"):
        plan_phases(ents(3, 4), [CupSpec("Oro", (1, 2), pairing="cross")])


def test_cruce_manual_y_aleatorio():
    manual = (("1A", "1B"), ("2A", "2B"))
    (p,) = plan_phases(ents(2, 4), [CupSpec("Oro", (1, 2), pairing="manual", manual_pairs=manual)],
                       group_names={1: "Grupo A", 2: "Grupo B"})
    assert _pairs(p) == [("1A", "1B"), ("2A", "2B")]
    with pytest.raises(ValueError, match="no está"):
        plan_phases(ents(2, 4), [CupSpec("Oro", (1, 2), pairing="manual", manual_pairs=(("1A", "9Z"), ("2A", "2B")))],
                    group_names={1: "Grupo A", 2: "Grupo B"})
    with pytest.raises(ValueError, match="faltan cruces"):
        plan_phases(ents(2, 4), [CupSpec("Oro", (1, 2), pairing="manual", manual_pairs=(("1A", "1B"),))],
                    group_names={1: "Grupo A", 2: "Grupo B"})
    a = plan_phases(ents(4, 4), [CupSpec("Oro", (1, 2), pairing="random", pairing_seed=1)])[0]
    b = plan_phases(ents(4, 4), [CupSpec("Oro", (1, 2), pairing="random", pairing_seed=1)])[0]
    c = plan_phases(ents(4, 4), [CupSpec("Oro", (1, 2), pairing="random", pairing_seed=2)])[0]
    assert _pairs(a) == _pairs(b) and _pairs(a) != _pairs(c)


def test_orden_libre_de_copas():
    plans = plan_phases(ents(), [ORO, PLATA, PLAYOFF])  # Oro primero aunque depende de la Reclasificación
    assert [p.spec.name for p in plans] == ["Copa de Oro", "Copa de Plata", "Reclasificación"]
    assert plans[0].size == 8 and plans[2].rounds == 1


def test_api_vista_previa_con_cruces_y_mundial(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    cups = [{"name": "Oro", "positions": [1, 2], "pairing": "cross"}]
    prev = client.post(f"/api/tournaments/{tid}/knockout/preview", json={"cups": cups}, headers=auth).json()
    pairs = prev["cups"][0]["pairs"]
    assert [(p["home"]["code"], p["away"]["code"]) for p in pairs] == [("1A", "2B"), ("1B", "2A")]
    play_groups(client, auth, ms)
    (stage,) = knock(client, auth, tid, cups=cups).json()
    first = [m for m in matches(client, auth, stage["id"]) if m["round"] == 1]
    assert len(first) == 2 and all(m["home_team_id"] and m["away_team_id"] for m in first)
    bad = [{"name": "Oro", "positions": [1, 2], "pairing": "manual", "manual_pairs": [["1A", "1A"], ["2A", "2B"]]}]
    assert client.post(f"/api/tournaments/{tid}/knockout/preview", json={"cups": bad}, headers=auth).status_code == 422


def test_primeros_contra_ganadores_predefinidos():
    """1A juega contra el ganador de 2B-3A, 1B contra el ganador de 2A-3B (cruces manuales en Oro)."""
    reclas = CupSpec("Reclasificación", (2, 3), max_rounds=1, pairing="cross")
    oro = CupSpec("Oro", (1,), from_winners=("Reclasificación",), pairing="manual", manual_pairs=(
        ("1A", "G3:Reclasificación"), ("1B", "G1:Reclasificación"), ("1C", "G4:Reclasificación"), ("1D", "G2:Reclasificación")))
    play, o = plan_phases(ents(4, 4), [reclas, oro], group_names=NAMES)
    assert _pairs(play)[2] == ("2B", "3A")
    pairs = _pairs(o)
    assert pairs[0] == ("1A", "G3:Reclasificación") and len(pairs) == 4
    labels = {s.code: s.label for s in o.slots if s.source}
    assert labels["G3:Reclasificación"].endswith("(2B vs 3A)")


CFG = {"cups": [{"name": "Oro", "positions": [1, 2], "pairing": "cross"}], "third_place": False}


def test_config_guardada_y_creacion_automatica(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    url = f"/api/tournaments/{tid}/knockout/config"
    assert client.get(url, headers=auth).json() is None
    assert client.put(url, json={**CFG, "auto_create": True, "picked": 2}, headers=auth).status_code == 200
    saved = client.get(url, headers=auth).json()
    assert saved["cups"][0]["pairing"] == "cross" and saved["auto_create"] and saved["picked"] == 2
    # cerrar todos los partidos de grupos menos el último: todavía no hay llaves
    for m in ms[:-1]:
        client.put(f"/api/matches/{m['id']}/result", json={"home_goals": 1, "away_goals": 0}, headers=auth)
    assert client.get(f"/api/tournaments/{tid}/stages", headers=auth).json()[0]["type"] == "groups"
    assert len(client.get(f"/api/tournaments/{tid}/stages", headers=auth).json()) == 1
    r = client.put(f"/api/matches/{ms[-1]['id']}/result", json={"home_goals": 1, "away_goals": 0}, headers=auth)
    assert r.status_code == 200
    stages = client.get(f"/api/tournaments/{tid}/stages", headers=auth).json()
    assert [s["type"] for s in stages] == ["groups", "knockout"]
    first = [m for m in matches(client, auth, stages[1]["id"]) if m["round"] == 1]
    assert len(first) == 2 and all(m["home_team_id"] and m["away_team_id"] for m in first)


def test_creacion_automatica_apagada_o_invalida_no_rompe(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    url = f"/api/tournaments/{tid}/knockout/config"
    client.put(url, json={**CFG, "auto_create": False}, headers=auth)
    play_groups(client, auth, ms)
    assert len(client.get(f"/api/tournaments/{tid}/stages", headers=auth).json()) == 1
    tid2, teams2, st2, ms2 = setup(client, auth, 8, 2)
    bad = {"cups": [{"name": "Oro", "positions": [1, 2, 3], "max_rounds": 1}]}  # inválida para esta forma
    client.put(f"/api/tournaments/{tid2}/knockout/config", json={**bad, "auto_create": True}, headers=auth)
    play_groups(client, auth, ms2)  # el cierre de partidos igual funciona
    assert len(client.get(f"/api/tournaments/{tid2}/stages", headers=auth).json()) == 1


def test_patch_de_reglas_no_pisa_el_formato(client, auth):
    tid, *_ = setup(client, auth, 8, 2)
    client.put(f"/api/tournaments/{tid}/knockout/config", json=CFG, headers=auth)
    assert client.patch(f"/api/tournaments/{tid}", json={"rules": {"win": 3}}, headers=auth).status_code == 200
    assert client.get(f"/api/tournaments/{tid}/knockout/config", headers=auth).json()["cups"][0]["name"] == "Oro"


def test_config_invalida_no_pierde_el_cierre(client, auth):
    tid, teams, st, ms = setup(client, auth, 8, 2)
    bad = {"cups": [{"name": "Oro", "positions": [1, 2, 3], "max_rounds": 1}]}
    client.put(f"/api/tournaments/{tid}/knockout/config", json=bad, headers=auth)
    play_groups(client, auth, ms)
    after = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    assert all(m["status"] == "finished" for m in after)
