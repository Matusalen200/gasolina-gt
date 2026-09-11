"""Noticias: lee RSS de energía y medios guatemaltecos, filtra por combustibles y clasifica cada nota nueva
como ALZA, BAJA o NEUTRAL para el precio de la gasolina en Guatemala.

Claude clasifica (modelo en CLAUDE_MODELO, por defecto claude-opus-5). Si no hay clave o falla,
se usa una clasificación por palabras clave marcada como "reglas".
Guarda data/noticias.json sin duplicados, máximo 50 recientes.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser

from agente.comun import DATA, MODELO_CLAUDE, cliente_claude, guardar_json, http_get, leer_json, log

# Reuters cerró sus RSS públicos en 2020; se usa Google News filtrado a Reuters como sustituto.
FUENTES = [
    ("Reuters (vía Google News)", "https://news.google.com/rss/search?q=site:reuters.com+(oil+OR+gasoline+OR+OPEC+OR+crude)&hl=en-US&gl=US&ceid=US:en", "en"),
    ("OilPrice.com", "https://oilprice.com/rss/main", "en"),
    ("EIA", "https://www.eia.gov/rss/todayinenergy.xml", "en"),
    ("Prensa Libre", "https://www.prensalibre.com/feed/", "es"),
    # Soy502 y AGN ya no publican RSS válido (devuelven HTML); se leen vía Google News.
    ("Soy502 (vía Google News)", "https://news.google.com/rss/search?q=site:soy502.com+(gasolina+OR+combustible+OR+di%C3%A9sel+OR+MEM)&hl=es-419&gl=GT&ceid=GT:es-419", "es"),
    ("AGN (vía Google News)", "https://news.google.com/rss/search?q=site:agn.gt+(gasolina+OR+combustible+OR+MEM+OR+subsidio)&hl=es-419&gl=GT&ceid=GT:es-419", "es"),
    ("República", "https://republica.gt/feed", "es"),
    ("Prensa GT (vía Google News)", "https://news.google.com/rss/search?q=Guatemala+(gasolina+OR+di%C3%A9sel)+precio+MEM&hl=es-419&gl=GT&ceid=GT:es-419", "es"),
]
PALABRAS = {
    "es": re.compile(r"petr[oó]leo|gasolina|di[eé]sel|combustible|\bMEM\b|subsidio|crudo|hidrocarburo|galón|galon|OPEP", re.I),
    "en": re.compile(r"\boil\b|gasoline|crude|\bOPEC\b|refiner|fuel|diesel|\bWTI\b|\bBrent\b|petroleum", re.I),
}
RUTA = DATA / "noticias.json"
MAXIMO = 50

RX_ALZA = re.compile(r"sube|alza|aument|encarec|incremento|rises?|jumps?|surges?|climbs?|higher|rally|cut(s)? output|supply cut|disruption|hurricane|sanction|attack|tension|escala", re.I)
RX_BAJA = re.compile(r"baja|cae|caída|disminu|reduc|abarat|subsidio|falls?|drops?|slides?|tumbles?|lower|declines?|plunge|glut|oversupply|boost(s)? output|raise(s)? output|surplus|ceasefire|demand fears", re.I)


def _id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _fecha(entrada) -> str:
    for k in ("published_parsed", "updated_parsed"):
        if entrada.get(k):
            try:
                return datetime.fromtimestamp(mktime(entrada[k]), tz=timezone.utc).isoformat(timespec="minutes")
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat(timespec="minutes")


def _limpiar(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def leer_fuentes() -> list[dict]:
    notas = []
    for nombre, url, idioma in FUENTES:
        try:
            r = http_get(url, timeout=25, intentos=1, headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"})
            if r is None or r.status_code != 200:
                log(f"RSS {nombre}: HTTP {getattr(r, 'status_code', 'sin respuesta')}", "WARN")
                continue
            crudo = r.content.lstrip()
            if crudo.startswith(b"\xef\xbb\xbf"):
                crudo = crudo[3:]
            feed = feedparser.parse(crudo)
        except Exception as e:
            log(f"RSS {nombre} falló: {e}", "WARN")
            continue
        if getattr(feed, "bozo", False) and not feed.entries:
            log(f"RSS {nombre} sin entradas ({getattr(feed, 'bozo_exception', '')})", "WARN")
            continue
        for e in feed.entries[:60]:
            titulo = _limpiar(e.get("title", ""))
            if "Google News" in nombre:  # Google News agrega " - Medio" al final del titular
                titulo = re.sub(r"\s+-\s+[^-]{2,40}$", "", titulo)
            resumen = _limpiar(e.get("summary", ""))[:400]
            texto = f"{titulo} {resumen}"
            if not titulo or not e.get("link") or not PALABRAS[idioma].search(texto):
                continue
            notas.append({"id": _id(e["link"]), "titulo": titulo, "resumen": resumen, "fuente": nombre,
                          "url": e["link"], "fecha": _fecha(e), "idioma": idioma})
    log(f"RSS: {len(notas)} notas relevantes en {len(FUENTES)} fuentes")
    return notas


def clasificar_reglas(nota: dict) -> dict:
    texto = f"{nota['titulo']} {nota.get('resumen', '')}"
    a, b = len(RX_ALZA.findall(texto)), len(RX_BAJA.findall(texto))
    if a > b:
        return {"etiqueta": "ALZA", "razon": "El titular apunta a precios más altos.", "clasificado_por": "reglas"}
    if b > a:
        return {"etiqueta": "BAJA", "razon": "El titular apunta a precios más bajos.", "clasificado_por": "reglas"}
    return {"etiqueta": "NEUTRAL", "razon": "Sin efecto claro en el precio local.", "clasificado_por": "reglas"}


def clasificar_claude(notas: list[dict]) -> list[dict] | None:
    """Clasifica en lote con Claude. Devuelve None si no hay cliente o falla."""
    cliente = cliente_claude()
    if cliente is None or not notas:
        return None
    from pydantic import BaseModel

    class Nota(BaseModel):
        id: str
        etiqueta: str  # ALZA | BAJA | NEUTRAL
        razon: str

    class Lote(BaseModel):
        notas: list[Nota]

    listado = "\n".join(f"- id={n['id']} | {n['fuente']} | {n['titulo']} — {n.get('resumen', '')[:250]}" for n in notas)
    try:
        r = cliente.messages.parse(
            model=MODELO_CLAUDE,
            max_tokens=4000,
            system=(
                "Eres analista de precios de combustibles para Guatemala, país que importa toda su gasolina y diésel "
                "de Estados Unidos y fija precios de referencia semanales (MEM) los martes. Clasifica cada noticia según "
                "su efecto probable sobre el precio en Guatemala en las próximas 1-2 semanas: ALZA (empuja hacia arriba), "
                "BAJA (empuja hacia abajo) o NEUTRAL (sin efecto claro o ya reflejado). La razón va en español sencillo, "
                "máximo 12 palabras, sin tickers ni jerga: di 'petróleo' y 'gasolina en EE.UU.'. Devuelve una entrada por id."
            ),
            messages=[{"role": "user", "content": listado}],
            output_format=Lote,
        )
        por_id = {n.id: n for n in r.parsed_output.notas}
        out = []
        for n in notas:
            c = por_id.get(n["id"])
            et = (c.etiqueta.upper().strip() if c else "NEUTRAL")
            if et not in ("ALZA", "BAJA", "NEUTRAL"):
                et = "NEUTRAL"
            out.append({"etiqueta": et, "razon": (c.razon.strip() if c else "Sin efecto claro."), "clasificado_por": MODELO_CLAUDE})
        log(f"Claude clasificó {len(notas)} noticias")
        return out
    except Exception as e:
        log(f"Claude no pudo clasificar ({type(e).__name__}: {e}); uso reglas", "WARN")
        return None


def actualizar() -> dict:
    actual = leer_json(RUTA, {}) or {}
    existentes = {n["id"]: n for n in actual.get("noticias", [])}
    nuevas = [n for n in leer_fuentes() if n["id"] not in existentes]
    # sin duplicados por título (mismo titular en dos fuentes)
    vistos, unicas = {n["titulo"].lower() for n in existentes.values()}, []
    for n in nuevas:
        if n["titulo"].lower() not in vistos:
            vistos.add(n["titulo"].lower())
            unicas.append(n)
    nuevas = unicas[:40]
    if nuevas:
        clasif = clasificar_claude(nuevas) or [clasificar_reglas(n) for n in nuevas]
        for n, c in zip(nuevas, clasif):
            n.update(c)
            n.pop("resumen", None)
            existentes[n["id"]] = n
    todas = sorted(existentes.values(), key=lambda n: n["fecha"], reverse=True)[:MAXIMO]
    hace7 = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="minutes")
    balance = {"ALZA": 0, "BAJA": 0, "NEUTRAL": 0}
    for n in todas:
        if n["fecha"] >= hace7:
            balance[n.get("etiqueta", "NEUTRAL")] += 1
    salida = {"actualizado": datetime.now(timezone.utc).isoformat(timespec="minutes"), "nuevas": len(nuevas),
              "balance_7d": balance, "noticias": todas}
    guardar_json(RUTA, salida)
    log(f"Noticias: {len(nuevas)} nuevas, {len(todas)} guardadas, balance 7d {balance}")
    return salida


if __name__ == "__main__":  # pragma: no cover
    actualizar()
