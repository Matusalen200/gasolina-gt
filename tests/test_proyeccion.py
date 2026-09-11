import random

from agente import proyeccion


def test_resolver_sistema_simple():
    x = proyeccion.resolver([[2.0, 1.0], [1.0, 3.0]], [5.0, 10.0])
    assert abs(x[0] - 1.0) < 1e-9 and abs(x[1] - 3.0) < 1e-9


def test_ajuste_recupera_coeficientes_conocidos():
    random.seed(1)
    X, y = [], []
    for _ in range(60):
        r, c, r2 = random.uniform(15, 30), random.uniform(60, 110), random.uniform(15, 30)
        X.append([r, c, r2])
        y.append(3.0 + 0.9 * r + 0.05 * c + 0.1 * r2 + random.gauss(0, 0.05))
    coef = proyeccion.ajustar(X, y)
    assert abs(coef[1] - 0.9) < 0.05 and abs(coef[2] - 0.05) < 0.02 and abs(coef[3] - 0.1) < 0.05
    wf = proyeccion.walk_forward(X, y)
    assert wf["n_pruebas"] == 54 and wf["mae"] < 0.15


def test_singular_devuelve_none():
    assert proyeccion.resolver([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0]) is None


def test_construir_pares_alinea_por_lunes():
    historial = [{"fecha": "2026-01-19", "regular": 26.5, "superior": 27.5, "diesel": 25.1}]
    mercado = {"series": {
        "RB=F": [{"t": "2026-01-05T00:00+00:00", "p": 2.0}, {"t": "2026-01-12T00:00+00:00", "p": 2.1}],
        "CL=F": [{"t": "2026-01-05T00:00+00:00", "p": 70.0}, {"t": "2026-01-12T00:00+00:00", "p": 72.0}],
        "GTQ=X": [{"t": "2026-01-05T00:00+00:00", "p": 7.7}, {"t": "2026-01-12T00:00+00:00", "p": 7.7}],
    }}
    fechas, X, Y = proyeccion.construir_pares(historial, mercado)
    assert len(fechas) == 1 and fechas[0].isoformat() == "2026-01-19"
    assert X[0] == [2.1 * 7.7, 72.0, 2.0 * 7.7] and Y["regular"] == [26.5]
