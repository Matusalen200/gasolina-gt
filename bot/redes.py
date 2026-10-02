"""Publica el reporte diario en Facebook, Instagram y X, además del canal de Telegram.

Cada red es independiente: si una falla o no está configurada, las demás igual publican y queda
anotado en la bitácora. Nunca se publica dos veces lo mismo el mismo día.

Qué hace falta para cada una (ver docs/redes.md para el paso a paso):
  Facebook   FACEBOOK_PAGE_ID y FACEBOOK_TOKEN   (token de una página tuya, permiso de publicar)
  Instagram  INSTAGRAM_USER_ID y FACEBOOK_TOKEN  (cuenta de empresa o creador, ligada a esa página)
  X          X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET

Instagram EXIGE una imagen y que esté publicada en internet: se usa la gráfica que el agente ya
sube al tablero. Por eso, sin tablero público no se puede publicar en Instagram.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from agente.comun import DATA, ahora_gt, guardar_json, leer_json, log  # noqa: E402

RUTA_ESTADO = DATA / "redes_estado.json"
GRAFO = "https://graph.facebook.com/v21.0"
REDES = ("facebook", "instagram", "x")


def _llave(nombre: str) -> str:
    return os.environ.get(nombre, "").strip()


def url_de_la_imagen(nombre: str = "tarjeta_redes.png") -> str | None:
    """Dirección pública de una imagen del proyecto, deducida de la del tablero."""
    tablero = _llave("TABLERO_URL")
    if not tablero or "github.io" not in tablero:
        return None
    return tablero.rstrip("/").removesuffix("/web") + "/data/" + nombre


# ----------------------------------------------------------------------------- Facebook
def publicar_facebook(mensaje: str, imagen: str | None) -> bool:
    pagina, token = _llave("FACEBOOK_PAGE_ID"), _llave("FACEBOOK_TOKEN")
    if not pagina or not token:
        return False
    try:
        if imagen:
            r = requests.post(f"{GRAFO}/{pagina}/photos",
                              data={"url": imagen, "caption": mensaje, "access_token": token}, timeout=60)
        else:
            r = requests.post(f"{GRAFO}/{pagina}/feed",
                              data={"message": mensaje, "access_token": token}, timeout=60)
        datos = r.json()
        if r.status_code == 200 and datos.get("id"):
            log(f"Facebook: publicado ({datos['id']})")
            return True
        log(f"Facebook no publicó: {datos.get('error', {}).get('message', datos)}", "WARN")
    except Exception as e:
        log(f"Facebook falló: {type(e).__name__}: {e}", "WARN")
    return False


# ----------------------------------------------------------------------------- Instagram
def publicar_instagram(mensaje: str, imagen: str | None) -> bool:
    usuario, token = _llave("INSTAGRAM_USER_ID"), _llave("FACEBOOK_TOKEN")
    if not usuario or not token:
        return False
    if not imagen:
        log("Instagram: hace falta una imagen publicada en internet; se omite", "WARN")
        return False
    try:
        # Instagram se publica en dos pasos: primero se prepara la foto, después se suelta.
        r = requests.post(f"{GRAFO}/{usuario}/media",
                          data={"image_url": imagen, "caption": mensaje, "access_token": token}, timeout=90)
        datos = r.json()
        contenedor = datos.get("id")
        if not contenedor:
            log(f"Instagram no preparó la foto: {datos.get('error', {}).get('message', datos)}", "WARN")
            return False
        r = requests.post(f"{GRAFO}/{usuario}/media_publish",
                          data={"creation_id": contenedor, "access_token": token}, timeout=90)
        datos = r.json()
        if datos.get("id"):
            log(f"Instagram: publicado ({datos['id']})")
            return True
        log(f"Instagram no publicó: {datos.get('error', {}).get('message', datos)}", "WARN")
    except Exception as e:
        log(f"Instagram falló: {type(e).__name__}: {e}", "WARN")
    return False


# ----------------------------------------------------------------------------- X
def publicar_x(mensaje: str, imagen: str | None) -> bool:
    claves = [_llave(n) for n in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")]
    if not all(claves):
        return False
    try:
        from requests_oauthlib import OAuth1
    except Exception:
        log("X: falta la librería requests-oauthlib (pip install -r requirements.txt)", "WARN")
        return False
    firma = OAuth1(*claves)
    texto = mensaje if len(mensaje) <= 280 else mensaje[:277].rsplit(" ", 1)[0] + "…"
    try:
        r = requests.post("https://api.x.com/2/tweets", json={"text": texto}, auth=firma, timeout=60)
        if r.status_code in (200, 201):
            log("X: publicado")
            return True
        log(f"X no publicó ({r.status_code}): {r.text[:160]}", "WARN")
    except Exception as e:
        log(f"X falló: {type(e).__name__}: {e}", "WARN")
    return False


PUBLICADORES = {"facebook": publicar_facebook, "instagram": publicar_instagram, "x": publicar_x}


# ----------------------------------------------------------------------------- corrida
def texto_para_redes(mensaje: str) -> str:
    """El mismo mensaje, con la invitación al canal y las etiquetas que ayudan a que lo vean."""
    partes = [mensaje.strip()]
    canal = _llave("CANAL_URL")
    if canal:
        partes.append(f"Recibe esto cada mañana: {canal}")
    tablero = _llave("TABLERO_URL")
    if tablero:
        partes.append(f"Mapa de gasolineras y gráficas: {tablero}")
    partes.append("#Guatemala #gasolina #precios #combustibles #GasolinaGT")
    return "\n\n".join(partes)


def configuradas() -> list[str]:
    """Qué redes están listas para publicar."""
    listas = []
    if _llave("FACEBOOK_PAGE_ID") and _llave("FACEBOOK_TOKEN"):
        listas.append("facebook")
    if _llave("INSTAGRAM_USER_ID") and _llave("FACEBOOK_TOKEN"):
        listas.append("instagram")
    if all(_llave(n) for n in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
        listas.append("x")
    return listas


def publicar(forzar: bool = False) -> dict:
    """Publica el reporte del día en todas las redes que estén conectadas."""
    ultimo = leer_json(DATA / "reportes" / "ultimo.json", {}) or {}
    mensaje, fecha = ultimo.get("mensaje"), ultimo.get("fecha")
    if not mensaje:
        log("Redes: todavía no hay reporte del día", "WARN")
        return {}

    listas = configuradas()
    if not listas:
        log("Redes: ninguna conectada todavía (ver docs/redes.md)")
        return {}

    # En redes va la tarjeta (llama la atención); si no se pudo hacer, la gráfica.
    imagen = url_de_la_imagen("tarjeta_redes.png") if (DATA / "tarjeta_redes.png").exists()         else url_de_la_imagen("grafica_precios.png")
    mensaje = texto_para_redes(mensaje)
    estado = leer_json(RUTA_ESTADO, {}) or {}
    resultado = {}
    for red in listas:
        if not forzar and estado.get(red) == fecha:
            resultado[red] = "ya estaba publicado"
            continue
        if PUBLICADORES[red](mensaje, imagen):
            estado[red] = fecha
            resultado[red] = "publicado"
        else:
            resultado[red] = "falló"
    estado["ultima_corrida"] = ahora_gt().isoformat(timespec="minutes")
    guardar_json(RUTA_ESTADO, estado)
    log("Redes: " + ", ".join(f"{k}={v}" for k, v in resultado.items()))
    return resultado


if __name__ == "__main__":  # pragma: no cover
    from agente.comun import cargar_llaves
    cargar_llaves()
    if "--probar" in sys.argv:
        print("Redes conectadas:", ", ".join(configuradas()) or "ninguna")
        print("Imagen que se usaría:", url_de_la_imagen() or "(no hay tablero público)")
    else:
        print(publicar(forzar="--forzar" in sys.argv))
