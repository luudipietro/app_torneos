import pytest

from domain.groups import draw_groups, layout_for, suggest_layouts
from domain.team import Team


def equipos(n, seeds=0):
    return [Team(f"E{i}", i, seed=(i if i <= seeds else None)) for i in range(1, n + 1)]


def test_layout_desparejo():
    assert layout_for(10, 3).sizes == (4, 3, 3)


@pytest.mark.parametrize("n", range(4, 65))
def test_hay_sugerencias_o_se_explica(n):
    # toda cantidad >= 6 tiene al menos una distribución; no explota en ninguna
    s = suggest_layouts(n)
    assert all(sum(l.sizes) == n for l in s)
    if n >= 6:
        assert s


def test_sugerencias_64():
    s = suggest_layouts(64)
    primero = s[0]
    assert primero.balanced
    assert (primero.n_groups, primero.sizes[0]) in {(16, 4), (8, 8)}
    assert any(l.n_groups == 16 and l.sizes[0] == 4 for l in s)


def test_limites():
    with pytest.raises(ValueError):
        suggest_layouts(65)
    with pytest.raises(ValueError):
        layout_for(4, 5)


def test_sorteo_reproducible_y_completo():
    t = equipos(64)
    a = draw_groups(t, 16, seed=7)
    b = draw_groups(t, 16, seed=7)
    assert a == b
    assert all(len(g) == 4 for g in a)
    assert {x.id for g in a for x in g} == {x.id for x in t}


def test_cabezas_de_serie_en_grupos_distintos():
    g = draw_groups(equipos(16, seeds=4), 4, seed=1)
    assert all(sum(1 for x in grp if x.seed) == 1 for grp in g)


def test_sorteo_impar():
    g = draw_groups(equipos(10), 3, seed=3)
    assert sorted(len(x) for x in g) == [3, 3, 4]
