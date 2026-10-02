"""Todas las gasolineras de Guatemala, con su ubicación, para el mapa.

Las ubicaciones salen de OpenStreetMap, que es un mapa libre hecho por voluntarios: es gratis, no pide
cuenta ni tarjeta, y tiene más de mil gasolineras del país ya marcadas. Lo que OpenStreetMap NO tiene
son los precios; esos salen del monitoreo del MEM (agente/estaciones.py) para las estaciones que el
Ministerio visita cada semana. Para las demás se muestra el precio de referencia de su departamento.

Guarda data/gasolineras.json. Se vuelve a bajar una vez por semana; el resto del tiempo se reusa.
"""
from __future__ import annotations

import math
import unicodedata
from datetime import date, datetime, timedelta

import requests

from agente.comun import DATA, ahora_gt, guardar_json, leer_json, log

RUTA = DATA / "gasolineras.json"
DIAS_REFRESCO = 7
ESPEJOS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]
CONSULTA = """
[out:json][timeout:90];
area["ISO3166-1"="GT"][admin_level=2]->.gt;
nwr["amenity"="fuel"](area.gt);
out center tags;
"""
AGENTE = "GasolinaGT/1.0 (proyecto ciudadano de precios de combustible en Guatemala)"

# Cabeceras departamentales. Sirven para decir a qué departamento pertenece cada gasolinera
# (se toma la cabecera más cercana), y así mostrarle el precio de referencia que le toca.
CABECERAS = {
    "Guatemala": (14.6349, -90.5069), "Sacatepéquez": (14.5586, -90.7295),
    "Chimaltenango": (14.6611, -90.8208), "Escuintla": (14.3050, -90.7850),
    "Santa Rosa": (14.2769, -90.2986), "Sololá": (14.7722, -91.1833),
    "Totonicapán": (14.9111, -91.3611), "Quetzaltenango": (14.8347, -91.5181),
    "Suchitepéquez": (14.5347, -91.5031), "Retalhuleu": (14.5361, -91.6778),
    "San Marcos": (14.9639, -91.7944), "Huehuetenango": (15.3197, -91.4711),
    "Quiché": (15.0306, -91.1489), "Baja Verapaz": (15.1022, -90.3161),
    "Alta Verapaz": (15.4708, -90.3711), "Petén": (16.9283, -89.8925),
    "Izabal": (15.7278, -88.5944), "Zacapa": (14.9722, -89.5306),
    "Chiquimula": (14.8000, -89.5450), "Jalapa": (14.6333, -89.9889),
    "Jutiapa": (14.2917, -89.8958), "El Progreso": (14.8556, -90.0700),
}


def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia en línea recta entre dos puntos del mapa."""
    r = 6371.0
    dlat, dlon = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    x = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(x))


def departamento_de(lat: float, lon: float) -> str:
    """Departamento aproximado: el de la cabecera más cercana."""
    return min(CABECERAS, key=lambda d: distancia_km((lat, lon), CABECERAS[d]))


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn").lower()


def descargar() -> list[dict] | None:
    """Baja las gasolineras de OpenStreetMap. Devuelve None si ningún espejo responde."""
    for url in ESPEJOS:
        try:
            r = requests.post(url, data={"data": CONSULTA}, headers={"User-Agent": AGENTE}, timeout=150)
            if r.status_code != 200:
                log(f"Mapa: {url.split('/')[2]} respondió {r.status_code}", "WARN")
                continue
            elementos = r.json().get("elements", [])
            if elementos:
                log(f"Mapa: {len(elementos)} gasolineras bajadas de OpenStreetMap ({url.split('/')[2]})")
                return elementos
        except Exception as e:
            log(f"Mapa: {url.split('/')[2]} falló ({type(e).__name__})", "WARN")
    return None


def limpiar(elementos: list[dict]) -> list[dict]:
    """Deja solo lo que sirve para el mapa: nombre, marca, ubicación y departamento."""
    salida, vistas = [], set()
    for e in elementos:
        t = e.get("tags", {}) or {}
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        nombre = (t.get("name") or t.get("brand") or t.get("operator") or "Gasolinera").strip()
        clave = (round(lat, 4), round(lon, 4))
        if clave in vistas:
            continue
        vistas.add(clave)
        salida.append({
            "n": nombre[:60],
            "m": (t.get("brand") or "").strip()[:30] or None,
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "d": departamento_de(float(lat), float(lon)),
        })
    salida.sort(key=lambda g: (g["d"], g["n"]))
    return salida


# Palabras que están en casi todos los nombres y por eso no sirven para reconocer una estación.
GENERICAS = {"estacion", "estacion", "servicio", "gasolinera", "gasolinera", "combustibles", "auto",
             "centro", "parada", "shell", "puma", "texaco", "uno", "delta", "petro"}
CERCA_KM = 5.0
DIAS_UTIL = 14      # pasado eso, un precio por gasolinera ya no se muestra


def _distintivas(nombre: str) -> set[str]:
    """Palabras que de verdad identifican a una gasolinera (quita marcas y muletillas)."""
    return {p for p in _sin_acentos(nombre).replace(",", " ").split()
            if len(p) > 3 and p not in GENERICAS}


def marcar_con_precio(gasolineras: list[dict], monitoreadas: list[dict]) -> int:
    """Le pega el precio real a las gasolineras que el MEM sí visitó esta semana.

    Se aparean solo si comparten una palabra distintiva Y están cerca una de la otra. Sin las dos
    condiciones no se aparean: antes, palabras como 'estación' o 'servicio' juntaban gasolineras
    de departamentos distintos.
    """
    pegadas = 0
    for est in monitoreadas:
        precios = {"s": est["superior"], "r": est["regular"], "d": est["diesel"]}
        palabras = _distintivas(est["nombre"])
        punto = (est.get("lat"), est.get("lon")) if est.get("lat") else None
        mejor, mejor_puntaje = None, 0
        if palabras and punto:
            for g in gasolineras:
                if g.get("p"):
                    continue
                if distancia_km(punto, (g["lat"], g["lon"])) > CERCA_KM:
                    continue
                comunes = len(palabras & _distintivas(g["n"]))
                if comunes > mejor_puntaje:
                    mejor, mejor_puntaje = g, comunes
        if mejor and mejor_puntaje >= 1:
            mejor["p"] = precios
            mejor["mem"] = True
            pegadas += 1
        elif punto:   # no está en el mapa libre: la agregamos con la ubicación que tenemos
            gasolineras.append({"n": est["nombre"][:60], "m": None, "lat": est["lat"], "lon": est["lon"],
                                "d": departamento_de(est["lat"], est["lon"]), "p": precios, "mem": True,
                                "aprox": not est.get("ubicacion_exacta", False)})
            pegadas += 1
    return pegadas


def _dias_desde(fecha_iso) -> int | None:
    try:
        return (ahora_gt().date() - date.fromisoformat(str(fecha_iso))).days
    except Exception:
        return None


def actualizar(forzar: bool = False) -> dict:
    actual = leer_json(RUTA, {}) or {}
    fresco = False
    if actual.get("actualizado") and not forzar:
        try:
            dias = (ahora_gt().date() - date.fromisoformat(actual["actualizado"][:10])).days
            fresco = dias < DIAS_REFRESCO
        except Exception:
            fresco = False

    if fresco and actual.get("gasolineras"):
        gasolineras = [g for g in actual["gasolineras"] if not g.get("mem")]
        for g in gasolineras:
            g.pop("p", None)
            g.pop("mem", None)
        log(f"Mapa: reuso las {len(gasolineras)} gasolineras que ya tenía (se rebajan cada {DIAS_REFRESCO} días)")
    else:
        elementos = descargar()
        if elementos is None:
            if actual:
                log("Mapa: OpenStreetMap no respondió; conservo el mapa anterior", "WARN")
                return actual
            log("Mapa: OpenStreetMap no respondió y no tengo mapa guardado", "WARN")
            return {}
        gasolineras = limpiar(elementos)

    est = leer_json(DATA / "estaciones.json", {}) or {}
    monitoreadas = est.get("autoservicio", [])
    dias = _dias_desde(est.get("fecha_monitoreo"))
    if dias is not None and dias > DIAS_UTIL:
        log(f"Mapa: la lista de gasolineras del MEM tiene {dias} días; no se muestran esos precios "
            f"para no engañar. Se usa el de referencia de cada departamento.", "WARN")
        monitoreadas = []
    con_precio = marcar_con_precio(gasolineras, monitoreadas)

    from collections import Counter
    por_depto = Counter(g["d"] for g in gasolineras)
    salida = {
        "actualizado": ahora_gt().isoformat(timespec="minutes"),
        "total": len(gasolineras),
        "con_precio_real": con_precio,
        "fecha_verificado": est.get("fecha_monitoreo"),
        "por_departamento": dict(sorted(por_depto.items(), key=lambda x: -x[1])),
        "fuente": "OpenStreetMap (ubicaciones) y MEM (precios monitoreados)",
        "gasolineras": gasolineras,
    }
    guardar_json(RUTA, salida)
    log(f"Mapa: {len(gasolineras)} gasolineras en {len(por_depto)} departamentos, "
        f"{con_precio} con precio real del MEM")
    return salida


if __name__ == "__main__":  # pragma: no cover
    actualizar(forzar=True)
