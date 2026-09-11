"""Reporte diario (7:00 GT): data/reportes/AAAA-MM-DD.md, data/reportes/ultimo.json y evaluación de los martes
(qué publicó el MEM vs qué predijimos) en data/aciertos.json.
"""
from __future__ import annotations

from datetime import date, timedelta

from agente.comun import DATA, ahora_gt, fecha_bonita, guardar_json, leer_json, log
from bot import plantillas as P

RUTA_REPORTES = DATA / "reportes"
RUTA_ACIERTOS = DATA / "aciertos.json"
UMBRAL_REAL_Q = 0.10  # cambio real del MEM por encima del cual se considera alza/baja
MIN_SEMANAS = 4


def q(v) -> str:
    return "–" if v is None else f"Q{float(v):.2f}"


def _pct(v) -> str:
    return "–" if v is None else f"{v:+.1f} %"


def precios_vigentes(precios: dict, hoy: dict | None = None) -> tuple[dict, str, str]:
    """(precios {superior, regular, diesel}, fecha, fuente): el dato más reciente entre el informe del MEM
    y lo observado hoy en medios (data/precio_hoy.json)."""
    auto = dict((precios or {}).get("autoservicio", {}))
    fecha = (precios or {}).get("fecha_monitoreo") or ""
    fuente = (precios or {}).get("fuente") or "MEM"
    hoy = hoy if hoy is not None else (leer_json(DATA / "precio_hoy.json", {}) or {})
    u = hoy.get("ultimo") or {}
    fechas = [u[p]["fecha"] for p in ("superior", "regular", "diesel") if p in u]
    if fechas and max(fechas) > fecha:
        auto = {p: u[p]["valor"] for p in ("superior", "regular", "diesel") if p in u}
        fecha = max(fechas)
        fuente = "medios: " + ", ".join(sorted({u[p]["fuente"] for p in u}))
    return auto, fecha, fuente


def departamentos_vigentes(deptos: dict) -> dict:
    """La estimación de hoy (data/departamentos_hoy.json) si existe; si no, la tabla oficial."""
    hoy = leer_json(DATA / "departamentos_hoy.json", {}) or {}
    return hoy if hoy.get("departamentos") else (deptos or {})


def datos_mensaje(senal: dict, precios: dict, deptos: dict, noticias: dict) -> dict:
    """Diccionario con todas las variables que usan las plantillas."""
    auto, fecha_mem, _ = precios_vigentes(precios)
    deptos = departamentos_vigentes(deptos)
    barato = (deptos or {}).get("mas_barato") or {}
    caro = (deptos or {}).get("mas_caro") or {}
    # Titulares en español primero (o traducidos por Claude); las que mueven el precio antes que las neutrales.
    lista = (noticias or {}).get("noticias", [])[:20]
    lista = sorted(lista, key=lambda n: -((2 if n.get("etiqueta") != "NEUTRAL" else 0) + (1 if n.get("idioma") == "es" or n.get("titulo_es") else 0)))
    titulares = [n.get("titulo_es") or n["titulo"] for n in lista[:3]]
    det = (senal or {}).get("detalle", {})
    return {
        "emoji": senal.get("emoji", "🟡"),
        "veredicto": senal.get("veredicto", "Calibrando"),
        "cambio": senal.get("cambio_estimado_texto", ""),
        "superior": q(auto.get("superior")),
        "regular": q(auto.get("regular")),
        "diesel": q(auto.get("diesel")),
        "razon": senal.get("razon", ""),
        "depto_barato": barato.get("departamento", "–"),
        "cabecera_barata": barato.get("cabecera", "–"),
        "precio_barato": q(barato.get("regular")),
        "depto_caro": caro.get("departamento", "–"),
        "precio_caro": q(caro.get("regular")),
        "noticias": " · ".join(t[:60] for t in titulares) or "sin novedades",
        "fecha": ahora_gt().date().isoformat(),
        "fecha_mem": fecha_bonita(fecha_mem),
        "puntaje": f"{senal.get('puntaje', 0):+d}" if isinstance(senal.get("puntaje"), int) else "–",
        "proximo_martes": fecha_bonita(senal.get("proximo_martes")),
        "rbob_pct": _pct(det.get("rbob_cambio_7d_pct")),
        "fx_pct": _pct(det.get("usdgtq_cambio_7d_pct")),
        "n_alza": det.get("noticias_alza_7d", 0),
        "n_baja": det.get("noticias_baja_7d", 0),
    }


def mensaje_corto(senal: dict, precios: dict, deptos: dict, noticias: dict) -> str:
    return P.MENSAJE_DIARIO.format(**datos_mensaje(senal, precios, deptos, noticias))


# ----------------------------------------------------------------------------- martes
def direccion_real(cambio_q: float | None) -> str | None:
    if cambio_q is None:
        return None
    return "alza" if cambio_q > UMBRAL_REAL_Q else "baja" if cambio_q < -UMBRAL_REAL_Q else "estable"


def evaluar_martes(hoy: date, precios: dict, historial_senal: list[dict]) -> dict:
    """Compara la señal del lunes (o la última antes del martes) con el cambio real que publicó el MEM."""
    aciertos = leer_json(RUTA_ACIERTOS, {}) or {}
    semanas = [s for s in aciertos.get("semanas", []) if s.get("fecha_martes") != hoy.isoformat()]
    previas = [h for h in historial_senal if h["fecha"] < hoy.isoformat()]
    predicho = previas[-1] if previas else None
    fecha_mem = (precios or {}).get("fecha_monitoreo") or ""
    fresco = fecha_mem >= (hoy - timedelta(days=6)).isoformat()
    cambio_real = (precios or {}).get("cambio_semanal", {}).get("regular") if fresco else None
    real = direccion_real(cambio_real)
    fila = {
        "fecha_martes": hoy.isoformat(),
        "predicho": predicho["tendencia"] if predicho else None,
        "cambio_predicho_q": predicho.get("cambio_estimado_q") if predicho else None,
        "fecha_mem": fecha_mem if fresco else None,
        "cambio_real_q": cambio_real,
        "real": real,
        "acierto": (predicho["tendencia"] == real) if (predicho and real) else None,
    }
    semanas.append(fila)
    semanas = semanas[-52:]
    evaluadas = [s for s in semanas if s.get("acierto") is not None]
    n_ok = sum(1 for s in evaluadas if s["acierto"])
    salida = {
        "actualizado": ahora_gt().isoformat(timespec="minutes"),
        "semanas": semanas,
        "total": len(evaluadas),
        "aciertos": n_ok,
        "porcentaje": round(100 * n_ok / len(evaluadas)) if evaluadas else None,
        "estado": "ok" if len(evaluadas) >= MIN_SEMANAS else "calibrando",
    }
    guardar_json(RUTA_ACIERTOS, salida)
    return fila


def texto_martes(fila: dict) -> str:
    nombres = {"alza": "alza", "baja": "baja", "estable": "sin cambio"}
    predicho = nombres.get(fila.get("predicho"), "nada")
    if fila.get("real") is None:
        return P.MENSAJE_MARTES.format(real="(pendiente)", predicho=predicho, resultado=P.RESULTADO_SIN_DATO)
    real = f"{nombres[fila['real']]} ({fila['cambio_real_q']:+.2f} Q/gal)"
    resultado = P.RESULTADO_ACIERTO if fila.get("acierto") else P.RESULTADO_FALLO
    return P.MENSAJE_MARTES.format(real=real, predicho=predicho, resultado=resultado)


# ----------------------------------------------------------------------------- generación
def generar(hoy: date | None = None) -> dict:
    hoy = hoy or ahora_gt().date()
    senal = leer_json(DATA / "senal.json", {}) or {}
    precios = leer_json(DATA / "precios.json", {}) or {}
    deptos = leer_json(DATA / "departamentos.json", {}) or {}
    noticias = leer_json(DATA / "noticias.json", {}) or {}
    historial = leer_json(DATA / "senal_historial.json", []) or []
    if not senal:
        log("Reporte: no hay señal todavía; no se genera", "WARN")
        return {}

    datos = datos_mensaje(senal, precios, deptos, noticias)
    datos["fecha"] = hoy.isoformat()
    mensaje = P.MENSAJE_DIARIO.format(**datos)
    seccion_martes = ""
    if hoy.weekday() == 1:
        fila = evaluar_martes(hoy, precios, historial)
        seccion_martes = "## Martes: MEM vs. predicción\n" + texto_martes(fila)
        mensaje = mensaje + "\n" + texto_martes(fila) if len(mensaje.splitlines()) < 5 else mensaje

    noticias_md = "\n".join(
        f"- **{n['etiqueta']}** [{n['titulo']}]({n['url']}) — {n.get('razon', '')} ({n['fuente']})"
        for n in noticias.get("noticias", [])[:3]
    ) or "- Sin novedades."
    md = P.REPORTE_MD.format(noticias_md=noticias_md, seccion_martes=seccion_martes, **datos)
    RUTA_REPORTES.mkdir(parents=True, exist_ok=True)
    (RUTA_REPORTES / f"{hoy.isoformat()}.md").write_text(md, encoding="utf-8")
    ultimo = {"fecha": hoy.isoformat(), "mensaje": mensaje, "veredicto": senal.get("veredicto"), "puntaje": senal.get("puntaje"),
              "emoji": senal.get("emoji"), "generado": ahora_gt().isoformat(timespec="minutes")}
    guardar_json(RUTA_REPORTES / "ultimo.json", ultimo)
    log("Reporte diario generado:\n" + mensaje)
    return ultimo


if __name__ == "__main__":  # pragma: no cover
    generar()
