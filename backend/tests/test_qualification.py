import pytest

from domain.knockout import build_bracket
from domain.qualification import (
    CupSpec, assign_cups, avoid_same_group, entrants_from_tables, suggest_cup_plans,
)
from domain.standings import Row


def tables(n_groups, size, strength=None):
    """Tablas ordenadas; el equipo (g, p) tiene id g*100+p. 'strength' ajusta puntos por grupo."""
    out = {}
    for g in range(1, n_groups + 1):
        rows = []
        for p in range(1, size + 1):
            pts = (size - p) * 3 + (strength(g) if strength else 0)
            rows.append(Row(team=g * 100 + p, points=pts, gf=10 - p, ga=p))
        out[g] = rows
    return out


def test_dos_primeros_de_16_grupos_son_32_sembrados():
    ents = entrants_from_tables(tables(16, 4))
    (cup,) = assign_cups(ents, [CupSpec("Oro", (1, 2))])
    assert len(cup) == 32
    assert all(e.position == 1 for e in cup[:16]) and all(e.position == 2 for e in cup[16:])


def test_siembra_por_rendimiento_dentro_del_puesto():
    # el grupo 3 es más fuerte: su primero debe ser serie 1
    ents = entrants_from_tables(tables(4, 3, strength=lambda g: 5 if g == 3 else 0))
    (cup,) = assign_cups(ents, [CupSpec("Oro", (1,))])
    assert cup[0].group == 3


def test_mejores_terceros_y_copa_de_plata_48_equipos():
    ents = entrants_from_tables(tables(12, 4, strength=lambda g: g))  # grupos más altos = más fuertes
    oro, plata = assign_cups(ents, [CupSpec("Oro", (1, 2), ((3, 8),)), CupSpec("Plata", (3, 4))])
    assert len(oro) == 32 and len(plata) == 16
    thirds_oro = [e for e in oro if e.position == 3]
    assert len(thirds_oro) == 8 and {e.group for e in thirds_oro} == set(range(5, 13))  # los 8 mejores
    assert {e.team for e in oro}.isdisjoint({e.team for e in plata})
    assert len({e.team for e in oro + plata}) == 48  # nadie queda afuera
    assert [e.position for e in plata][:4] == [3, 3, 3, 3] and {e.group for e in plata if e.position == 3} == {1, 2, 3, 4}


def test_errores_de_configuracion():
    ents = entrants_from_tables(tables(4, 4))
    with pytest.raises(ValueError):
        assign_cups(ents, [CupSpec("Oro", (1,), ((2, 9),))])  # solo hay 4 segundos
    with pytest.raises(ValueError):
        assign_cups(ents, [CupSpec("Oro", (1, 2), ((2, 1),))])  # puesto repetido


def test_evitar_cruces_del_mismo_grupo():
    ents = entrants_from_tables(tables(8, 4))
    (cup,) = assign_cups(ents, [CupSpec("Oro", (1, 2))])  # 16 equipos
    ms = build_bracket(16)

    def clashes(teams):
        return sum(1 for m in ms if m.round == 1 and teams[m.home.value - 1].group == teams[m.away.value - 1].group)

    fixed = avoid_same_group(cup, ms)
    assert clashes(fixed) == 0
    assert sorted(e.team for e in fixed) == sorted(e.team for e in cup)  # mismos equipos
    assert fixed[:8] == cup[:8]  # los cabezas de serie no se mueven


def test_evitar_cruces_grupos_chicos():
    ents = entrants_from_tables(tables(4, 2))
    (cup,) = assign_cups(ents, [CupSpec("Oro", (1, 2))])
    ms = build_bracket(8)
    fixed = avoid_same_group(cup, ms)
    assert all(fixed[m.home.value - 1].group != fixed[m.away.value - 1].group for m in ms if m.round == 1)


def test_sugerencias_16_grupos_de_4():
    plans = suggest_cup_plans(16, 4)
    labels = [p.label for p in plans]
    assert "Los 2 primeros de cada grupo" in labels
    con_plata = next(p for p in plans if p.label == "Los 2 primeros de cada grupo · con Copa de Plata")
    assert [c.name for c in con_plata.cups] == ["Copa de Oro", "Copa de Plata"]
    assert con_plata.cups[1].positions == (3, 4)


def test_sugerencias_12_grupos_de_4_incluyen_mejores_terceros():
    plans = {p.label: p for p in suggest_cup_plans(12, 4)}
    p = plans["Los 2 primeros de cada grupo + los 8 mejores 3º"]
    assert p.cups[0].extra == ((3, 8),)
    ents = entrants_from_tables(tables(12, 4))
    oro, plata = assign_cups(ents, list(plans["Los 2 primeros de cada grupo + los 8 mejores 3º · con Copa de Plata"].cups))
    assert (len(oro), len(plata)) == (32, 16)


def test_todas_las_sugerencias_son_ejecutables():
    for g, s in [(2, 4), (4, 4), (6, 4), (8, 4), (12, 4), (16, 4), (8, 8), (3, 3), (10, 5), (5, 6)]:
        ents = entrants_from_tables(tables(g, s))
        for plan in suggest_cup_plans(g, s):
            cups = assign_cups(ents, list(plan.cups))
            assert all(2 <= len(c) <= 64 for c in cups), (g, s, plan.label)
