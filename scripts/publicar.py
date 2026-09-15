"""Asistente para poner Gasolina GT en internet, gratis, sin que tu PC esté encendida.

Doble clic en «Publicar en internet.bat», o:
    .venv\\Scripts\\python.exe scripts\\publicar.py

Qué hace:
  1. Comprueba que tengas GitHub CLI y te ayuda a entrar a tu cuenta.
  2. Crea el repositorio PÚBLICO (así los servidores de GitHub trabajan sin límite y sin costo).
  3. Sube tus llaves como «secrets» (nadie más las ve, ni siquiera quien mire el código).
  4. Prende el tablero en internet (GitHub Pages).
  5. Lanza la primera corrida y te da las direcciones.

Después de esto, GitHub revisa precios cada hora y publica en tu canal todos los días a las 7:00,
aunque tu computadora esté apagada.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from agente.comun import ARCHIVO_LLAVES, cargar_llaves  # noqa: E402

RUTAS_GH = [r"C:\Program Files\GitHub CLI\gh.exe", r"C:\Program Files (x86)\GitHub CLI\gh.exe"]
SECRETS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID", "ANTHROPIC_API_KEY")


def titulo(texto: str) -> None:
    print("\n" + "─" * 60)
    print(texto)
    print("─" * 60)


def buscar_gh() -> str | None:
    ruta = shutil.which("gh")
    if ruta:
        return ruta
    return next((r for r in RUTAS_GH if Path(r).exists()), None)


def gh(*args, mostrar: bool = False, entrada=None):
    """Corre gh. mostrar=True deja que veas y respondas (para el login)."""
    cmd = [GH, *args]
    if mostrar:
        return subprocess.run(cmd, cwd=RAIZ).returncode == 0, ""
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, input=entrada)
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or r.stderr).strip()


# ----------------------------------------------------------------------------- pasos
def paso_gh() -> bool:
    titulo("PASO 1 de 5 · Tu cuenta de GitHub")
    ok, salida = gh("auth", "status")
    if ok:
        ok2, usuario = gh("api", "user", "--jq", ".login")
        print(f"✅ Ya estás dentro como {usuario}." if ok2 else "✅ Ya estás dentro de GitHub.")
        return True
    print("Necesito que entres a tu cuenta de GitHub. Es gratis.")
    print("Si no tienes cuenta, créala en https://github.com/signup y vuelve a correr esto.")
    print("\nAhora GitHub te va a dar un código de 8 letras y abrirá tu navegador.")
    print("Pega el código ahí y autoriza. Luego vuelve a esta ventana.")
    input("\nDale Enter para empezar... ")
    gh("auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web", mostrar=True)
    ok, _ = gh("auth", "status")
    print("✅ Listo, ya entraste." if ok else "❌ No se completó el ingreso. Vuelve a intentar.")
    return ok


def paso_repo() -> str | None:
    titulo("PASO 2 de 5 · El repositorio")
    ok, usuario = gh("api", "user", "--jq", ".login")
    if not ok:
        print("No pude ver tu usuario de GitHub.")
        return None
    ok_remoto, remotos = git("remote")
    if ok_remoto and "origin" in remotos:
        ok_url, url = git("remote", "get-url", "origin")
        print(f"Ya estaba conectado a: {url}")
        print("Subiendo los cambios...")
        ok_push, msg = git("push", "-u", "origin", "main")
        if not ok_push:
            print(f"Aviso al subir: {msg[:200]}")
        return usuario

    nombre = input("\nNombre para el proyecto en GitHub [gasolina-gt]: ").strip() or "gasolina-gt"
    print(f"\nCreando https://github.com/{usuario}/{nombre} (público)...")
    print("Público es importante: así los servidores de GitHub trabajan sin límite y sin cobrarte.")
    ok, msg = gh("repo", "create", nombre, "--public", "--source", ".", "--remote", "origin",
                 "--description", "Dónde y cuándo llenar gasolina en Guatemala", "--push")
    if not ok:
        print(f"❌ No pude crearlo: {msg[:300]}")
        return None
    print("✅ Repositorio creado y código subido.")
    return usuario


def paso_secrets() -> None:
    titulo("PASO 3 de 5 · Tus llaves, guardadas en secreto")
    cargar_llaves()
    puestas = []
    for nombre in SECRETS:
        valor = os.environ.get(nombre, "").strip()
        if not valor:
            continue
        ok, msg = gh("secret", "set", nombre, entrada=valor)
        if ok:
            puestas.append(nombre)
        else:
            print(f"   Aviso con {nombre}: {msg[:150]}")
    if puestas:
        print("✅ Guardadas en GitHub (cifradas, nadie puede leerlas): " + ", ".join(puestas))
    faltan = [n for n in SECRETS if n not in puestas]
    if "TELEGRAM_BOT_TOKEN" in faltan or "TELEGRAM_CHANNEL_ID" in faltan:
        print("\n⚠️  Falta conectar Telegram. Haz doble clic en «Conectar bot.bat» y vuelve a correr esto.")
    if "ANTHROPIC_API_KEY" in faltan:
        print("\nℹ️  Sin clave de Claude el agente igual funciona, pero con reglas simples en vez de")
        print("   inteligencia artificial para leer noticias. Si quieres ponerla, agrégala en")
        print(f"   {ARCHIVO_LLAVES} como  ANTHROPIC_API_KEY=sk-ant-...  y corre esto otra vez.")


def paso_pages(usuario: str, nombre: str) -> str:
    titulo("PASO 4 de 5 · El tablero en internet")
    for metodo in ("POST", "PUT"):
        ok, msg = gh("api", "-X", metodo, f"repos/{usuario}/{nombre}/pages",
                     "-f", "source[branch]=main", "-f", "source[path]=/")
        if ok:
            break
    url = f"https://{usuario}.github.io/{nombre}/web/"
    print(f"✅ Tablero encendido: {url}")
    print("   (tarda 1 a 3 minutos la primera vez)")
    ok, _ = gh("variable", "set", "TABLERO_URL", entrada=url)
    return url


def paso_primera_corrida() -> None:
    titulo("PASO 5 de 5 · Primera corrida")
    ok, msg = gh("workflow", "run", "agente.yml", "-f", "modo=diaria")
    if not ok:
        print(f"Aviso: no pude lanzarla ({msg[:150]}). Puedes hacerlo desde la pestaña Actions.")
        return
    print("✅ El agente está trabajando en los servidores de GitHub ahora mismo.")
    time.sleep(6)
    ok, salida = gh("run", "list", "--workflow", "agente.yml", "--limit", "1")
    if ok and salida:
        print("   " + salida.splitlines()[0])


def main() -> int:
    global GH
    print("\n🌎  GASOLINA GT · Ponerlo en internet")
    print("Cuando termines, todo corre en los servidores de GitHub: gratis, y con tu PC apagada.")

    GH = buscar_gh()
    if not GH:
        print("\n❌ Te falta GitHub CLI. Instálalo con este comando en PowerShell:")
        print("      winget install GitHub.cli")
        print("   Luego cierra y abre la ventana, y corre esto otra vez.")
        return 1

    if not paso_gh():
        return 1
    usuario = paso_repo()
    if not usuario:
        return 1
    ok, nombre = git("remote", "get-url", "origin")
    nombre = nombre.rstrip("/").rstrip(".git").split("/")[-1] if ok else "gasolina-gt"

    paso_secrets()
    url = paso_pages(usuario, nombre)
    paso_primera_corrida()

    titulo("¡Ya está en internet!")
    print(f"  Tablero:  {url}")
    print(f"  Proyecto: https://github.com/{usuario}/{nombre}")
    print(f"  Corridas: https://github.com/{usuario}/{nombre}/actions")
    print("\nDe ahora en adelante, sin tocar nada y con tu PC apagada:")
    print("  · Cada hora (lunes a viernes, 7 a 15): revisa precios, mercado y noticias.")
    print("  · Todos los días a las 7:00 am: publica el resumen en tu canal de Telegram.")
    print("  · El bot contesta los mensajes en la siguiente revisión de cada hora.\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(1)
