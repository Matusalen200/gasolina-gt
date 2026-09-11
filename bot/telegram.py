"""Bot de Telegram: publica el reporte diario en el canal y responde /senal, /precio <departamento>, /plus.

Secrets: TELEGRAM_BOT_TOKEN y TELEGRAM_CHANNEL_ID (p. ej. @gasolinagt o -100123456789).
Corre dentro del workflow: cada hora atiende los comandos pendientes (getUpdates) y a las 7:00 publica.
Si no hay token, no hace nada y lo deja en el log.
"""
from __future__ import annotations

import os
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from agente.comun import DATA, ahora_gt, cargar_plan, guardar_json, leer_json, log  # noqa: E402
from bot import plantillas as P  # noqa: E402

RUTA_ESTADO = DATA / "telegram_estado.json"
API = "https://api.telegram.org/bot{token}/{metodo}"


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def _llamar(metodo: str, **params):
    try:
        r = requests.post(API.format(token=_token(), metodo=metodo), json=params, timeout=30)
        datos = r.json()
        if not datos.get("ok"):
            log(f"Telegram {metodo}: {datos.get('description')}", "WARN")
            return None
        return datos["result"]
    except Exception as e:
        log(f"Telegram {metodo} falló: {e}", "WARN")
        return None


def enviar(chat_id, texto: str):
    return _llamar("sendMessage", chat_id=chat_id, text=texto, disable_web_page_preview=True)


# ----------------------------------------------------------------------------- respuestas
def _normalizar(txt: str) -> str:
    txt = unicodedata.normalize("NFD", txt.lower())
    return "".join(c for c in txt if unicodedata.category(c) != "Mn").strip()


def respuesta_senal() -> str:
    senal = leer_json(DATA / "senal.json", {}) or {}
    if not senal:
        return "Todavía estoy calibrando la señal. Vuelve en unas horas."
    return P.MENSAJE_SENAL.format(
        emoji=senal.get("emoji", "🟡"), veredicto=senal.get("veredicto", "Calibrando"),
        cambio=senal.get("cambio_estimado_texto", ""), razon=senal.get("razon", ""),
        proximo_martes=senal.get("proximo_martes", "próximo"),
    )


def respuesta_precio(consulta: str) -> str:
    deptos = leer_json(DATA / "departamentos.json", {}) or {}
    filas = deptos.get("departamentos", [])
    if not filas:
        return "Aún no tengo los precios por departamento."
    clave = _normalizar(consulta)
    if not clave:
        lista = ", ".join(sorted(d["departamento"] for d in filas))
        return P.MENSAJE_PRECIO_NO_ENCONTRADO.format(lista=lista)
    encontrado = None
    for d in filas:
        if clave in _normalizar(d["departamento"]) or clave in _normalizar(d["cabecera"]):
            encontrado = d
            break
    if not encontrado:
        lista = ", ".join(sorted(d["departamento"] for d in filas))
        return P.MENSAJE_PRECIO_NO_ENCONTRADO.format(lista=lista)
    barato = deptos.get("mas_barato") or filas[0]
    if encontrado["departamento"] == barato["departamento"]:
        comparacion = P.COMPARACION_MAS_BARATO
    else:
        comparacion = P.COMPARACION_OTRO.format(diferencia=f"Q{encontrado['regular'] - barato['regular']:.2f}", depto_barato=barato["departamento"])
    return P.MENSAJE_PRECIO.format(
        departamento=encontrado["departamento"], cabecera=encontrado["cabecera"],
        superior=f"Q{encontrado['superior']:.2f}", regular=f"Q{encontrado['regular']:.2f}", diesel=f"Q{encontrado['diesel']:.2f}",
        comparacion=comparacion, fecha_mem=deptos.get("vigencia_inicio", "–"),
    )


def respuesta_plus() -> str:
    plan = cargar_plan()
    if not plan.get("plus_activo") or not plan.get("precio_mensual_q"):
        return P.MENSAJE_PLUS_INACTIVO
    return P.MENSAJE_PLUS.format(moneda=plan["moneda"], precio=plan["precio_mensual_q"], link=plan.get("link_pago") or "")


def responder(texto: str) -> str | None:
    """Devuelve la respuesta para un comando o None si no es un comando conocido."""
    t = texto.strip()
    if not t.startswith("/"):
        return None
    partes = t.split(maxsplit=1)
    comando = partes[0].split("@")[0].lower()
    arg = partes[1] if len(partes) > 1 else ""
    if comando == "/senal":
        return respuesta_senal()
    if comando == "/precio":
        return respuesta_precio(arg)
    if comando == "/plus":
        return respuesta_plus()
    if comando in ("/start", "/ayuda", "/help"):
        return P.MENSAJE_AYUDA
    return None


# ----------------------------------------------------------------------------- corrida
def atender_comandos(estado: dict) -> int:
    offset = estado.get("offset", 0)
    updates = _llamar("getUpdates", offset=offset, timeout=0, allowed_updates=["message", "channel_post"]) or []
    respondidos = 0
    for u in updates:
        estado["offset"] = u["update_id"] + 1
        msg = u.get("message") or u.get("channel_post") or {}
        texto = msg.get("text") or ""
        resp = responder(texto)
        if resp and msg.get("chat"):
            enviar(msg["chat"]["id"], resp)
            respondidos += 1
    return respondidos


def publicar_diario(estado: dict) -> bool:
    canal = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
    ultimo = leer_json(DATA / "reportes" / "ultimo.json", {}) or {}
    if not canal or not ultimo.get("mensaje"):
        return False
    if estado.get("ultimo_publicado") == ultimo["fecha"]:
        return False
    if enviar(canal, ultimo["mensaje"]) is not None:
        estado["ultimo_publicado"] = ultimo["fecha"]
        log(f"Telegram: reporte {ultimo['fecha']} publicado en {canal}")
        return True
    return False


def corrida() -> dict:
    if not _token():
        log("Telegram: sin TELEGRAM_BOT_TOKEN, se omite")
        return {"omitido": True}
    estado = leer_json(RUTA_ESTADO, {}) or {}
    publicado = publicar_diario(estado)
    n = atender_comandos(estado)
    estado["ultima_corrida"] = ahora_gt().isoformat(timespec="minutes")
    guardar_json(RUTA_ESTADO, estado)
    log(f"Telegram: {n} comandos respondidos, publicado={publicado}")
    return {"comandos": n, "publicado": publicado}


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) > 1:  # prueba local: python bot/telegram.py "/precio Petén"
        print(responder(" ".join(sys.argv[1:])))
    else:
        corrida()
