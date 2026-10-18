import pytest

from domain.groups import draw_groups, draw_steps
from tests.conftest import make_tournament
from tests.test_groups import equipos


def test_pasos_coinciden_con_el_sorteo():
    t = equipos(12, seeds=3)
    steps = draw_steps(t, 3, seed=9)
    assert len(steps) == 12
    groups = [[] for _ in range(3)]
    for team, g in steps:
        groups[g].append(team)
    assert groups == draw_groups(t, 3, seed=9)
    # el primer bombo (cabezas de serie) sale primero, uno por grupo
    assert [team.id for team, _ in steps[:3]] == [1, 2, 3]
    assert sorted(g for _, g in steps[:3]) == [0, 1, 2]


def test_equipos_fijos_se_respetan_y_se_balancea():
    t = equipos(12, seeds=4)
    fixed = {1: 0, 2: 0, 12: 1}
    steps = draw_steps(t, 3, seed=2, fixed=fixed)
    assert {team.id for team, _ in steps} == set(range(1, 13)) - set(fixed)
    groups = draw_groups(t, 3, seed=2, fixed=fixed)
    assert [len(g) for g in groups] == [4, 4, 4]
    assert {x.id for x in groups[0]} >= {1, 2} and 12 in {x.id for x in groups[1]}
    assert len({x.id for g in groups for x in g}) == 12


def test_fijos_invalidos():
    with pytest.raises(ValueError):
        draw_steps(equipos(8), 2, fixed={99: 0})
    with pytest.raises(ValueError):
        draw_steps(equipos(8), 2, fixed={1: 5})


def test_api_sorteo_sin_guardar_y_confirmacion_manual(client, auth):
    tid, teams = make_tournament(client, auth, 8)
    r = client.post(f"/api/tournaments/{tid}/stages/groups/draw", json={"n_groups": 2, "seed": 4, "fixed": {str(teams[0]): 1}}, headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert len(d["steps"]) == 7 and teams[0] not in [s["team_id"] for s in d["steps"]]
    assert teams[0] in d["groups"][1] and sorted(len(g) for g in d["groups"]) == [4, 4]
    assert client.get(f"/api/tournaments/{tid}/stages", headers=auth).json() == []  # no guardó nada

    ok = client.post(f"/api/tournaments/{tid}/stages/groups", json={"groups": d["groups"]}, headers=auth)
    assert ok.status_code == 201
    st = ok.json()
    assert [g["team_ids"] for g in st["groups"]] == [sorted(g) for g in d["groups"]] and st["config"]["manual"]
    ms = client.get(f"/api/stages/{st['id']}/matches", headers=auth).json()
    assert len(ms) == 12  # 6 partidos por grupo de 4


def test_api_grupos_manuales_invalidos(client, auth):
    tid, teams = make_tournament(client, auth, 6)
    url = f"/api/tournaments/{tid}/stages/groups"
    assert client.post(url, json={}, headers=auth).status_code == 422
    assert client.post(url, json={"groups": [teams[:3], teams[3:5]]}, headers=auth).status_code == 422  # falta uno
    assert client.post(url, json={"groups": [teams[:3], teams[2:]]}, headers=auth).status_code == 422  # repetido
    assert client.post(url, json={"groups": [teams[:5], [teams[5], 9999]]}, headers=auth).status_code == 422  # ajeno
    assert client.post(url, json={"groups": [teams[:5], teams[5:]]}, headers=auth).status_code == 422  # grupo de 1
    # grupos desparejos a mano están permitidos
    assert client.post(url, json={"groups": [teams[:4], teams[4:]]}, headers=auth).status_code == 201
