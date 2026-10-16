import pytest

from domain.knockout import build_bracket, bracket_size, round_name, seed_order, total_rounds


def test_seed_order():
    assert seed_order(2) == [1, 2]
    assert seed_order(4) == [1, 4, 2, 3]
    assert seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_tamanos():
    assert [bracket_size(n) for n in (2, 3, 4, 5, 8, 9, 32, 33, 64)] == [2, 4, 4, 8, 8, 16, 32, 64, 64]
    assert [total_rounds(n) for n in (2, 8, 33)] == [1, 3, 6]
    for bad in (0, 1, 65):
        with pytest.raises(ValueError):
            bracket_size(bad)


@pytest.mark.parametrize("n", range(2, 65))
def test_cantidad_de_partidos(n):
    # eliminación directa: n equipos -> n-1 partidos (sin 3er puesto)
    assert len(build_bracket(n)) == n - 1


@pytest.mark.parametrize("n", range(2, 65))
def test_integridad_de_la_llave(n):
    ms = build_bracket(n)
    keys = [m.key for m in ms]
    assert keys == sorted(set(keys))
    seeds = [r.value for m in ms for r in (m.home, m.away) if r.kind == "seed"]
    assert sorted(seeds) == list(range(1, n + 1))  # cada equipo entra una sola vez
    # cada ganador alimenta exactamente a un partido y solo el campeón queda sin destino
    winners = [r.value for m in ms for r in (m.home, m.away) if r.kind == "winner"]
    assert len(winners) == len(set(winners)) == n - 2
    assert set(winners) | {ms[-1].key} == set(keys)
    # un partido solo puede referirse a partidos de rondas anteriores
    rnd = {m.key: m.round for m in ms}
    for m in ms:
        for r in (m.home, m.away):
            if r.kind == "winner":
                assert rnd[r.value] < m.round


def test_ocho_equipos_sin_byes():
    ms = build_bracket(8)
    r1 = [(m.home.value, m.away.value) for m in ms if m.round == 1]
    assert r1 == [(1, 8), (4, 5), (2, 7), (3, 6)]
    assert [m.round for m in ms] == [1, 1, 1, 1, 2, 2, 3]


def test_byes_para_los_mejores_cabezas():
    ms = build_bracket(5)  # llave de 8 con 3 byes: series 1, 2 y 3 pasan directo
    r1 = [m for m in ms if m.round == 1]
    assert [(m.home.value, m.away.value) for m in r1] == [(4, 5)]
    r2 = [m for m in ms if m.round == 2]
    assert [(m.home.kind, m.home.value, m.away.kind) for m in r2] == [("seed", 1, "winner"), ("seed", 2, "seed")]
    assert r2[1].away.value == 3


def test_tres_equipos():
    ms = build_bracket(3, third_place=True)
    assert [(m.round, m.home.value, m.away.value) for m in ms] == [(1, 2, 3), (2, 1, 1)]
    assert not any(m.third_place for m in ms)  # una sola semifinal real: no hay 3er puesto


def test_tercer_puesto():
    ms = build_bracket(8, third_place=True)
    third = ms[-1]
    assert third.third_place and third.round == 3
    assert (third.home.kind, third.away.kind) == ("loser", "loser")
    semis = [m.key for m in ms if m.round == 2]
    assert [third.home.value, third.away.value] == semis
    assert len(ms) == 8
    assert sum(1 for m in build_bracket(8, third_place=True) if m.third_place) == 1
    assert len(build_bracket(2, third_place=True)) == 1  # solo la final


def test_nombres_de_ronda():
    assert [round_name(r, 5) for r in range(1, 6)] == [
        "Dieciseisavos de final", "Octavos de final", "Cuartos de final", "Semifinales", "Final"]
    assert round_name(1, 6) == "Ronda de 64"
    assert round_name(1, 1) == "Final"
