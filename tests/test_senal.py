from agente import senal


def mercado(rb_pct, fx_pct=0.0, rb_abs=0.0, tc=7.7):
    return {"ultimo": {"RB=F": {"precio": 2.5, "cambio_7d_pct": rb_pct, "cambio_7d_abs": rb_abs},
                       "GTQ=X": {"precio": tc, "cambio_7d_pct": fx_pct}}}


def noticias(alza=0, baja=0):
    return {"balance_7d": {"ALZA": alza, "BAJA": baja, "NEUTRAL": 0}}


def test_alza_fuerte_dice_llena_hoy():
    s = senal.calcular(mercado(4.0, 0.5, rb_abs=0.10), noticias(3, 0))
    assert s["tendencia"] == "alza" and s["veredicto"] == "Llena HOY" and s["emoji"] == "🔴"
    assert s["puntaje"] == 40 + 10 + 15
    assert s["cambio_estimado_q"] == 0.65  # 0.10 * 7.7 * 0.85 = 0.65 -> redondeado a 0.05
    assert s["cambio_estimado_texto"].startswith("Sube ~Q0.65")


def test_baja_dice_espera():
    s = senal.calcular(mercado(-3.0, -0.2, rb_abs=-0.08), noticias(0, 2))
    assert s["tendencia"] == "baja" and s["veredicto"] == "Espera" and s["emoji"] == "🟢"
    assert s["puntaje"] == -30 - 4 - 10
    assert s["cambio_estimado_texto"].startswith("Baja ~Q0.5")


def test_estable_dice_llena_esta_semana():
    s = senal.calcular(mercado(0.5), noticias(1, 1))
    assert s["tendencia"] == "estable" and s["veredicto"] == "Llena esta semana"
    assert s["cambio_estimado_texto"] == "Se mantiene el martes."


def test_saturacion_de_componentes():
    s = senal.calcular(mercado(15.0, 5.0), noticias(20, 0))
    assert s["componentes"] == {"gasolina_eeuu": 60.0, "dolar": 20.0, "noticias": 20.0}
    assert s["puntaje"] == 100


def test_sin_datos_no_rompe():
    s = senal.calcular({}, {})
    assert s["puntaje"] == 0 and s["tendencia"] == "estable"


def test_razon_simple_sin_tickers():
    s = senal.calcular(mercado(3.2, 0.6), noticias(2, 0))
    r = senal.razon_simple(s)
    assert "RBOB" not in r and "WTI" not in r
    assert "gasolina en EE.UU." in r and "subió 3%" in r
