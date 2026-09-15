"""Utilidades compartidas: rutas, log, JSON, HTTP y cliente de Claude."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
CONFIG = RAIZ / "config"
DATA.mkdir(exist_ok=True)

TZ_GT = timezone(timedelta(hours=-6), name="GT")  # Guatemala no usa horario de verano
MODELO_CLAUDE = os.environ.get("CLAUDE_MODELO", "claude-opus-5")

CABECERAS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-GT,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*;q=0.8",
}

try:  # Windows imprime cp1252 por defecto; forzamos UTF-8 para los acentos
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass


ARCHIVO_LLAVES = CONFIG / ".env.local"


def cargar_llaves(ruta: Path | None = None) -> dict:
    """Lee config/.env.local (TELEGRAM_BOT_TOKEN=..., una por línea) y las pone en el entorno.

    Así el bot y Claude funcionan con solo hacer doble clic, sin configurar nada a mano.
    Lo que ya venga en el entorno (por ejemplo los secrets de GitHub Actions) manda y no se pisa.
    El archivo es privado: está en .gitignore y nunca se sube.
    """
    ruta = ruta or ARCHIVO_LLAVES
    puestas = {}
    try:
        if not ruta.exists():
            return puestas
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave, valor = clave.strip(), valor.strip().strip('"').strip("'")
            if clave and valor and not os.environ.get(clave):
                os.environ[clave] = valor
                puestas[clave] = valor
    except Exception as e:  # nunca romper por culpa del archivo de llaves
        print(f"Aviso: no pude leer {ruta}: {e}")
    return puestas


cargar_llaves()


def ahora_gt() -> datetime:
    return datetime.now(TZ_GT)


MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_bonita(iso: str | None) -> str:
    """'2026-09-15' -> '15 de septiembre'. Si no es fecha, devuelve el texto tal cual."""
    try:
        d = datetime.fromisoformat(str(iso)[:10])
        return f"{d.day} de {MESES_ES[d.month - 1]}"
    except Exception:
        return str(iso) if iso else "–"


def log(mensaje: str, nivel: str = "INFO") -> None:
    """Escribe en consola y en data/log.txt (últimas ~2000 líneas)."""
    linea = f"{ahora_gt().strftime('%Y-%m-%d %H:%M')} [{nivel}] {mensaje}"
    print(linea, flush=True)
    ruta = DATA / "log.txt"
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
        lineas.append(linea)
        ruta.write_text("\n".join(lineas[-2000:]) + "\n", encoding="utf-8")
    except Exception:  # pragma: no cover
        pass


def leer_json(ruta: Path, defecto=None):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except Exception:
        return defecto


def guardar_json(ruta: Path, datos) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def http_get(url: str, timeout: int = 30, intentos: int = 2, **kwargs) -> requests.Response | None:
    """GET con cabeceras de navegador y reintentos. Devuelve None si falla."""
    cabeceras = dict(CABECERAS_HTTP)
    cabeceras.update(kwargs.pop("headers", {}))
    for i in range(intentos):
        try:
            r = requests.get(url, headers=cabeceras, timeout=timeout, **kwargs)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 404, 429):
                return r  # no tiene sentido reintentar
        except requests.RequestException as e:
            log(f"HTTP fallo {url}: {e}", "WARN")
        time.sleep(1 + i)
    return None


def cliente_claude():
    """Devuelve un cliente de Anthropic o None si no hay credenciales."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None
    try:
        import anthropic

        return anthropic.Anthropic()
    except Exception as e:  # pragma: no cover
        log(f"No se pudo crear cliente de Claude: {e}", "WARN")
        return None


def cargar_plan() -> dict:
    plan = leer_json(CONFIG / "plan.json", {}) or {}
    plan.setdefault("plus_activo", False)
    plan.setdefault("precio_mensual_q", 0)
    plan.setdefault("moneda", "GTQ")
    plan.setdefault("link_pago", "")
    return plan
