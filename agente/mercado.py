"""Mercado: futuros de gasolina RBOB (RB=F), petróleo WTI (CL=F) y dólar/quetzal (GTQ=X) desde Yahoo Finance.

Guarda data/mercado_horario.json (últimos 30 días, velas de 1 hora) y data/mercado_semanal.json
(2 años de cierres semanales, para la proyección). Si Yahoo falla se conserva el último dato bueno.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agente.comun import DATA, guardar_json, http_get, leer_json, log

SIMBOLOS = {"RB=F": "gasolina_eeuu", "CL=F": "petroleo_wti", "GTQ=X": "usd_gtq"}
URL_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}?range={rango}&interval={intervalo}"
RUTA_HORARIO = DATA / "mercado_horario.json"
RUTA_SEMANAL = DATA / "mercado_semanal.json"
DIAS_RETENCION = 30


def _descargar(simbolo: str, rango: str, intervalo: str) -> list[dict]:
    """Lista de {t: iso-utc, p: cierre} o [] si falla."""
    r = http_get(URL_CHART.format(simbolo=simbolo.replace("=", "%3D"), rango=rango, intervalo=intervalo), timeout=30,
                 headers={"Accept": "application/json"})
    if r is None or r.status_code != 200:
        log(f"Yahoo {simbolo} {intervalo}: HTTP {getattr(r, 'status_code', 'sin respuesta')}", "WARN")
        return []
    try:
        res = r.json()["chart"]["result"][0]
        tiempos = res["timestamp"]
        cierres = res["indicators"]["quote"][0]["close"]
    except Exception as e:
        log(f"Yahoo {simbolo}: respuesta inesperada ({e})", "WARN")
        return []
    puntos = []
    for t, c in zip(tiempos, cierres):
        if c is None:
            continue
        puntos.append({"t": datetime.fromtimestamp(t, tz=timezone.utc).isoformat(timespec="minutes"), "p": round(float(c), 4)})
    return puntos


def _fusionar(viejos: list[dict], nuevos: list[dict], dias: int | None) -> list[dict]:
    por_t = {p["t"]: p for p in viejos}
    for p in nuevos:
        por_t[p["t"]] = p
    serie = sorted(por_t.values(), key=lambda p: p["t"])
    if dias:
        limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="minutes")
        serie = [p for p in serie if p["t"] >= limite]
    return serie


def _valor_hace(serie: list[dict], dias: float) -> float | None:
    """Último cierre registrado a más tardar hace `dias` días."""
    if not serie:
        return None
    objetivo = (datetime.fromisoformat(serie[-1]["t"]) - timedelta(days=dias)).isoformat(timespec="minutes")
    candidatos = [p for p in serie if p["t"] <= objetivo]
    return candidatos[-1]["p"] if candidatos else serie[0]["p"]


def resumen(serie: list[dict]) -> dict:
    if not serie:
        return {"precio": None}
    ultimo = serie[-1]["p"]
    hace7, hace1 = _valor_hace(serie, 7), _valor_hace(serie, 1)
    return {
        "precio": ultimo,
        "fecha": serie[-1]["t"],
        "hace_7d": hace7,
        "cambio_7d_pct": round((ultimo / hace7 - 1) * 100, 2) if hace7 else None,
        "cambio_7d_abs": round(ultimo - hace7, 4) if hace7 else None,
        "cambio_1d_pct": round((ultimo / hace1 - 1) * 100, 2) if hace1 else None,
    }


def actualizar() -> dict:
    horario = leer_json(RUTA_HORARIO, {}) or {}
    series = horario.get("series", {})
    semanal = leer_json(RUTA_SEMANAL, {}) or {}
    series_sem = semanal.get("series", {})
    ok = 0
    for simbolo in SIMBOLOS:
        nuevos = _descargar(simbolo, "1mo", "1h")
        if nuevos:
            ok += 1
            series[simbolo] = _fusionar(series.get(simbolo, []), nuevos, DIAS_RETENCION)
        else:
            log(f"{simbolo}: sin datos nuevos, se conserva la serie anterior ({len(series.get(simbolo, []))} puntos)", "WARN")
        nuevos_sem = _descargar(simbolo, "2y", "1wk")
        if nuevos_sem:
            series_sem[simbolo] = _fusionar(series_sem.get(simbolo, []), nuevos_sem, None)[-120:]

    ahora = datetime.now(timezone.utc).isoformat(timespec="minutes")
    horario = {
        "actualizado": ahora if ok else horario.get("actualizado"),
        "nombres": SIMBOLOS,
        "ultimo": {s: resumen(series.get(s, [])) for s in SIMBOLOS},
        "series": series,
    }
    guardar_json(RUTA_HORARIO, horario)
    guardar_json(RUTA_SEMANAL, {"actualizado": ahora, "series": series_sem})
    u = horario["ultimo"]
    log(f"Mercado: RBOB {u['RB=F'].get('precio')} ({u['RB=F'].get('cambio_7d_pct')}% 7d), WTI {u['CL=F'].get('precio')}, USD/GTQ {u['GTQ=X'].get('precio')} · {ok}/3 símbolos")
    return horario


if __name__ == "__main__":  # pragma: no cover
    actualizar()
