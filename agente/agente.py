"""Orquestador de Gasolina GT.

Uso:
  python agente/agente.py                 # corrida horaria: MEM + mercado + noticias + señal
  python agente/agente.py --diario        # además: reporte diario, aciertos, proyección y Telegram
  python agente/agente.py --solo mem      # una sola etapa (mem, hoy, mercado, noticias, senal, reporte, proyeccion, telegram)
  python agente/agente.py --semilla DIR   # carga PDFs del MEM desde una carpeta (p. ej. tests/fixtures)

Cada etapa está aislada: si una falla, se registra en data/log.txt y las demás siguen.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agente.comun import ahora_gt, log  # noqa: E402


def _etapa(nombre: str, funcion):
    try:
        log(f"--- {nombre} ---")
        return funcion()
    except Exception as e:  # nunca romper la corrida completa
        log(f"Etapa {nombre} falló: {type(e).__name__}: {e}", "ERROR")
        return None


def etapa_mem():
    from agente import mem
    return mem.actualizar()


def etapa_hoy():
    from agente import hoy
    return hoy.actualizar()


def etapa_mercado():
    from agente import mercado
    return mercado.actualizar()


def etapa_noticias():
    from agente import noticias
    return noticias.actualizar()


def etapa_senal():
    from agente import senal
    return senal.actualizar()


def etapa_reporte():
    from agente import reporte
    return reporte.generar()


def etapa_proyeccion():
    from agente import proyeccion
    return proyeccion.actualizar()


def etapa_telegram():
    from bot import telegram
    return telegram.corrida()


def etapa_mensual():
    from reportes import mensual
    return mensual.generar()


ETAPAS = {
    "mem": etapa_mem,
    "hoy": etapa_hoy,
    "mercado": etapa_mercado,
    "noticias": etapa_noticias,
    "senal": etapa_senal,
    "reporte": etapa_reporte,
    "proyeccion": etapa_proyeccion,
    "telegram": etapa_telegram,
    "mensual": etapa_mensual,
}


def semilla(carpeta: str) -> None:
    from agente import mem
    for ruta in sorted(Path(carpeta).glob("*.pdf")):
        tipo, _ = mem.clasificar_nombre(ruta.name)
        mem.procesar_pdf(ruta, tipo, "MEM (archivo)", ruta.name)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Agente Gasolina GT")
    ap.add_argument("--diario", action="store_true", help="incluye reporte diario, proyección y Telegram")
    ap.add_argument("--solo", choices=sorted(ETAPAS), help="ejecuta una sola etapa")
    ap.add_argument("--semilla", metavar="DIR", help="carga PDFs del MEM desde una carpeta")
    args = ap.parse_args(argv)

    log(f"Inicio corrida {ahora_gt().strftime('%Y-%m-%d %H:%M')} GT")
    if args.semilla:
        semilla(args.semilla)
        return 0
    if args.solo:
        _etapa(args.solo, ETAPAS[args.solo])
        return 0

    for nombre in ("mem", "hoy", "mercado", "noticias", "senal"):
        _etapa(nombre, ETAPAS[nombre])
    if args.diario:
        for nombre in ("proyeccion", "reporte", "telegram"):
            _etapa(nombre, ETAPAS[nombre])
        if ahora_gt().day == 1:
            _etapa("mensual", ETAPAS["mensual"])
    else:
        _etapa("telegram", ETAPAS["telegram"])  # responde comandos pendientes cada hora
    log("Fin corrida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
