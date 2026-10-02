"""Prueba todas las fuentes posibles de precios de combustible en Guatemala y dice cuáles sirven.

No es parte del agente: es una herramienta para revisar el panorama cada cierto tiempo.
    .venv\\Scripts\\python.exe scripts\\revisar_fuentes.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import requests  # noqa: E402

try:   # la consola de Windows no imprime acentos por defecto
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
RX_PRECIO_GT = re.compile(r"Q\s?\d{2}[.,]\d{2}|\d{2}[.,]\d{2}\s*quetzales", re.I)
RX_TEMA = re.compile(r"gasolina|di[eé]sel|combustible", re.I)

# (grupo, nombre, url, tipo)   tipo: web | rss | api
FUENTES = [
    # ---------------- oficiales
    ("Oficial", "MEM · precios nacionales", "https://mem.gob.gt/que-hacemos/hidrocarburos/comercializacion-downstream/precios-combustible-nacionales/", "web"),
    ("Oficial", "MEM · histórico", "https://mem.gob.gt/historico-precios-nacionales/", "web"),
    ("Oficial", "MEM · petróleo y combustibles", "https://mem.gob.gt/precios-petroleo-combustibles/", "web"),
    ("Oficial", "MEM · buscador de contenido", "https://mem.gob.gt/wp-json/wp/v2/posts?search=precios", "api"),
    ("Oficial", "Consulta el precio (MEM)", "https://www.consultaelprecio.gob.gt/", "web"),
    ("Oficial", "DIACO", "https://diaco.gob.gt/feed/", "rss"),
    ("Oficial", "AGN · agencia estatal", "https://agn.gt/feed/", "rss"),
    ("Oficial", "Diario de Centro América", "https://dca.gob.gt/feed/", "rss"),
    ("Oficial", "Banco de Guatemala", "https://www.banguat.gob.gt/", "web"),
    ("Oficial", "Congreso · decretos", "https://www.congreso.gob.gt/noticias", "web"),

    # ---------------- medios guatemaltecos
    ("Medios", "Prensa Libre · economía", "https://www.prensalibre.com/economia/feed/", "rss"),
    ("Medios", "La Hora", "https://lahora.gt/feed/", "rss"),
    ("Medios", "TV Azteca Guatemala", "https://tvaztecaguate.com/feed/", "rss"),
    ("Medios", "TV Azteca · búsqueda precios", "https://tvaztecaguate.com/?s=precios+combustibles&feed=rss2", "rss"),
    ("Medios", "Emisoras Unidas", "https://emisorasunidas.com/feed/", "rss"),
    ("Medios", "República", "https://republica.gt/feed", "rss"),
    ("Medios", "Soy502", "https://www.soy502.com/rss", "rss"),
    ("Medios", "Publinews", "https://www.publinews.gt/feed/", "rss"),
    ("Medios", "CRN Noticias", "https://crnnoticias.com/feed/", "rss"),
    ("Medios", "La Red 106.1", "https://www.lared1061.com/feed", "rss"),
    ("Medios", "Guatemala.com", "https://www.guatemala.com/noticias/feed/", "rss"),
    ("Medios", "Infobae Guatemala", "https://www.infobae.com/guatemala/", "web"),
    ("Medios", "Perspectiva", "https://perspectiva.gt/feed/", "rss"),
    ("Medios", "Google News Guatemala", "https://news.google.com/rss/search?q=Guatemala+combustibles+precio+MEM+when:7d&hl=es-419&gl=GT&ceid=GT:es-419", "rss"),

    # ---------------- comerciales (las gasolineras mismas)
    ("Comercial", "Puma Energy Guatemala", "https://www.pumaenergy.com/es/guatemala/", "web"),
    ("Comercial", "Uno Guatemala", "https://www.unopetrol.com/", "web"),
    ("Comercial", "Shell Guatemala", "https://www.shell.com.gt/", "web"),
    ("Comercial", "Texaco Guatemala", "https://www.texaco.com.gt/", "web"),
    ("Comercial", "Grupo Delta", "https://www.gruposdelta.com/", "web"),

    # ---------------- agregadores internacionales
    ("Agregador", "GlobalPetrolPrices · Guatemala", "https://www.globalpetrolprices.com/Guatemala/gasoline_prices/", "web"),
    ("Agregador", "Trading Economics · Guatemala", "https://tradingeconomics.com/guatemala/gasoline-prices", "web"),
    ("Agregador", "Numbeo · Guatemala", "https://www.numbeo.com/gas-prices/country_result.jsp?country=Guatemala", "web"),

    # ---------------- referencia internacional (lo que ya usamos)
    ("Mercado", "Yahoo · gasolina RBOB", "https://query1.finance.yahoo.com/v8/finance/chart/RB%3DF?range=5d&interval=1d", "api"),
    ("Mercado", "Yahoo · petróleo WTI", "https://query1.finance.yahoo.com/v8/finance/chart/CL%3DF?range=5d&interval=1d", "api"),
    ("Mercado", "EIA · energía hoy", "https://www.eia.gov/rss/todayinenergy.xml", "rss"),
    ("Mercado", "OpenStreetMap · gasolineras", "https://overpass-api.de/api/interpreter", "api"),
# ---------------- internacionales: referencia del crudo y los combustibles
    ("Internacional", "EIA · precios semanales EE.UU.", "https://api.eia.gov/v2/petroleum/pri/gnd/data/?frequency=weekly&data[0]=value&length=5", "api"),
    ("Internacional", "EIA · noticias de energía", "https://www.eia.gov/rss/todayinenergy.xml", "rss"),
    ("Internacional", "OPEP · comunicados", "https://www.opec.org/opec_web/en/press_room/28.htm", "web"),
    ("Internacional", "AIE (IEA) · noticias", "https://www.iea.org/news", "web"),
    ("Internacional", "OilPrice.com", "https://oilprice.com/rss/main", "rss"),
    ("Internacional", "Investing · crudo", "https://www.investing.com/commodities/crude-oil", "web"),
    ("Internacional", "Reuters energía (vía Google)", "https://news.google.com/rss/search?q=site:reuters.com+(oil+OR+gasoline+OR+OPEC)+when:7d&hl=en-US&gl=US&ceid=US:en", "rss"),
    ("Internacional", "Bloomberg energía (vía Google)", "https://news.google.com/rss/search?q=site:bloomberg.com+(oil+OR+gasoline)+when:7d&hl=en-US&gl=US&ceid=US:en", "rss"),
    ("Internacional", "Banco Mundial · materias primas", "https://www.worldbank.org/en/research/commodity-markets", "web"),
    ("Internacional", "Yahoo · dólar a quetzal", "https://query1.finance.yahoo.com/v8/finance/chart/GTQ%3DX?range=5d&interval=1d", "api"),
    ("Internacional", "Yahoo · gasolina Brent", "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF?range=5d&interval=1d", "api"),
    ("Internacional", "Stooq · gasolina RBOB", "https://stooq.com/q/d/l/?s=rb.f&i=d", "api"),

    # ---------------- Centroamérica: para comparar con los vecinos
    ("Centroamérica", "SIECA · estadísticas", "https://www.sieca.int/", "web"),
    ("Centroamérica", "CEPAL · energía", "https://www.cepal.org/es/temas/energia", "web"),
    ("Centroamérica", "El Salvador · CNE precios", "https://www.cne.gob.sv/precios-de-referencia/", "web"),
    ("Centroamérica", "Honduras · SEN precios", "https://sen.hn/", "web"),
    ("Centroamérica", "Costa Rica · RECOPE", "https://www.recope.go.cr/productos/precios-nacionales/", "web"),
    ("Centroamérica", "Panamá · ASEP", "https://www.asep.gob.pa/", "web"),
    ("Centroamérica", "Nicaragua · INE", "https://www.ine.gob.ni/", "web"),
]


def probar(url: str, tipo: str) -> dict:
    try:
        if "overpass" in url:
            r = requests.post(url, data={"data": '[out:json][timeout:25];node["amenity"="fuel"](14.6,-90.6,14.7,-90.4);out count;'},
                              headers={"User-Agent": "GasolinaGT/1.0"}, timeout=60)
        else:
            r = requests.get(url, headers={"User-Agent": AGENTE, "Accept-Language": "es-GT,es;q=0.9"}, timeout=40)
    except Exception as e:
        return {"estado": "sin respuesta", "detalle": type(e).__name__}

    if r.status_code != 200:
        bloqueo = " (bloqueado por Cloudflare)" if r.status_code == 403 else ""
        return {"estado": f"HTTP {r.status_code}{bloqueo}", "detalle": ""}

    texto = r.text
    if tipo == "rss":
        n = texto.count("<item")
        con_tema = len(RX_TEMA.findall(texto))
        if n == 0:
            return {"estado": "no es RSS válido", "detalle": "devuelve HTML"}
        return {"estado": "sirve", "detalle": f"{n} notas, {con_tema} mencionan combustibles"}

    precios = len(set(RX_PRECIO_GT.findall(texto)))
    tema = len(RX_TEMA.findall(texto))
    if precios and tema:
        return {"estado": "sirve", "detalle": f"{precios} precios en quetzales, {tema} menciones"}
    if tema:
        return {"estado": "habla del tema", "detalle": f"{tema} menciones, sin precios legibles"}
    return {"estado": "responde", "detalle": "sin precios ni mención directa"}


def main() -> int:
    print("\nREVISIÓN DE FUENTES DE PRECIOS DE COMBUSTIBLE EN GUATEMALA")
    print("=" * 78)
    grupo_actual = None
    resumen = {}
    for grupo, nombre, url, tipo in FUENTES:
        if grupo != grupo_actual:
            grupo_actual = grupo
            print(f"\n── {grupo} ──")
        r = probar(url, tipo)
        marca = {"sirve": "✅", "habla del tema": "🟡"}.get(r["estado"], "❌")
        print(f"  {marca} {nombre:<34} {r['estado']:<28} {r['detalle']}")
        resumen.setdefault(marca, []).append(nombre)
    print("\n" + "=" * 78)
    print(f"Sirven: {len(resumen.get('✅', []))} · A medias: {len(resumen.get('🟡', []))} · No sirven: {len(resumen.get('❌', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
