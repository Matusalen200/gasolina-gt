"""Gasolineras con los precios más bajos de la capital, del monitoreo semanal del MEM.

El MEM recorre cada semana una lista de estaciones de la Ciudad de Guatemala y alrededores y publica
cuáles cobran menos. Su PDF está bloqueado, pero los medios republican la lista completa con nombre,
zona y los tres combustibles. De ahí la sacamos.

Guarda data/estaciones.json con las estaciones de autoservicio y de servicio completo, ordenadas de
más barata a más cara, y un enlace de Google Maps para llegar a cada una.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote_plus

from agente.comun import DATA, ahora_gt, guardar_json, http_get, leer_json, log
from agente.hoy import _fecha_gt, _texto_articulo, candidatos

RUTA = DATA / "estaciones.json"
RUTA_COORDS = DATA / "estaciones_coords.json"
# Nominatim (OpenStreetMap) es gratis y sin cuenta. Su norma: identificarse y máximo una consulta
# por segundo. Por eso guardamos lo que ya buscamos y solo preguntamos por lo nuevo.
NOMINATIM = "https://nominatim.openstreetmap.org/search"
ESPERA_MAPA = 1.2
MAX_ARTICULOS = 10        # cuántas notas abrimos por corrida buscando la lista
MINIMO_ESTACIONES = 5     # con menos de esto no es una lista de gasolineras
# Búsquedas dedicadas: la lista sale una vez por semana y el titular cambia cada vez.
FUENTES_EXTRA = [
    ("TV Azteca Guatemala", "https://tvaztecaguate.com/?s=gasolineras+precios+mas+bajos&feed=rss2"),
    ("Google News GT", "https://news.google.com/rss/search?q=Guatemala+gasolineras+precios+m%C3%A1s+bajos+MEM+when:14d&hl=es-419&gl=GT&ceid=GT:es-419"),
]
MAPA = "https://www.google.com/maps/search/?api=1&query="
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

# "Texaco Pesa Tivoli, zona 9: superior Q42.05, regular Q40.05 y diésel Q46.35."
RX_ESTACION = re.compile(
    r"([A-ZÁÉÍÓÚÑ][^:,]{2,55}?),\s*"
    r"(zona\s*\d+|[A-ZÁÉÍÓÚa-záéíóúñ][A-Za-zÁÉÍÓÚáéíóúñ .]{2,25}?)\s*:\s*"
    # Ojo: el precio se captura como 42.05 y NO 42.05. — el punto final de la oración no va incluido.
    r"superior\s*Q\s*(\d+(?:[.,]\d+)?)[,;]?\s*"
    r"regular\s*Q\s*(\d+(?:[.,]\d+)?)\s*(?:y\s*)?"
    r"di[eé]sel\s*Q\s*(\d+(?:[.,]\d+)?)", re.I)
RX_TITULO = re.compile(r"gasolineras|estaciones", re.I)
RX_PRECIOS_BAJOS = re.compile(r"m[aá]s bajos|m[aá]s barat", re.I)
RANGO = (15.0, 90.0)


def _limpiar_nombre(nombre: str) -> str:
    """El texto corrido a veces arrastra la frase anterior; nos quedamos con la última oración."""
    nombre = re.split(r"(?<=[.;])\s+", nombre.strip())[-1]
    nombre = re.sub(r"^\d+[.)]\s*", "", nombre).strip(" .,;")
    return " ".join(nombre.split())


def _zona(txt: str) -> str:
    txt = " ".join(txt.split()).strip(" .,;")
    m = re.match(r"zona\s*(\d+)", txt, re.I)
    return f"zona {m.group(1)}" if m else txt.title()


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


def fecha_monitoreo(texto: str) -> str | None:
    m = re.search(r"recopilad[oa]s?\s+el\s+\w*\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.I)
    if not m:
        return None
    mes = MESES.get(_sin_acentos(m.group(2)))
    return f"{int(m.group(3)):04d}-{mes:02d}-{int(m.group(1)):02d}" if mes else None


def parsear(texto: str) -> dict:
    """Saca las estaciones del texto de la nota, separando autoservicio de servicio completo."""
    encontradas = list(RX_ESTACION.finditer(texto))
    if not encontradas:
        return {"autoservicio": [], "servicio_completo": []}

    # El corte entre las dos modalidades es el título que aparece DESPUÉS de la primera estación.
    corte = len(texto)
    for m in re.finditer(r"servicio\s+completo", texto, re.I):
        if m.start() > encontradas[0].start():
            corte = m.start()
            break

    salida = {"autoservicio": [], "servicio_completo": []}
    vistas = set()
    for m in encontradas:
        try:
            precios = [float(m.group(i).replace(",", ".")) for i in (3, 4, 5)]
        except ValueError:
            continue
        if not all(RANGO[0] <= p <= RANGO[1] for p in precios):
            continue
        nombre, zona = _limpiar_nombre(m.group(1)), _zona(m.group(2))
        if len(nombre) < 4:
            continue
        modalidad = "autoservicio" if m.start() < corte else "servicio_completo"
        clave = (modalidad, _sin_acentos(nombre), zona)
        if clave in vistas:
            continue
        vistas.add(clave)
        salida[modalidad].append({
            "nombre": nombre, "zona": zona,
            "superior": precios[0], "regular": precios[1], "diesel": precios[2],
            "mapa": MAPA + quote_plus(f"{nombre} {zona} Guatemala"),
        })
    for lista in salida.values():
        lista.sort(key=lambda e: e["regular"])
    return salida


def _prioridad(c: dict) -> int:
    """Primero las notas cuyo titular ya promete la lista; después el resto."""
    t = c.get("titulo", "")
    if RX_TITULO.search(t) and RX_PRECIOS_BAJOS.search(t):
        return 0
    if RX_TITULO.search(t):
        return 1
    return 2


def _fuentes_extra() -> list[dict]:
    """Búsquedas propias, porque el titular de la lista semanal cambia cada vez."""
    import feedparser
    fuera = []
    for nombre, url in FUENTES_EXTRA:
        r = http_get(url, timeout=25, intentos=1,
                     headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"})
        if r is None or r.status_code != 200:
            continue
        for e in feedparser.parse(r.content.lstrip()).entries[:15]:
            enlace = e.get("link", "")
            if enlace and "news.google.com" not in enlace:
                fuera.append({"fuente": nombre, "url": enlace, "titulo": e.get("title", ""),
                              "fecha": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                              "resumen": "", "google": False})
    return fuera


def _buscar_coordenadas(consulta: str):
    r = http_get(NOMINATIM, timeout=25, intentos=1,
                 params={"q": consulta, "format": "json", "limit": 1, "countrycodes": "gt"},
                 headers={"User-Agent": "GasolinaGT/1.0 (proyecto ciudadano de precios de combustible)",
                          "Accept": "application/json"})
    if r is None or r.status_code != 200:
        return None
    try:
        datos = r.json()
    except Exception:
        return None
    if not datos:
        return None
    return round(float(datos[0]["lat"]), 6), round(float(datos[0]["lon"]), 6)


def geocodificar(estaciones: list[dict]) -> int:
    """Le pone coordenadas a cada estación para poder pintarla en el mapa.

    Primero busca la gasolinera por su nombre; si no aparece, usa el centro de su zona y lo marca
    como aproximado, para no dar una dirección exacta que no sabemos.
    """
    import time
    cache = leer_json(RUTA_COORDS, {}) or {}
    nuevas = 0
    for e in estaciones:
        clave = f"{e['nombre']}|{e['zona']}"
        if clave not in cache:
            punto = _buscar_coordenadas(f"{e['nombre']}, {e['zona']}, Ciudad de Guatemala, Guatemala")
            exacta = punto is not None
            if punto is None:
                time.sleep(ESPERA_MAPA)
                punto = _buscar_coordenadas(f"{e['zona']}, Ciudad de Guatemala, Guatemala")
            cache[clave] = {"lat": punto[0], "lon": punto[1], "exacta": exacta} if punto else None
            nuevas += 1
            time.sleep(ESPERA_MAPA)
        punto = cache.get(clave)
        if punto:
            e.update(lat=punto["lat"], lon=punto["lon"], ubicacion_exacta=punto["exacta"])
    if nuevas:
        guardar_json(RUTA_COORDS, cache)
        log(f"Mapa: busqué la ubicación de {nuevas} gasolineras nuevas")
    return sum(1 for e in estaciones if e.get("lat"))


def actualizar() -> dict:
    """Busca la lista semanal de gasolineras. Decide por el contenido, no por el titular."""
    actual = leer_json(RUTA, {}) or {}
    vistas = set()
    lista = _fuentes_extra() + [c for c in candidatos() if not c.get("google")]
    lista.sort(key=_prioridad)

    revisados = 0
    for c in lista:
        if revisados >= MAX_ARTICULOS:
            break
        url = c.get("url")
        if not url or url in vistas:
            continue
        vistas.add(url)
        revisados += 1
        r = http_get(url, timeout=30, intentos=1)
        if r is None or r.status_code != 200:
            continue
        texto = _texto_articulo(r.text)
        datos = parsear(texto)
        if len(datos["autoservicio"]) < MINIMO_ESTACIONES:
            continue
        fecha = fecha_monitoreo(texto) or _fecha_gt(c["fecha"])
        if actual.get("fecha_monitoreo", "") > fecha:
            log(f"Gasolineras: la nota de {fecha} es más vieja que la que ya tengo; sigo buscando")
            continue
        baratas = datos["autoservicio"]
        try:
            con_mapa = geocodificar(baratas + datos["servicio_completo"])
        except Exception as ex:   # sin coordenadas el listado igual sirve
            log(f"Mapa: no pude ubicar las gasolineras ({ex})", "WARN")
            con_mapa = 0
        salida = {
            "con_ubicacion": con_mapa,
            "actualizado": ahora_gt().isoformat(timespec="minutes"),
            "fecha_monitoreo": fecha,
            "fuente": c["fuente"], "url": url, "titulo": c.get("titulo", ""),
            "mas_barata": baratas[0] if baratas else None,
            "autoservicio": baratas,
            "servicio_completo": datos["servicio_completo"],
        }
        guardar_json(RUTA, salida)
        log(f"Gasolineras: {len(baratas)} estaciones del {fecha} ({c['fuente']}); la más barata es "
            f"{baratas[0]['nombre']} {baratas[0]['zona']} a Q{baratas[0]['regular']:.2f} la normal")
        return salida

    if actual:
        log(f"Gasolineras: revisé {revisados} notas y no había lista nueva; conservo la del "
            f"{actual.get('fecha_monitoreo')}", "WARN")
    else:
        log(f"Gasolineras: revisé {revisados} notas y ninguna traía la lista de estaciones", "WARN")
    return actual


if __name__ == "__main__":  # pragma: no cover
    actualizar()
