"""Descarga y lectura de los informes semanales de precios del MEM.

Estrategias, en orden (si una falla se pasa a la siguiente y se registra en el log):
  1. Página oficial del MEM (bloqueada por Cloudflare desde mediados de 2026).
  2. URLs adivinadas por fecha en /wp-content/uploads/AAAA/MM/ (directo y vía Wayback Machine).
  3. Índice CDX de Wayback Machine para el mes actual y el anterior.
  4. Carpeta manual data/pdf/ o variable MEM_PDF_URL (workflow_dispatch).
Si nada funciona, se conserva el último dato bueno.
"""
from __future__ import annotations

import io
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import logging

import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)

from agente.comun import DATA, guardar_json, http_get, leer_json, log

URL_LISTADO = (
    "https://mem.gob.gt/que-hacemos/hidrocarburos/comercializacion-downstream/"
    "precios-combustible-nacionales/"
)
BASE_UPLOADS = "https://mem.gob.gt/wp-content/uploads/{anio}/{mes:02d}/"

# Patrones de nombre de archivo que publica el MEM.
PATRONES = {
    "ejecutivo": [
        re.compile(r"INFORME-EJECUTIVO-DE-PRECIOS-DE-LOS-COMBUSTIBLES(?:-AREA-METROPOLITANA)?-(\d{4}-\d{2}-\d{2})(?:-\d+)?\.pdf", re.I),
    ],
    "departamental": [
        re.compile(r"Precios-de-referencia-departamental-semanal-(\d{4}-\d{2}-\d{2})(?:-\d+)?\.pdf", re.I),
        re.compile(r"Precios-de-referencia-en-terminales-y-departamentos-(\d{4}-\d{2}-\d{2})(?:-\d+)?\.pdf", re.I),
        re.compile(r"Informe-de-precios-de-combustible-a-nivel-nacional(?:-AST)?-(\d{4}-\d{2}-\d{2})(?:-\d+)?\.pdf", re.I),
    ],
}
PLANTILLAS_NOMBRE = {
    "ejecutivo": [
        "INFORME-EJECUTIVO-DE-PRECIOS-DE-LOS-COMBUSTIBLES-{f}.pdf",
        "INFORME-EJECUTIVO-DE-PRECIOS-DE-LOS-COMBUSTIBLES-AREA-METROPOLITANA-{f}.pdf",
    ],
    "departamental": [
        "Precios-de-referencia-departamental-semanal-{f}.pdf",
        "Precios-de-referencia-en-terminales-y-departamentos-{f}.pdf",
        "Informe-de-precios-de-combustible-a-nivel-nacional-{f}.pdf",
    ],
}

RUTA_PRECIOS = DATA / "precios.json"
RUTA_DEPTOS = DATA / "departamentos.json"
RUTA_HISTORIAL = DATA / "precios_historial.json"
CARPETA_MANUAL = DATA / "pdf"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


# ----------------------------------------------------------------------------- utilidades
def _num(txt: str) -> float:
    return float(txt.replace("Q", "").replace(",", "").strip())


def _fecha_ddmmaaaa(txt: str) -> str:
    d, m, a = txt.strip().split("/")
    return f"{int(a):04d}-{int(m):02d}-{int(d):02d}"


def _sin_acentos(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


def clasificar_nombre(nombre_o_url: str):
    """Devuelve (tipo, fecha_iso) si el nombre coincide con un informe conocido."""
    nombre = nombre_o_url.rsplit("/", 1)[-1]
    for tipo, regexes in PATRONES.items():
        for rx in regexes:
            m = rx.search(nombre)
            if m:
                return tipo, m.group(1)
    return None, None


def texto_pdf(origen) -> str:
    """Texto plano de un PDF (ruta o bytes)."""
    if isinstance(origen, (bytes, bytearray)):
        origen = io.BytesIO(origen)
    partes = []
    with pdfplumber.open(origen) as pdf:
        for pagina in pdf.pages:
            partes.append(pagina.extract_text() or "")
    return "\n".join(partes)


# ----------------------------------------------------------------------------- parsers
RX_FILA_PRODUCTO = re.compile(
    r"(Gasolina Superior|Gasolina Regular|Combustible Diesel|Kerosene)\s+Q?([\d.,]+)\s+Q?([\d.,]+)\s+Q?(-?[\d.,]+)"
)
RX_FECHAS = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")
CLAVE = {"Gasolina Superior": "superior", "Gasolina Regular": "regular", "Combustible Diesel": "diesel", "Kerosene": "kerosene"}


def parsear_ejecutivo(origen) -> dict:
    """Lee el INFORME EJECUTIVO (área metropolitana): precios autoservicio, servicio completo e historial."""
    texto = texto_pdf(origen)
    res = {"tipo": "ejecutivo", "autoservicio": {}, "servicio_completo": {}, "historial": [], "tipo_cambio": None}

    m = re.search(r"Fecha del Monitoreo:\s*\w+,\s*(\d{1,2}) de (\w+) de (\d{4})", texto, re.I)
    if m:
        mes = MESES.get(_sin_acentos(m.group(2)).lower())
        if mes:
            res["fecha_monitoreo"] = f"{int(m.group(3)):04d}-{mes:02d}-{int(m.group(1)):02d}"
    m = re.search(r"Correlativo:\s*(\S+)", texto)
    if m:
        res["correlativo"] = m.group(1)
    m = re.search(r"Tipo de cambio[^:]*:\s*([\d.]+)", texto)
    if m:
        res["tipo_cambio"] = float(m.group(1))

    # Sección 1: dos bloques (autoservicio y servicio completo), cada uno con fecha anterior / actual.
    bloques = re.split(r"MODALIDAD:\s*", texto)
    for bloque in bloques[1:]:
        cabecera = bloque[:40].upper()
        destino = "autoservicio" if "AUTOSERVICIO" in cabecera else "servicio_completo" if "SERVICIO COMPLETO" in cabecera else None
        if not destino or res[destino]:
            continue
        seccion = bloque.split("2. COMPARACI")[0]
        fechas = RX_FECHAS.findall(seccion.split("Producto")[1][:60]) if "Producto" in seccion else []
        for prod, ant, act, dif in RX_FILA_PRODUCTO.findall(seccion):
            res[destino][CLAVE[prod]] = _num(act)
            res[destino].setdefault("_anterior", {})[CLAVE[prod]] = _num(ant)
        if fechas and len(fechas) >= 2:
            res[destino]["fecha_anterior"] = _fecha_ddmmaaaa(fechas[0])
            res[destino]["fecha"] = _fecha_ddmmaaaa(fechas[1])
    if "fecha_monitoreo" not in res and res["autoservicio"].get("fecha"):
        res["fecha_monitoreo"] = res["autoservicio"]["fecha"]

    # Sección 2: historial de últimas semanas (autoservicio).
    m = re.search(r"2\. COMPARACI.*?Producto((?:\s+\d{1,2}/\d{1,2}/\d{4})+)(.*?)(?:Precios promedio semanales|$)", texto, re.S)
    if m:
        fechas = [_fecha_ddmmaaaa(f) for f in RX_FECHAS.findall(m.group(1))]
        series = {}
        for linea in m.group(2).splitlines():
            mm = re.match(r"(Gasolina Superior|Gasolina Regular|Combustible Diesel)((?:\s+Q?[\d.,]+)+)", linea.strip())
            if mm:
                series[CLAVE[mm.group(1)]] = [_num(x) for x in mm.group(2).split()]
        for i, f in enumerate(fechas):
            fila = {"fecha": f}
            for k, vals in series.items():
                if i < len(vals):
                    fila[k] = vals[i]
            if len(fila) > 1:
                res["historial"].append(fila)
    return res


RX_DEPTO = re.compile(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .'\-]+?),\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .'\-]+?)\s+Q?([\d.,]+)\s+Q?([\d.,]+)\s+Q?([\d.,]+)\s*$")


def _titulo(txt: str) -> str:
    palabras = []
    for p in txt.strip().split():
        pl = p.lower()
        palabras.append(pl if pl in ("de", "del", "la", "las", "los", "y") and palabras else p.capitalize())
    return " ".join(palabras)


def parsear_departamental(origen) -> dict:
    """Lee el informe de precios de referencia por cabecera departamental (autoservicio)."""
    texto = texto_pdf(origen)
    res = {"tipo": "departamental", "departamentos": []}
    m = re.search(r"Vigencia:\s*Del\s*(\d{1,2}/\d{1,2}/\d{4})\s*al\s*(\d{1,2}/\d{1,2}/\d{4})", texto, re.I)
    if m:
        res["vigencia_inicio"] = _fecha_ddmmaaaa(m.group(1))
        res["vigencia_fin"] = _fecha_ddmmaaaa(m.group(2))
    for linea in texto.splitlines():
        mm = RX_DEPTO.match(linea.strip())
        if not mm:
            continue
        res["departamentos"].append({
            "cabecera": _titulo(mm.group(1)),
            "departamento": _titulo(mm.group(2)),
            "superior": _num(mm.group(3)),
            "regular": _num(mm.group(4)),
            "diesel": _num(mm.group(5)),
        })
    return res


RX_CELDA = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)


def parsear_tabla_html(html: str) -> dict | None:
    """Lee la tabla 'Comparación semanal de precios promedio' de la página del MEM.
    Devuelve el mismo formato que parsear_ejecutivo (autoservicio, servicio_completo, tipo_cambio, fechas)."""
    limpio = re.sub(r"<(script|style)[^>]*>.*?</>", " ", html, flags=re.S | re.I)
    tablas = re.findall(r"<table[^>]*>(.*?)</table>", limpio, re.S | re.I)
    res = {"tipo": "ejecutivo", "autoservicio": {}, "servicio_completo": {}, "historial": [], "tipo_cambio": None}
    destinos = ["autoservicio", "servicio_completo"]
    for t in tablas:
        filas = [[re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in RX_CELDA.findall(f)]
                 for f in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I)]
        filas = [f for f in filas if f]
        if not filas or not any("Monitoreados" in c for c in filas[0]):
            continue
        fechas = RX_FECHAS.findall(" ".join(filas[0]))
        if len(fechas) < 2 or not destinos:
            continue
        destino = destinos.pop(0)
        bloque = res[destino]
        bloque["fecha_anterior"], bloque["fecha"] = _fecha_ddmmaaaa(fechas[0]), _fecha_ddmmaaaa(fechas[1])
        for f in filas[1:]:
            if len(f) < 3:
                continue
            nombre = _sin_acentos(f[0]).lower()
            clave = "superior" if "superior" in nombre else "regular" if "regular" in nombre else "diesel" if "diesel" in nombre else "kerosene" if "keros" in nombre else None
            if not clave:
                continue
            try:
                bloque[clave] = _num(f[2])
                bloque.setdefault("_anterior", {})[clave] = _num(f[1])
            except ValueError:
                continue
    m = re.search(r"Tipo de cambio[^:]*:\s*Q?\s*([\d.]+)", limpio, re.I)
    if m:
        res["tipo_cambio"] = float(m.group(1))
    if not res["autoservicio"].get("superior"):
        return None
    res["fecha_monitoreo"] = res["autoservicio"].get("fecha")
    return res


def parsear_pdf(origen, tipo: str | None = None) -> dict:
    """Detecta el tipo por contenido si no se indica."""
    if tipo is None:
        texto = texto_pdf(origen)[:900].upper()
        tipo = "departamental" if ("CABECERA" in texto or "VIGENCIA:" in texto) else "ejecutivo"
    return parsear_departamental(origen) if tipo == "departamental" else parsear_ejecutivo(origen)


# ----------------------------------------------------------------------------- descubrimiento
def extraer_enlaces(html: str) -> list[dict]:
    """Enlaces a informes dentro del HTML del listado del MEM (o de un snapshot de Wayback)."""
    vistos, enlaces = set(), []
    for href in re.findall(r'href="([^"]+\.pdf)"', html, re.I):
        href = re.sub(r"^https?://web\.archive\.org/web/\d+(?:id_)?/", "", href)
        if href.startswith("/"):
            href = "https://mem.gob.gt" + href
        tipo, fecha = clasificar_nombre(href)
        if tipo and href not in vistos:
            vistos.add(href)
            enlaces.append({"url": href, "tipo": tipo, "fecha": fecha})
    enlaces.sort(key=lambda e: e["fecha"], reverse=True)
    return enlaces


def _es_pdf(r) -> bool:
    return r is not None and r.status_code == 200 and r.content[:5] == b"%PDF-"


def descargar_pdf(url: str, directo: bool = True, wayback: bool = True) -> bytes | None:
    """Intenta directo y luego por Wayback Machine."""
    r = http_get(url, timeout=40, intentos=1) if directo else None
    if _es_pdf(r):
        return r.content
    if not wayback:
        return None
    r = http_get(f"https://web.archive.org/web/2id_/{url}", timeout=60, intentos=1)
    if _es_pdf(r):
        log(f"PDF obtenido vía Wayback: {url}")
        return r.content
    return None


def candidatos_por_fecha(hoy: date | None = None, dias: int = 21) -> list[dict]:
    hoy = hoy or date.today()
    out = []
    for i in range(dias):
        f = hoy - timedelta(days=i)
        if f.weekday() > 4:  # el MEM publica entre semana
            continue
        for tipo, plantillas in PLANTILLAS_NOMBRE.items():
            for pl in plantillas:
                out.append({"url": BASE_UPLOADS.format(anio=f.year, mes=f.month) + pl.format(f=f.isoformat()), "tipo": tipo, "fecha": f.isoformat()})
    return out


def candidatos_wayback_cdx(hoy: date | None = None) -> list[dict]:
    hoy = hoy or date.today()
    hace_un_mes = hoy - timedelta(days=28)
    meses = {(hoy.year, hoy.month), (hace_un_mes.year, hace_un_mes.month)}
    out = []
    for anio, mes in sorted(meses):
        url = (f"https://web.archive.org/cdx/search/cdx?url=mem.gob.gt/wp-content/uploads/{anio}/{mes:02d}/*"
               "&filter=statuscode:200&fl=original&collapse=original&limit=200")
        r = http_get(url, timeout=60, intentos=1)
        if r is None or r.status_code != 200:
            continue
        for linea in r.text.splitlines():
            tipo, fecha = clasificar_nombre(linea.strip())
            if tipo:
                out.append({"url": linea.strip(), "tipo": tipo, "fecha": fecha, "wayback": True})
    out.sort(key=lambda e: e["fecha"], reverse=True)
    return out


def descubrir(hoy: date | None = None) -> list[dict]:
    """Lista de candidatos {url, tipo, fecha} ordenados del más reciente al más viejo."""
    candidatos = []
    r = http_get(URL_LISTADO, timeout=40, intentos=1)
    if r is not None and r.status_code == 200 and "wp-content" in r.text:
        enlaces = extraer_enlaces(r.text)
        log(f"Listado MEM leído directo: {len(enlaces)} informes")
        candidatos += enlaces
        tabla = parsear_tabla_html(r.text)
        if tabla:
            integrar_ejecutivo(tabla, "MEM (página oficial)", URL_LISTADO)
            log(f"Tabla HTML del MEM leída: monitoreo {tabla.get('fecha_monitoreo')}")
    else:
        log(f"Listado MEM no accesible (HTTP {getattr(r, 'status_code', 'sin respuesta')}); probando alternativas", "WARN")
        candidatos += candidatos_por_fecha(hoy)
        try:
            candidatos += candidatos_wayback_cdx(hoy)
        except Exception as e:  # pragma: no cover
            log(f"Wayback CDX falló: {e}", "WARN")
    vistos, unicos = set(), []
    for c in candidatos:
        if c["url"] not in vistos:
            vistos.add(c["url"])
            unicos.append(c)
    unicos.sort(key=lambda e: e["fecha"], reverse=True)
    return unicos


def pdfs_manuales() -> list[dict]:
    """PDFs colocados a mano en data/pdf/ o indicados por MEM_PDF_URL."""
    out = []
    if CARPETA_MANUAL.exists():
        for ruta in sorted(CARPETA_MANUAL.glob("*.pdf")):
            tipo, fecha = clasificar_nombre(ruta.name)
            out.append({"ruta": ruta, "tipo": tipo, "fecha": fecha or "0000-00-00"})
    url = os.environ.get("MEM_PDF_URL", "").strip()
    if url:
        tipo, fecha = clasificar_nombre(url)
        out.append({"url": url, "tipo": tipo, "fecha": fecha or "0000-00-00"})
    return out


# ----------------------------------------------------------------------------- integración
def _registrar_historial(fecha: str, precios: dict, fuente: str) -> None:
    hist = leer_json(RUTA_HISTORIAL, []) or []
    hist = [h for h in hist if h.get("fecha") != fecha]
    hist.append({"fecha": fecha, "superior": precios.get("superior"), "regular": precios.get("regular"),
                 "diesel": precios.get("diesel"), "fuente": fuente})
    hist.sort(key=lambda h: h["fecha"])
    guardar_json(RUTA_HISTORIAL, hist[-160:])


def integrar_ejecutivo(info: dict, fuente: str, origen: str) -> dict:
    """Guarda data/precios.json y el historial semanal a partir de un informe ejecutivo."""
    fecha = info.get("fecha_monitoreo") or info.get("autoservicio", {}).get("fecha")
    actual = leer_json(RUTA_PRECIOS, {}) or {}
    if actual.get("fecha_monitoreo") and fecha and fecha < actual["fecha_monitoreo"]:
        log(f"Informe {fecha} es más viejo que el vigente {actual['fecha_monitoreo']}; solo sumo historial")
    else:
        auto = {k: v for k, v in info["autoservicio"].items() if not k.startswith("_")}
        anterior = info["autoservicio"].get("_anterior", {})
        actual = {
            "actualizado": datetime.now().isoformat(timespec="minutes"),
            "fuente": fuente,
            "origen": origen,
            "fecha_monitoreo": fecha,
            "correlativo": info.get("correlativo"),
            "tipo_cambio": info.get("tipo_cambio"),
            "autoservicio": auto,
            "servicio_completo": {k: v for k, v in info["servicio_completo"].items() if not k.startswith("_")},
            "cambio_semanal": {k: round(auto[k] - anterior[k], 2) for k in ("superior", "regular", "diesel", "kerosene") if k in auto and k in anterior},
        }
        guardar_json(RUTA_PRECIOS, actual)
    for fila in info.get("historial", []):
        _registrar_historial(fila["fecha"], fila, fuente)
    if fecha and info["autoservicio"].get("superior"):
        _registrar_historial(fecha, info["autoservicio"], fuente)
    return actual


def integrar_departamental(info: dict, fuente: str, origen: str) -> dict:
    actual = leer_json(RUTA_DEPTOS, {}) or {}
    ini = info.get("vigencia_inicio", "")
    if actual.get("vigencia_inicio") and ini and ini < actual["vigencia_inicio"]:
        log(f"Departamental {ini} más viejo que {actual['vigencia_inicio']}; se ignora")
        return actual
    if not info.get("departamentos"):
        log("Informe departamental sin filas reconocibles; se ignora", "WARN")
        return actual
    deptos = sorted(info["departamentos"], key=lambda d: d["regular"])
    actual = {
        "actualizado": datetime.now().isoformat(timespec="minutes"),
        "fuente": fuente,
        "origen": origen,
        "vigencia_inicio": ini,
        "vigencia_fin": info.get("vigencia_fin"),
        "mas_barato": deptos[0],
        "mas_caro": deptos[-1],
        "departamentos": deptos,
    }
    guardar_json(RUTA_DEPTOS, actual)
    return actual


def procesar_pdf(origen, tipo: str | None, fuente: str, nombre: str) -> bool:
    try:
        info = parsear_pdf(origen, tipo)
    except Exception as e:
        log(f"No se pudo leer {nombre}: {e}", "WARN")
        return False
    if info["tipo"] == "ejecutivo" and info["autoservicio"].get("superior"):
        integrar_ejecutivo(info, fuente, nombre)
        log(f"Precios MEM actualizados desde {nombre} ({info.get('fecha_monitoreo')})")
        return True
    if info["tipo"] == "departamental" and info["departamentos"]:
        integrar_departamental(info, fuente, nombre)
        log(f"Departamentos actualizados desde {nombre} ({info.get('vigencia_inicio')})")
        return True
    log(f"{nombre}: PDF leído pero sin datos reconocibles", "WARN")
    return False


def actualizar(hoy: date | None = None, max_descargas: int = 8) -> dict:
    """Corre todas las estrategias. Devuelve resumen {ejecutivo: bool, departamental: bool}."""
    logrado = {"ejecutivo": False, "departamental": False}

    for m in pdfs_manuales():  # 4. manual primero: si el usuario puso un PDF, manda
        origen = m.get("ruta")
        if origen is None:
            datos = descargar_pdf(m["url"])
            if datos is None:
                log(f"MEM_PDF_URL no descargable: {m['url']}", "WARN")
                continue
            origen, nombre = datos, m["url"]
        else:
            nombre = str(origen.name)
        if procesar_pdf(origen, m["tipo"], "MEM (manual)", nombre):
            logrado[m["tipo"] or "ejecutivo"] = True

    descargas = 0
    for c in descubrir(hoy):
        if all(logrado.values()) or descargas >= max_descargas:
            break
        if logrado.get(c["tipo"]):
            continue
        # Los candidatos adivinados solo se prueban directo; los del índice de Wayback, solo vía Wayback.
        datos = descargar_pdf(c["url"], directo=not c.get("wayback"), wayback=bool(c.get("wayback")))
        if datos is None:
            continue
        descargas += 1
        if procesar_pdf(datos, c["tipo"], "MEM", c["url"]):
            logrado[c["tipo"]] = True

    if not any(logrado.values()):
        vigente = leer_json(RUTA_PRECIOS, {}) or {}
        log(f"MEM sin datos nuevos; se conserva el último bueno ({vigente.get('fecha_monitoreo', 'ninguno')})", "WARN")
    return logrado


if __name__ == "__main__":  # pragma: no cover
    print(actualizar())
