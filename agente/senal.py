"""Señal: combina mercado y noticias en un puntaje de -100 a +100 y un veredicto.

REGLA (explícita, documentada en el README; Claude solo redacta la razón, nunca decide):
  c_gasolina = limitar(cambio_7d_pct_RBOB * 10, -60, 60)      # 6 % en una semana satura
  c_dolar    = limitar(cambio_7d_pct_USDGTQ * 20, -20, 20)    # 1 % de depreciación del quetzal = +20
  c_noticias = limitar((n_ALZA - n_BAJA) * 5, -20, 20)        # noticias de los últimos 7 días
  puntaje    = limitar(c_gasolina + c_dolar + c_noticias, -100, 100)

  puntaje >= +15  -> tendencia "alza"    -> veredicto "Llena HOY"          -> 🔴
  puntaje <= -15  -> tendencia "baja"    -> veredicto "Espera"             -> 🟢
  en medio        -> tendencia "estable" -> veredicto "Llena esta semana"  -> 🟡

  Cambio estimado del martes (Q/galón) = cambio_7d_abs_RBOB (US$/gal) * tipo_cambio * 0.85 (traslado
  típico al surtidor), redondeado a Q0.05.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from agente.comun import DATA, MODELO_CLAUDE, ahora_gt, cliente_claude, guardar_json, leer_json, log

RUTA = DATA / "senal.json"
RUTA_HISTORIAL = DATA / "senal_historial.json"
UMBRAL = 15
TRASLADO = 0.85
TIPO_CAMBIO_DEFECTO = 7.70


def limitar(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def calcular(mercado: dict, noticias: dict, tipo_cambio: float | None = None) -> dict:
    """Función pura: regla de puntaje. Se prueba en tests/test_senal.py."""
    u = (mercado or {}).get("ultimo", {})
    rb = u.get("RB=F", {}) or {}
    fx = u.get("GTQ=X", {}) or {}
    r7 = rb.get("cambio_7d_pct") or 0.0
    f7 = fx.get("cambio_7d_pct") or 0.0
    bal = (noticias or {}).get("balance_7d", {}) or {}
    n_alza, n_baja = bal.get("ALZA", 0), bal.get("BAJA", 0)

    c_gas = limitar(r7 * 10, -60, 60)
    c_fx = limitar(f7 * 20, -20, 20)
    c_not = limitar((n_alza - n_baja) * 5, -20, 20)
    puntaje = int(round(limitar(c_gas + c_fx + c_not, -100, 100)))

    if puntaje >= UMBRAL:
        tendencia, veredicto, emoji = "alza", "Llena HOY", "🔴"
    elif puntaje <= -UMBRAL:
        tendencia, veredicto, emoji = "baja", "Espera", "🟢"
    else:
        tendencia, veredicto, emoji = "estable", "Llena esta semana", "🟡"

    tc = tipo_cambio or fx.get("precio") or TIPO_CAMBIO_DEFECTO
    cambio_q = round((rb.get("cambio_7d_abs") or 0.0) * tc * TRASLADO / 0.05) * 0.05
    if abs(cambio_q) < 0.05:
        cambio_txt = "Se mantiene el martes."
    else:
        cambio_txt = f"{'Sube' if cambio_q > 0 else 'Baja'} ~Q{abs(cambio_q):.2f} el martes."

    return {
        "puntaje": puntaje,
        "tendencia": tendencia,
        "veredicto": veredicto,
        "emoji": emoji,
        "cambio_estimado_q": round(cambio_q, 2),
        "cambio_estimado_texto": cambio_txt,
        "componentes": {"gasolina_eeuu": round(c_gas, 1), "dolar": round(c_fx, 1), "noticias": round(c_not, 1)},
        "detalle": {"rbob_cambio_7d_pct": r7, "usdgtq_cambio_7d_pct": f7, "noticias_alza_7d": n_alza, "noticias_baja_7d": n_baja,
                    "rbob_precio": rb.get("precio"), "usdgtq": fx.get("precio"), "tipo_cambio_usado": tc},
    }


def razon_simple(s: dict) -> str:
    """Una línea en palabras simples, sin tickers."""
    d = s["detalle"]
    partes = []
    r7 = d["rbob_cambio_7d_pct"]
    if abs(r7) >= 1:
        partes.append(f"La gasolina en EE.UU. {'subió' if r7 > 0 else 'bajó'} {abs(r7):.0f}% esta semana")
    else:
        partes.append("La gasolina en EE.UU. casi no se movió esta semana")
    f7 = d["usdgtq_cambio_7d_pct"]
    if abs(f7) >= 0.4:
        partes.append(f"el dólar {'subió' if f7 > 0 else 'bajó'}")
    na, nb = d["noticias_alza_7d"], d["noticias_baja_7d"]
    if na or nb:
        if na > nb:
            partes.append("las noticias empujan hacia arriba")
        elif nb > na:
            partes.append("las noticias empujan hacia abajo")
    return (", ".join(partes) + ".").replace(", las", " y las")


def razon_claude(s: dict, noticias: dict) -> str | None:
    cliente = cliente_claude()
    if cliente is None:
        return None
    titulares = "\n".join(f"- [{n['etiqueta']}] {n['titulo']}" for n in (noticias or {}).get("noticias", [])[:8])
    try:
        r = cliente.messages.create(
            model=MODELO_CLAUDE,
            max_tokens=200,
            system=(
                "Redactas para conductores guatemaltecos que leen en el celular. Escribe UNA sola oración (máximo 18 palabras) "
                "que explique en palabras simples por qué la gasolina va a subir, bajar o mantenerse el próximo martes. "
                "Prohibido: porcentajes con decimales, tickers (RBOB, WTI), tecnicismos. Usa 'petróleo', 'gasolina en EE.UU.', 'dólar'. "
                "No decidas el veredicto: ya está decidido; solo explica."
            ),
            messages=[{"role": "user", "content": (
                f"Veredicto: {s['veredicto']} ({s['tendencia']}, puntaje {s['puntaje']}). {s['cambio_estimado_texto']}\n"
                f"Gasolina EE.UU. 7 días: {s['detalle']['rbob_cambio_7d_pct']}%. Dólar 7 días: {s['detalle']['usdgtq_cambio_7d_pct']}%. "
                f"Noticias 7 días: {s['detalle']['noticias_alza_7d']} al alza, {s['detalle']['noticias_baja_7d']} a la baja.\n{titulares}"
            )}],
        )
        texto = " ".join(b.text for b in r.content if b.type == "text").strip()
        return texto.splitlines()[0][:160] if texto else None
    except Exception as e:
        log(f"Claude no redactó la razón ({type(e).__name__}); uso plantilla", "WARN")
        return None


def proximo_martes(desde: datetime) -> str:
    dias = (1 - desde.weekday()) % 7 or 7
    return (desde + timedelta(days=dias)).date().isoformat()


def actualizar() -> dict:
    mercado = leer_json(DATA / "mercado_horario.json", {})
    noticias = leer_json(DATA / "noticias.json", {})
    precios = leer_json(DATA / "precios.json", {}) or {}
    if not mercado or not mercado.get("ultimo", {}).get("RB=F", {}).get("precio"):
        anterior = leer_json(RUTA, {})
        log("Señal: sin datos de mercado; se conserva la señal anterior", "WARN")
        return anterior or {}
    s = calcular(mercado, noticias, precios.get("tipo_cambio"))
    s["razon"] = razon_claude(s, noticias) or razon_simple(s)
    s["redactado_por"] = MODELO_CLAUDE if cliente_claude() else "plantilla"
    ahora = ahora_gt()
    s["actualizado"] = ahora.isoformat(timespec="minutes")
    s["proximo_martes"] = proximo_martes(ahora)
    s["fecha"] = ahora.date().isoformat()
    guardar_json(RUTA, s)

    hist = [h for h in (leer_json(RUTA_HISTORIAL, []) or []) if h.get("fecha") != s["fecha"]]
    hist.append({"fecha": s["fecha"], "puntaje": s["puntaje"], "tendencia": s["tendencia"], "veredicto": s["veredicto"],
                 "cambio_estimado_q": s["cambio_estimado_q"]})
    hist.sort(key=lambda h: h["fecha"])
    guardar_json(RUTA_HISTORIAL, hist[-90:])
    log(f"Señal: {s['emoji']} {s['veredicto']} (puntaje {s['puntaje']:+d}) · {s['razon']}")
    return s


if __name__ == "__main__":  # pragma: no cover
    actualizar()
