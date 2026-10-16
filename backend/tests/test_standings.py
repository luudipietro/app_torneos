from domain.standings import Result, Rules, standings


def R(h, a, hg, ag):
    return Result(h, a, hg, ag)


def test_puntos_basicos():
    t = standings([1, 2, 3], [R(1, 2, 2, 0), R(2, 3, 1, 1), R(1, 3, 0, 1)])
    pts = {r.team: r.points for r in t}
    assert pts == {1: 3, 2: 1, 3: 4}
    assert t[0].team == 3


def test_diferencia_de_gol_desempata():
    res = [R(1, 3, 3, 0), R(2, 3, 1, 0), R(1, 2, 0, 0)]
    t = standings([1, 2, 3], res, Rules(tiebreakers=["points", "gd", "gf"]))
    assert [r.team for r in t][:2] == [1, 2]


def test_h2h_antes_que_diferencia():
    # 1 y 2 igualan en puntos; 2 le ganó a 1, pero 1 tiene mejor DG por goleada a 3
    res = [R(2, 1, 1, 0), R(1, 3, 5, 0), R(2, 3, 0, 0), R(3, 1, 0, 0)]
    t = standings([1, 2, 3], res)
    pts = {r.team: r.points for r in t}
    assert pts[1] == pts[2] == 4
    assert [r.team for r in t][:2] == [2, 1]
    t2 = standings([1, 2, 3], res, Rules(tiebreakers=["points", "gd"]))
    assert [r.team for r in t2][:2] == [1, 2]


def test_fair_play():
    res = [R(1, 2, 1, 1)]
    t = standings([1, 2], res, Rules(tiebreakers=["points", "fair_play"]), fair_play={1: 5, 2: 2})
    assert t[0].team == 2


def test_ignora_equipos_ajenos_y_sin_partidos():
    t = standings([1, 2], [R(1, 9, 3, 0)])
    assert all(r.played == 0 for r in t)
