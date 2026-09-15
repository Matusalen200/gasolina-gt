"""Lector del MEM con navegador real (Playwright/Chromium), para correr desde una PC normal.

El sitio del MEM está detrás de Cloudflare y rechaza a curl, Python y GitHub Actions. Un navegador real
desde una conexión doméstica normalmente pasa la verificación automática. Este script:
  1. Abre la página de precios con un perfil persistente (data/.navegador, no se sube al repo).
  2. Espera la tabla "Precios Monitoreados". Si aparece un reto interactivo (casilla de Cloudflare), NO lo
     resuelve: avisa en el log y termina. Nadie salta verificaciones aquí.
  3. Lee la tabla del área metropolitana (autoservicio y servicio completo, dos fechas, tipo de cambio).
  4. Descarga con las cookies del navegador los PDFs enlazados (Informe Ejecutivo, informe nacional por
     departamento, precios más bajos) y los pasa a los mismos parsers de agente/mem.py.
  5. Guarda data/precios.json, data/departamentos.json y el historial; opcionalmente hace commit y push.

Uso:
  python agente/mem_navegador.py            # lee y guarda
  python agente/mem_navegador.py --push     # además commit + push (para la tarea programada)
  python agente/mem_navegador.py --visible  # con ventana, por si quieres ver qué pasa

Programar en Windows (martes 8:30, cuando el MEM ya publicó):
  schtasks /Create /SC WEEKLY /D TUE /ST 08:30 /TN "GasolinaGT MEM" /TR "\"<ruta>\\.venv\\Scripts\\python.exe\" \"<ruta>\\agente\\mem_navegador.py\" --push"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agente import mem  # noqa: E402
from agente.comun import DATA, RAIZ, log  # noqa: E402

PERFIL = DATA / ".navegador"
ESPERA_SEG = 40


def leer_con_navegador(visible: bool = False) -> dict:
    from playwright.sync_api import sync_playwright

    resultado = {"tabla": None, "pdfs": 0, "bloqueado": False}
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            str(PERFIL), headless=not visible, locale="es-GT",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        pagina = contexto.new_page()
        pagina.goto(mem.URL_LISTADO, wait_until="domcontentloaded", timeout=60_000)
        try:
            pagina.wait_for_function(
                "() => document.body && document.body.innerText.includes('Precios Monitoreados')",
                timeout=ESPERA_SEG * 1000,
            )
        except Exception:
            html = pagina.content()
            if "challenges.cloudflare.com" in html or "Un momento" in pagina.title() or "Just a moment" in pagina.title():
                log("MEM (navegador): Cloudflare pide verificación interactiva; no se intenta saltar. Abre la página una vez a mano en esta misma PC y vuelve a correr.", "WARN")
                resultado["bloqueado"] = True
            else:
                log("MEM (navegador): la página cargó pero no apareció la tabla de precios", "WARN")
            contexto.close()
            return resultado

        html = pagina.content()
        (DATA / "mem_ultima_pagina.html").write_text(html, encoding="utf-8")
        tabla = mem.parsear_tabla_html(html)
        if tabla and tabla.get("autoservicio", {}).get("superior"):
            mem.integrar_ejecutivo(tabla, "MEM (página oficial)", mem.URL_LISTADO)
            resultado["tabla"] = tabla
            log(f"MEM (navegador): tabla leída, monitoreo {tabla.get('fecha_monitoreo')} · regular {tabla['autoservicio'].get('regular')}")

        enlaces = mem.extraer_enlaces(html)
        vistos = set()
        for e in enlaces[:8]:
            if e["tipo"] in vistos:
                continue
            try:
                r = pagina.request.get(e["url"], timeout=60_000)
                datos = r.body() if r.ok else None
            except Exception as ex:
                log(f"MEM (navegador): no se pudo bajar {e['url']} ({ex})", "WARN")
                datos = None
            if datos and datos[:5] == b"%PDF-":
                if mem.procesar_pdf(datos, e["tipo"], "MEM (página oficial)", e["url"]):
                    resultado["pdfs"] += 1
                    vistos.add(e["tipo"])
        contexto.close()
    return resultado


def commit_y_push() -> None:
    def git(*args):
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)

    git("add", "data")
    if git("diff", "--cached", "--quiet").returncode == 0:
        log("MEM (navegador): sin cambios que subir")
        return
    git("commit", "-m", "datos: informe del MEM leído con navegador local")
    r = git("push")
    log("MEM (navegador): push " + ("ok" if r.returncode == 0 else f"falló: {r.stderr.strip()[:200]}"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--visible", action="store_true")
    args = ap.parse_args(argv)
    try:
        res = leer_con_navegador(visible=args.visible)
    except Exception as e:
        log(f"MEM (navegador) falló: {type(e).__name__}: {e}", "ERROR")
        return 1
    if res["bloqueado"]:
        return 2
    if args.push:
        commit_y_push()
    return 0


if __name__ == "__main__":
    sys.exit(main())
