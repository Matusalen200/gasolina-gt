"""Precio de HOY: lee cada hora las noticias y comunicados guatemaltecos (RSS) y extrae del texto los precios
del galón publicados ese día (promedios del MEM, monitoreos, estaciones, precio tope del Congreso).

Guarda data/precio_hoy.json: una serie de observaciones con hora, fuente y tipo, más el último precio
por producto y su cambio contra el día anterior. Es la fuente del número grande del tablero.

Claude (si hay clave) extrae con precisión desde el texto; sin clave se usan expresiones regulares.
"""
from __future__ import annotations

import html as html_mod
import re
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser

from agente.comun import DATA, MODELO_CLAUDE, TZ_GT, ahora_gt, cliente_claude, guardar_json, http_get, leer_json, log

RUTA = DATA / "precio_hoy.json"
DIAS_VENTANA = 30         # solo artículos de los últimos días
MAX_ARTICULOS = 25        # por corrida
MAX_SERIE = 600
RANGO = (15.0, 80.0)      # Q/galón plausibles
BANDA = 7.0               # un precio no puede alejarse más de Q7 del precio oficial del MEM


def _referencia() -> dict:
    """Precios oficiales del MEM (data/precios.json) para descartar cifras incoherentes de las noticias."""
    pr = leer_json(DATA / "precios.json", {}) or {}
    return {k: v for k, v in (pr.get("autoservicio") or {}).items() if isinstance(v, (int, float))}


def _coherente(fila: dict, ref: dict) -> bool:
    """Rechaza observaciones imposibles: súper por debajo de regular, o cifras muy lejos del precio oficial.
    El precio tope del Congreso es un límite legal, no un precio de mercado: solo se le exige el orden."""
    s, r, d = fila.get("superior"), fila.get("regular"), fila.get("diesel")
    if s is not None and r is not None and s < r:       # la súper siempre cuesta más que la regular
        return False
    if fila.get("tipo") == "tope":
        return True
    for prod in ("superior", "regular", "diesel"):
        v = fila.get(prod)
        if v is None:
            continue
        if ref.get(prod) is not None and abs(v - ref[prod]) > BANDA:
            return False
    return True

# Feeds que sí funcionan (probados el 11/09/2026). Google News sirve para titulares, no para el texto.
FUENTES = [
    ("Prensa Libre", "https://www.prensalibre.com/economia/feed/"),
    ("La Hora", "https://lahora.gt/feed/"),
    ("TV Azteca Guatemala", "https://tvaztecaguate.com/feed/"),
    ("TV Azteca Guatemala", "https://tvaztecaguate.com/?s=precios+combustibles&feed=rss2"),
    ("Emisoras Unidas", "https://emisorasunidas.com/feed/"),
    ("Diaco", "https://diaco.gob.gt/feed/"),
    ("República", "https://republica.gt/feed"),
    ("Google News GT", "https://news.google.com/rss/search?q=Guatemala+(gasolina+OR+di%C3%A9sel+OR+combustibles)+precio+when:3d&hl=es-419&gl=GT&ceid=GT:es-419"),
]
RX_TEMA = re.compile(r"gasolina|di[eé]?sel|combustible", re.I)
RX_PRODUCTO = {
    "superior": re.compile(r"\b(?:superior|s[uú]per)\b", re.I),
    "regular": re.compile(r"\bregular\b", re.I),
    "diesel": re.compile(r"\bdi[eé]sel\b", re.I),
}
RX_PRECIO = re.compile(r"(?:Q\s?|quetzales?\s)?(\d{2}(?:[.,]\d{2}))(?:\s?(?:quetzales|Q))?")
RX_TOPE = re.compile(r"tope|precio m[aá]ximo|decreto", re.I)
RX_ESTACION = re.compile(r"gasolinera|estaci[oó]n|texaco|shell|puma|uno\b", re.I)


# ----------------------------------------------------------------------------- texto
def _texto_articulo(html: str) -> str:
    t = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    cuerpo = re.search(r"<article[^>]*>.*?</article>", t, re.S | re.I)
    if cuerpo:
        t = cuerpo.group(0)
    parrafos = re.findall(r"<(?:p|h1|h2|h3|li|td|th)[^>]*>(.*?)</(?:p|h1|h2|h3|li|td|th)>", t, re.S | re.I)
    texto = " ".join(parrafos) if parrafos else t
    texto = html_mod.unescape(re.sub(r"<[^>]+>", " ", texto))
    return re.sub(r"\s+", " ", texto).strip()


def extraer_precios(texto: str) -> dict:
    """Heurística: cada precio se asigna al producto cuya palabra está más cerca (antes o después).
    Para cada producto se toma el primer precio que aparece DESPUÉS de la palabra ("la regular a Q40.93");
    si no hay, el más cercano ANTES ("Q40.93 la regular"). Las notas abren con el precio de la ciudad."""
    palabras = [(k, m.start(), m.end()) for k, rx in RX_PRODUCTO.items() for m in rx.finditer(texto)]

    def _duenio(pos: int) -> str | None:
        mejor, dist = None, 10 ** 9
        for k, ini, fin in palabras:
            d = min(abs(pos - ini), abs(pos - fin))
            if d < dist:
                mejor, dist = k, d
        return mejor

    out = {}
    for prod, rx in RX_PRODUCTO.items():
        for m in rx.finditer(texto):
            hallado = None
            for p in RX_PRECIO.finditer(texto[m.end(): m.end() + 60]):
                v, pos = float(p.group(1).replace(",", ".")), m.end() + p.start()
                if RANGO[0] <= v <= RANGO[1] and _duenio(pos) == prod:
                    hallado = v
                    break
            if hallado is None:
                ini = max(0, m.start() - 45)
                for p in RX_PRECIO.finditer(texto[ini: m.start()]):
                    v, pos = float(p.group(1).replace(",", ".")), ini + p.start()
                    if RANGO[0] <= v <= RANGO[1] and _duenio(pos) == prod:
                        hallado = v
            if hallado is not None:
                out[prod] = hallado
                break
    return out


def clasificar_tipo(texto: str, titulo: str = "") -> str:
    """'tope' solo si el titular (o el arranque de la nota) habla del precio máximo legal; si no, promedio/estación."""
    t = texto[:1500]
    if RX_TOPE.search(titulo or texto[:200]) and not re.search(r"as[ií] est[aá]n|amanecieron|monitoreo", titulo or "", re.I):
        return "tope"
    if re.search(r"promedio|precio de referencia|monitoreo|MEM", t):
        return "promedio"
    if RX_ESTACION.search(t):
        return "estacion"
    return "otro"


def extraer_claude(texto: str, titulo: str, fecha: str) -> dict | None:
    cliente = cliente_claude()
    if cliente is None:
        return None
    from pydantic import BaseModel

    class Obs(BaseModel):
        hay_precios: bool
        tipo: str          # promedio | estacion | tope | otro
        superior: float | None
        regular: float | None
        diesel: float | None
        fecha_dato: str    # AAAA-MM-DD del precio (no de la nota)
        resumen: str       # una frase en español sencillo

    try:
        r = cliente.messages.parse(
            model=MODELO_CLAUDE, max_tokens=600,
            system=("Extraes precios del galón de combustible en Guatemala (Q/galón, autoservicio) de una noticia. "
                    "Si hay varios valores del mismo producto, usa el promedio o precio de referencia del MEM para la ciudad de Guatemala. "
                    "tipo: 'promedio' si son promedios o referencias del MEM, 'estacion' si son precios de gasolineras concretas, "
                    "'tope' si es el precio máximo legal del Congreso, 'otro' si no aplica. Si la nota no trae precios, hay_precios=false."),
            messages=[{"role": "user", "content": f"Título: {titulo}\nFecha de publicación: {fecha}\n\n{texto[:6000]}"}],
            output_format=Obs,
        )
        o = r.parsed_output
        if not o.hay_precios:
            return {}
        return {"tipo": o.tipo, "superior": o.superior, "regular": o.regular, "diesel": o.diesel,
                "fecha_dato": o.fecha_dato, "resumen": o.resumen, "extraido_por": MODELO_CLAUDE}
    except Exception as e:
        log(f"Claude no extrajo precios ({type(e).__name__}); uso reglas", "WARN")
        return None


# ----------------------------------------------------------------------------- feeds
def _fecha(e) -> datetime:
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return datetime.fromtimestamp(mktime(e[k]), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _fecha_gt(iso_utc: str) -> str:
    try:
        return datetime.fromisoformat(iso_utc).astimezone(TZ_GT).date().isoformat()
    except Exception:
        return iso_utc[:10]


def candidatos() -> list[dict]:
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_VENTANA)
    out = []
    for nombre, url in FUENTES:
        r = http_get(url, timeout=25, intentos=1, headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"})
        if r is None or r.status_code != 200:
            log(f"Feed {nombre}: HTTP {getattr(r, 'status_code', 'sin respuesta')}", "WARN")
            continue
        feed = feedparser.parse(r.content.lstrip())
        for e in feed.entries[:80]:
            titulo = re.sub(r"\s+-\s+[^-]{2,40}$", "", html_mod.unescape(e.get("title", ""))) if "Google" in nombre else html_mod.unescape(e.get("title", ""))
            resumen = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
            if not RX_TEMA.search(titulo + " " + resumen):
                continue
            f = _fecha(e)
            if f < limite:
                continue
            out.append({"fuente": nombre, "url": e.get("link", ""), "titulo": titulo, "fecha": f.isoformat(timespec="minutes"),
                        "resumen": html_mod.unescape(resumen)[:600], "google": "Google" in nombre})
    # Primero las notas que hablan de precios en el titular; luego las demás, de la más nueva a la más vieja.
    out.sort(key=lambda c: c["fecha"], reverse=True)
    out.sort(key=lambda c: 0 if re.search(r"precio|galón|galon|Q\d{2}", c["titulo"], re.I) else 1)
    return out


def observar(c: dict) -> dict | None:
    """Convierte un artículo en una observación {t, superior, regular, diesel, tipo, fuente, url, titulo}."""
    texto = c["titulo"] + ". " + c["resumen"]
    if not c["google"] and c["url"]:
        r = http_get(c["url"], timeout=30, intentos=1)
        if r is not None and r.status_code == 200:
            texto = c["titulo"] + ". " + _texto_articulo(r.text)
    datos = extraer_claude(texto, c["titulo"], c["fecha"])
    if datos is None:
        precios = extraer_precios(texto)
        datos = dict(precios, tipo=clasificar_tipo(texto, c["titulo"]), fecha_dato=_fecha_gt(c["fecha"]), extraido_por="reglas") if precios else {}
    if not datos or not any(datos.get(p) for p in ("superior", "regular", "diesel")):
        return None
    if not _coherente(datos, _referencia()):
        log(f"Precio hoy: descarto cifras incoherentes de {c['fuente']} ({c['titulo'][:50]}): S={datos.get('superior')} R={datos.get('regular')} D={datos.get('diesel')}", "WARN")
        return None
    fecha_dato = datos.get("fecha_dato") or _fecha_gt(c["fecha"])
    if fecha_dato > ahora_gt().date().isoformat():
        fecha_dato = ahora_gt().date().isoformat()
    obs = {"t": c["fecha"], "fecha_dato": fecha_dato, "tipo": datos.get("tipo", "otro"),
           "superior": datos.get("superior"), "regular": datos.get("regular"), "diesel": datos.get("diesel"),
           "fuente": c["fuente"], "url": c["url"], "titulo": c["titulo"][:140], "extraido_por": datos.get("extraido_por")}
    if datos.get("resumen"):
        obs["resumen"] = datos["resumen"]
    return obs


# ----------------------------------------------------------------------------- consolidación
PRIORIDAD = {"promedio": 3, "estacion": 2, "otro": 1, "tope": 0}


def _mediana(vals: list[float]) -> float:
    vals = sorted(vals)
    n = len(vals)
    return round(vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2, 2)


def consolidar(serie: list[dict]) -> dict:
    """Por día y producto: mediana de las observaciones del mejor tipo disponible (promedio > estación > otro).
    Devuelve el último valor por producto, el cambio contra el día anterior, la serie diaria y el tope legal."""
    utiles = [o for o in serie if o["tipo"] != "tope"]
    por_dia: dict[str, dict] = {}
    for o in utiles:
        for p in ("superior", "regular", "diesel"):
            if o.get(p) is None:
                continue
            celda = por_dia.setdefault(o["fecha_dato"], {}).setdefault(p, {"tipo": o["tipo"], "obs": []})
            if PRIORIDAD[o["tipo"]] > PRIORIDAD[celda["tipo"]]:
                celda["tipo"], celda["obs"] = o["tipo"], []
            if PRIORIDAD[o["tipo"]] == PRIORIDAD[celda["tipo"]]:
                celda["obs"].append(o)
    dias = sorted(por_dia)
    for d in dias:
        for p, celda in por_dia[d].items():
            ult = max(celda["obs"], key=lambda o: o["t"])
            celda.update({"valor": _mediana([o[p] for o in celda["obs"]]), "t": ult["t"], "fuente": ult["fuente"], "url": ult["url"], "n": len(celda["obs"])})
            celda.pop("obs")
    ultimo, cambio = {}, {}
    for p in ("superior", "regular", "diesel"):
        con = [d for d in dias if p in por_dia[d]]
        if not con:
            continue
        d = con[-1]
        ultimo[p] = dict(por_dia[d][p], fecha=d)
        if len(con) >= 2:
            prev = por_dia[con[-2]][p]["valor"]
            cambio[p] = {"vs_fecha": con[-2], "q": round(por_dia[d][p]["valor"] - prev, 2), "pct": round((por_dia[d][p]["valor"] / prev - 1) * 100, 1)}
    diario = [{"fecha": d, **{p: por_dia[d][p]["valor"] for p in por_dia[d]}} for d in dias]
    topes = [o for o in serie if o["tipo"] == "tope"]
    tope = None
    if topes:
        t = max(topes, key=lambda o: o["t"])
        tope = {"superior": t.get("superior"), "regular": t.get("regular"), "diesel": t.get("diesel"), "fecha": t["fecha_dato"], "fuente": t["fuente"], "url": t["url"], "titulo": t["titulo"]}
    return {"ultimo": ultimo, "cambio_dia": cambio, "diario": diario, "tope": tope}


RUTA_DEPTOS_HOY = DATA / "departamentos_hoy.json"


def precio_vigente(hoy_datos: dict | None = None) -> tuple[dict, str, str, bool]:
    """(precios, fecha, fuente, es_oficial) del galón en autoservicio.

    Manda el dato MÁS RECIENTE entre el informe oficial del MEM y el promedio que publican los medios.
    En empate gana el oficial. Así, el martes que el MEM sube el precio, el tablero lo refleja el mismo
    día aunque el PDF oficial todavía no se pueda bajar.
    """
    from agente.reporte import precios_vigentes
    pr = leer_json(DATA / "precios.json", {}) or {}
    auto, fecha, fuente = precios_vigentes(pr, hoy_datos if hoy_datos is not None else (leer_json(RUTA, {}) or {}))
    return auto, fecha, fuente, fuente == (pr.get("fuente") or "MEM")


def estimar_departamentos(hoy_datos: dict) -> dict | None:
    """Precio de hoy por departamento = precio de hoy en la capital + diferencia habitual del departamento
    (según la última tabla oficial del MEM en data/departamentos.json). Se marca como estimado; cuando llega
    una tabla oficial más nueva que el dato de hoy, se usa la oficial tal cual."""
    tabla = leer_json(DATA / "departamentos.json", {}) or {}
    filas = tabla.get("departamentos") or []
    # Base = precio de hoy en la capital. Preferimos el precio OFICIAL del MEM (data/precios.json);
    # si no hay uno reciente, usamos lo último de los medios.
    base, fecha_hoy, base_fuente, es_oficial = precio_vigente(hoy_datos)
    if es_oficial:
        base_fuente = "MEM (oficial)"
    if not filas or not base:
        return None
    capital = next((d for d in filas if d["departamento"] == "Guatemala"), None)
    if capital is None:
        return None
    if tabla.get("vigencia_inicio", "") >= fecha_hoy:
        salida = dict(tabla, estimado=False, fecha=tabla.get("vigencia_inicio"))
    else:
        deptos = []
        for d in filas:
            fila = {"cabecera": d["cabecera"], "departamento": d["departamento"]}
            for p in ("superior", "regular", "diesel"):
                if p in base and d.get(p) is not None and capital.get(p) is not None:
                    fila[p] = round(base[p] + (d[p] - capital[p]), 2)
                    fila[p + "_diferencia"] = round(d[p] - capital[p], 2)
            if "regular" in fila:
                deptos.append(fila)
        deptos.sort(key=lambda d: d["regular"])
        salida = {
            "estimado": True,
            "fecha": fecha_hoy,
            "base": base,
            "base_fuente": base_fuente,
            "tabla_oficial_fecha": tabla.get("vigencia_inicio"),
            "mas_barato": deptos[0] if deptos else None,
            "mas_caro": deptos[-1] if deptos else None,
            "departamentos": deptos,
        }
    salida["actualizado"] = ahora_gt().isoformat(timespec="minutes")
    guardar_json(RUTA_DEPTOS_HOY, salida)
    return salida


def actualizar() -> dict:
    actual = leer_json(RUTA, {}) or {}
    serie = actual.get("serie", [])
    vistos = {o["url"] for o in serie} | set(actual.get("sin_precio", []))
    nuevos, sin_precio, revisados = 0, list(actual.get("sin_precio", []))[-300:], 0
    for c in candidatos():
        if c["url"] in vistos:
            continue
        if revisados >= MAX_ARTICULOS:
            break
        revisados += 1
        vistos.add(c["url"])
        try:
            obs = observar(c)
        except Exception as e:
            log(f"Precio hoy: fallo leyendo {c['url'][:80]} ({e})", "WARN")
            obs = None
        if obs:
            serie.append(obs)
            nuevos += 1
            log(f"Precio hoy: {obs['fuente']} {obs['fecha_dato']} {obs['tipo']} S={obs['superior']} R={obs['regular']} D={obs['diesel']} · {obs['titulo'][:60]}")
        else:
            sin_precio.append(c["url"])
    serie.sort(key=lambda o: o["t"])
    serie = serie[-MAX_SERIE:]
    salida = {"actualizado": ahora_gt().isoformat(timespec="minutes"), "revisados": revisados, "nuevos": nuevos,
              **consolidar(serie), "serie": serie, "sin_precio": sin_precio[-300:]}
    guardar_json(RUTA, salida)
    try:
        est = estimar_departamentos(salida)
        if est:
            log(f"Departamentos de hoy: {'estimados' if est.get('estimado') else 'tabla oficial'} ({len(est.get('departamentos', []))}), más barato {est['mas_barato']['departamento'] if est.get('mas_barato') else '–'}")
    except Exception as e:
        log(f"No se pudieron estimar departamentos: {e}", "WARN")
    u = salida["ultimo"]
    log(f"Precio hoy: {nuevos} observaciones nuevas de {revisados} artículos · regular {u.get('regular', {}).get('valor')} ({u.get('regular', {}).get('fecha')})")
    return salida


if __name__ == "__main__":  # pragma: no cover
    actualizar()
