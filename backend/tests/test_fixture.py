from itertools import combinations

import pytest

from domain.fixture import round_robin


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 8, 11, 12])
def test_cada_par_se_enfrenta_una_vez(n):
    ids = list(range(1, n + 1))
    rounds = round_robin(ids)
    pares = [frozenset(m) for r in rounds for m in r]
    assert len(pares) == len(set(pares)) == n * (n - 1) // 2
    assert set(pares) == {frozenset(c) for c in combinations(ids, 2)}


@pytest.mark.parametrize("n", [4, 5, 8])
def test_un_equipo_juega_una_vez_por_fecha(n):
    for rnd in round_robin(list(range(n))):
        jugadores = [t for m in rnd for t in m]
        assert len(jugadores) == len(set(jugadores))


def test_cantidad_de_fechas():
    assert len(round_robin(list(range(6)))) == 5
    assert len(round_robin(list(range(5)))) == 5  # impar: uno descansa


def test_ida_y_vuelta_invierte_localia():
    r = round_robin([1, 2, 3, 4], double=True)
    assert len(r) == 6
    ida = {m for rnd in r[:3] for m in rnd}
    vuelta = {m for rnd in r[3:] for m in rnd}
    assert vuelta == {(b, a) for a, b in ida}


def test_ids_repetidos():
    with pytest.raises(ValueError):
        round_robin([1, 1, 2])


def test_menos_de_dos():
    assert round_robin([1]) == []
