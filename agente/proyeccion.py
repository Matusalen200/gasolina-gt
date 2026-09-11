"""Proyección a 4 semanas del precio MEM (regular, súper, diésel).

Modelo: regresión lineal (mínimos cuadrados, sin numpy) del precio MEM de la semana t contra
  x1 = RBOB (US$/gal) x USD/GTQ de la semana t-1
  x2 = WTI (US$/barril) de la semana t-1
  x3 = RBOB x USD/GTQ de la semana t-2
Validación walk-forward: para cada semana i se entrena con las semanas anteriores y se predice i;
se reporta el error absoluto medio (MAE) en Q/galón. Con menos de MIN_SEMANAS pares MEM/mercado
el modelo no se usa; se aplica un traslado simple (cambio de RBOB x tipo de cambio x 0.85) y se
marca estado "calibrando". El rango es ± max(Q0.50, 1.5 x MAE) x sqrt(horizonte).
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from agente.comun import DATA, ahora_gt, guardar_json, leer_json, log

RUTA = DATA / "proyeccion.json"
MIN_SEMANAS = 10
TRASLADO = 0.85
PRODUCTOS = ("regular", "superior", "diesel")


# ----------------------------------------------------------------------------- álgebra mínima
def resolver(A: list[list[float]], b: list[float]) -> list[float] | None:
    """Resuelve A x = b por eliminación gaussiana con pivoteo. None si es singular."""
    n = len(b)
    M = [fila[:] + [b[i]] for i, fila in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return None
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def ajustar(X: list[list[float]], y: list[float]) -> list[float] | None:
    """Coeficientes OLS (con intercepto) o None."""
    Xi = [[1.0] + fila for fila in X]
    k = len(Xi[0])
    A = [[sum(f[i] * f[j] for f in Xi) for j in range(k)] for i in range(k)]
    b = [sum(f[i] * yi for f, yi in zip(Xi, y)) for i in range(k)]
    for i in range(k):  # regularización mínima (ridge) para estabilidad con pocas semanas
        A[i][i] += 1e-6 * (1 if i == 0 else A[i][i])
    return resolver(A, b)


def predecir(coef: list[float], x: list[float]) -> float:
    return coef[0] + sum(c * v for c, v in zip(coef[1:], x))


# ----------------------------------------------------------------------------- datos
def _semanal(serie: list[dict]) -> dict[str, float]:
    """{fecha_iso (lunes de la semana): cierre} a partir de una serie de cierres semanales."""
    out = {}
    for p in serie:
        d = datetime.fromisoformat(p["t"]).date()
        lunes = d - timedelta(days=d.weekday())
        out[lunes.isoformat()] = p["p"]
    return out


def _valor_semana(sem: dict[str, float], lunes: date, rezago: int) -> float | None:
    """Valor de la semana `rezago` semanas antes de `lunes` (busca hasta 2 semanas atrás si falta)."""
    for extra in range(0, 3):
        k = (lunes - timedelta(weeks=rezago + extra)).isoformat()
        if k in sem:
            return sem[k]
    return None


def construir_pares(historial: list[dict], mercado: dict) -> tuple[list[date], list[list[float]], dict[str, list[float]]]:
    rb, cl, fx = (_semanal(mercado.get("series", {}).get(s, [])) for s in ("RB=F", "CL=F", "GTQ=X"))
    fechas, X, Y = [], [], {p: [] for p in PRODUCTOS}
    for h in historial:
        if not all(h.get(p) for p in PRODUCTOS):
            continue
        d = date.fromisoformat(h["fecha"])
        lunes = d - timedelta(days=d.weekday())
        r1, c1, f1, r2, f2 = (_valor_semana(rb, lunes, 1), _valor_semana(cl, lunes, 1), _valor_semana(fx, lunes, 1),
                              _valor_semana(rb, lunes, 2), _valor_semana(fx, lunes, 2))
        if None in (r1, c1, f1, r2, f2):
            continue
        fechas.append(lunes)
        X.append([r1 * f1, c1, r2 * f2])
        for p in PRODUCTOS:
            Y[p].append(float(h[p]))
    return fechas, X, Y


def walk_forward(X: list[list[float]], y: list[float], minimo: int = 6) -> dict:
    errores = []
    for i in range(minimo, len(y)):
        coef = ajustar(X[:i], y[:i])
        if coef is None:
            continue
        errores.append(abs(predecir(coef, X[i]) - y[i]))
    return {"n_pruebas": len(errores), "mae": round(sum(errores) / len(errores), 3) if errores else None,
            "max": round(max(errores), 3) if errores else None}


# ----------------------------------------------------------------------------- proyección
def actualizar() -> dict:
    historial = leer_json(DATA / "precios_historial.json", []) or []
    mercado = leer_json(DATA / "mercado_semanal.json", {}) or {}
    horario = leer_json(DATA / "mercado_horario.json", {}) or {}
    precios = leer_json(DATA / "precios.json", {}) or {}
    if not historial or not mercado.get("series"):
        log("Proyección: faltan historial MEM o mercado semanal", "WARN")
        return {}

    fechas, X, Y = construir_pares(historial, mercado)
    n = len(fechas)
    ultimo = horario.get("ultimo", {})
    rb_now = (ultimo.get("RB=F") or {}).get("precio")
    cl_now = (ultimo.get("CL=F") or {}).get("precio")
    fx_now = (ultimo.get("GTQ=X") or {}).get("precio") or precios.get("tipo_cambio") or 7.7
    rb_sem = _semanal(mercado["series"].get("RB=F", []))
    rb_hace1 = _valor_semana(rb_sem, ahora_gt().date() - timedelta(days=ahora_gt().date().weekday()), 1)

    base = {p: float(historial[-1].get(p) or 0) for p in PRODUCTOS}
    fecha_base = date.fromisoformat(historial[-1]["fecha"])
    proximo_martes = ahora_gt().date() + timedelta(days=(1 - ahora_gt().date().weekday()) % 7 or 7)

    validacion = {p: walk_forward(X, Y[p]) for p in PRODUCTOS} if n >= MIN_SEMANAS else {}
    mae = (validacion.get("regular") or {}).get("mae")
    usar_modelo = n >= MIN_SEMANAS and mae is not None and rb_now and cl_now
    coefs = {p: ajustar(X, Y[p]) for p in PRODUCTOS} if usar_modelo else {}
    if usar_modelo and any(c is None for c in coefs.values()):
        usar_modelo = False

    semanas = []
    for k in range(1, 5):
        fecha = proximo_martes + timedelta(weeks=k - 1)
        fila = {"fecha": fecha.isoformat()}
        if usar_modelo:
            # Semana 1 usa el mercado de esta semana (rezago 1) y la anterior (rezago 2); después, persistencia.
            x = [rb_now * fx_now, cl_now, (rb_hace1 or rb_now) * fx_now] if k == 1 else [rb_now * fx_now, cl_now, rb_now * fx_now]
            for p in PRODUCTOS:
                fila[p] = round(predecir(coefs[p], x), 2)
            ancho = max(0.5, 1.5 * mae) * math.sqrt(k)
        else:
            delta = ((rb_now or 0) - (rb_hace1 or rb_now or 0)) * fx_now * TRASLADO if rb_now else 0.0
            for p in PRODUCTOS:
                fila[p] = round(base[p] + delta, 2)
            ancho = 0.75 * math.sqrt(k)
        fila["rango_bajo"] = round(fila["regular"] - ancho, 2)
        fila["rango_alto"] = round(fila["regular"] + ancho, 2)
        semanas.append(fila)

    if usar_modelo:
        nota = (f"Regresión sobre {n} semanas de datos del MEM. Error medio en validación walk-forward: "
                f"Q{mae:.2f} por galón (regular). El rango sombreado crece con el horizonte.")
        estado = "ok"
    else:
        nota = (f"Calibrando: solo hay {n} semanas con datos del MEM y de mercado (se necesitan {MIN_SEMANAS}). "
                f"Mientras tanto se muestra un traslado simple del cambio de la gasolina en EE.UU. "
                f"desde el último dato del MEM ({fecha_base.isoformat()}).")
        estado = "calibrando"
    salida = {
        "actualizado": ahora_gt().isoformat(timespec="minutes"),
        "estado": estado,
        "metodo": "regresion_rezago_1_2" if usar_modelo else "traslado_simple",
        "n_semanas": n,
        "fecha_base": fecha_base.isoformat(),
        "base": base,
        "validacion": validacion,
        "error_medio_q": mae,
        "coeficientes": {p: [round(c, 4) for c in coefs[p]] for p in PRODUCTOS} if usar_modelo else None,
        "semanas": semanas,
        "nota": nota,
    }
    guardar_json(RUTA, salida)
    log(f"Proyección ({estado}, n={n}, MAE={mae}): regular {[s['regular'] for s in semanas]}")
    return salida


if __name__ == "__main__":  # pragma: no cover
    actualizar()
