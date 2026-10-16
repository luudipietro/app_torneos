from domain.discipline import Card, DisciplineRules, discipline_status

Y = lambda p: Card(p, "yellow")
R = lambda p: Card(p, "red")
SY = lambda p: Card(p, "second_yellow")


def test_sin_historia():
    assert discipline_status([]) == ({}, {})


def test_acumulacion_de_amarillas():
    sus, run = discipline_status([[Y(1)], [Y(1)]])
    assert sus == {} and run == {1: 2}
    sus, run = discipline_status([[Y(1)], [Y(1)], [Y(1)]])
    assert sus[1].remaining == 1 and sus[1].reason == "yellows"
    assert run[1] == 0  # el contador vuelve a empezar


def test_cumple_la_fecha_y_vuelve():
    # 3 amarillas, luego un partido sentado, el siguiente ya puede jugar
    sus, _ = discipline_status([[Y(1)], [Y(1)], [Y(1)], []])
    assert sus == {}


def test_roja_directa():
    sus, _ = discipline_status([[R(2)]])
    assert sus[2].reason == "red" and sus[2].remaining == 1
    assert discipline_status([[R(2)], []])[0] == {}


def test_roja_de_varias_fechas():
    rules = DisciplineRules(red_matches=3)
    assert discipline_status([[R(2)], []], rules)[0][2].remaining == 2
    assert discipline_status([[R(2)], [], [], []], rules)[0] == {}


def test_doble_amarilla_es_roja_y_no_acumula():
    sus, run = discipline_status([[Y(3), SY(3)]])
    assert sus[3].reason == "red"
    assert run == {3: 1}


def test_tarjeta_durante_la_sancion_se_acumula():
    # roja en F1, en F2 (sentado) nada; amarillas posteriores siguen contando
    sus, run = discipline_status([[R(1)], [], [Y(1)]])
    assert sus == {} and run == {1: 1}


def test_regla_personalizada_y_sin_acumulacion():
    rules = DisciplineRules(yellows_for_suspension=2)
    assert 1 in discipline_status([[Y(1)], [Y(1)]], rules)[0]
    off = DisciplineRules(yellows_for_suspension=0)
    sus, run = discipline_status([[Y(1)]] * 10, off)
    assert sus == {} and run == {1: 10}


def test_jugadores_independientes():
    assert discipline_status([[R(1), Y(2)]])[0].keys() == {1}
    assert 1 not in discipline_status([[R(1), Y(2)], [Y(2)]])[0]  # 1 ya cumplió su fecha
