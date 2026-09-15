"""Asistente para conectar tu bot y tu canal de Telegram con el agente. No hay que saber programar.

Doble clic en «Conectar bot.bat», o:
    .venv\\Scripts\\python.exe scripts\\conectar.py

Qué hace, paso a paso:
  1. Te pide el token que te dio @BotFather y comprueba que sea válido.
  2. Encuentra tu canal solo (o se lo dices tú) y manda un mensaje de prueba.
  3. Guarda las llaves en config/.env.local, que es privado y nunca se sube a internet.
  4. Deja listo el menú de comandos del bot.
  5. Te ofrece programarlo para que publique solo todos los días.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import requests  # noqa: E402

from agente.comun import ARCHIVO_LLAVES, cargar_llaves  # noqa: E402

API = "https://api.telegram.org/bot{token}/{metodo}"
LLAVES_CONOCIDAS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID", "ANTHROPIC_API_KEY", "TABLERO_URL")


def titulo(texto: str) -> None:
    print("\n" + "─" * 60)
    print(texto)
    print("─" * 60)


def api(token: str, metodo: str, **params):
    """Llama a Telegram. Devuelve (ok, resultado_o_mensaje_de_error)."""
    try:
        r = requests.post(API.format(token=token, metodo=metodo), json=params, timeout=30)
        d = r.json()
        return (True, d["result"]) if d.get("ok") else (False, d.get("description", "error desconocido"))
    except Exception as e:
        return False, f"no pude conectarme a Telegram ({e})"


# ----------------------------------------------------------------------------- llaves guardadas
def leer_guardadas() -> dict:
    valores = {}
    if ARCHIVO_LLAVES.exists():
        for linea in ARCHIVO_LLAVES.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip()
    return valores


def guardar(nuevas: dict) -> None:
    valores = leer_guardadas()
    valores.update({k: v for k, v in nuevas.items() if v})
    lineas = ["# Llaves privadas de Gasolina GT. NO compartas este archivo ni lo subas a internet.",
              "# Está en .gitignore, así que git nunca lo sube.", ""]
    lineas += [f"{k}={valores[k]}" for k in LLAVES_CONOCIDAS if valores.get(k)]
    lineas += [f"{k}={v}" for k, v in valores.items() if k not in LLAVES_CONOCIDAS]
    ARCHIVO_LLAVES.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_LLAVES.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    try:  # que solo tu usuario de Windows pueda leerlo
        import subprocess
        subprocess.run(["icacls", str(ARCHIVO_LLAVES), "/inheritance:r", "/grant:r", f"{__import__('os').getlogin()}:R,W"],
                       capture_output=True, timeout=20)
    except Exception:
        pass


# ----------------------------------------------------------------------------- pasos
def paso_token() -> str | None:
    titulo("PASO 1 de 4 · El token de tu bot")
    guardadas = leer_guardadas()
    if guardadas.get("TELEGRAM_BOT_TOKEN"):
        ok, info = api(guardadas["TELEGRAM_BOT_TOKEN"], "getMe")
        if ok:
            print(f"Ya tenías conectado el bot @{info.get('username')}.")
            if input("¿Lo dejamos así? (sí / no): ").strip().lower() not in ("no", "n"):
                return guardadas["TELEGRAM_BOT_TOKEN"]

    print("Abre Telegram, busca @BotFather y copia el token que te dio.")
    print("Se parece a esto:  123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    for intento in range(3):
        token = input("\nPega aquí el token y dale Enter: ").strip()
        if not token:
            print("No escribiste nada.")
            continue
        ok, info = api(token, "getMe")
        if ok:
            print(f"\n✅ Conectado con tu bot: {info.get('first_name')} (@{info.get('username')})")
            return token
        print(f"❌ Ese token no sirve: {info}")
        if intento < 2:
            print("   Copialo completo, sin espacios. En BotFather podés pedir /mybots → API Token.")
    return None


def _detectar_canal(token: str):
    """Busca el canal en los mensajes recientes del bot (necesita que ya sea administrador)."""
    ok, updates = api(token, "getUpdates", timeout=0, allowed_updates=["channel_post", "message"])
    if not ok:
        return None
    for u in reversed(updates or []):
        chat = ((u.get("channel_post") or u.get("message") or {}).get("chat") or {})
        if chat.get("type") in ("channel", "supergroup") and chat.get("id"):
            return chat
    return None


def paso_canal(token: str) -> str | None:
    titulo("PASO 2 de 4 · Tu canal")
    print("Para que el bot pueda publicar, tiene que ser ADMINISTRADOR de tu canal:")
    print("  Canal «Gasolina GT» → Administradores → Agregar administrador → busca tu bot")
    print("  → dale permiso de «Publicar mensajes» → Guardar.")
    input("\nCuando ya lo hiciste, dale Enter para seguir... ")

    chat = _detectar_canal(token)
    if chat:
        nombre = chat.get("title") or chat.get("username")
        print(f"\nEncontré este canal: «{nombre}»")
        if input("¿Es ese? (sí / no): ").strip().lower() not in ("no", "n"):
            return str(chat["id"])

    print("\nNo lo encontré solo. Dime cuál es:")
    print("  · Si tu canal es público, escribe su nombre con arroba, por ejemplo  @gasolinagt")
    print("  · Si es privado, publica cualquier mensaje en el canal y escribe  buscar")
    for _ in range(3):
        resp = input("\nCanal: ").strip()
        if resp.lower() == "buscar":
            chat = _detectar_canal(token)
            if chat:
                print(f"Encontré: «{chat.get('title')}»")
                return str(chat["id"])
            print("Todavía no lo veo. Publica un mensaje en el canal y escribe «buscar» otra vez.")
            continue
        if not resp:
            continue
        canal = resp if resp.startswith(("@", "-")) else "@" + resp
        ok, info = api(token, "getChat", chat_id=canal)
        if ok:
            print(f"✅ Canal encontrado: «{info.get('title')}»")
            return canal
        print(f"❌ No pude entrar a ese canal: {info}")
    return None


def paso_prueba(token: str, canal: str) -> bool:
    titulo("PASO 3 de 4 · Mensaje de prueba")
    texto = ("⛽ ¡Listo! Gasolina GT ya está conectado.\n"
             "Desde ahora publico aquí cada mañana a las 7 si conviene llenar el tanque.")
    ok, info = api(token, "sendMessage", chat_id=canal, text=texto, disable_web_page_preview=True)
    if ok:
        print("✅ Mandé un mensaje de prueba. Revisa tu canal: ya debería estar ahí.")
        return True
    print(f"❌ No pude publicar: {info}")
    print("   Casi siempre es porque el bot todavía no es administrador del canal,")
    print("   o le falta el permiso de «Publicar mensajes».")
    return False


def paso_menu(token: str) -> None:
    from bot import plantillas as P
    ok, _ = api(token, "setMyCommands", commands=[{"command": c, "description": d} for c, d in P.COMANDOS_MENU])
    print("✅ Menú de comandos listo (el botón «/» del chat)." if ok else "Aviso: no pude registrar el menú de comandos.")


def paso_automatizar() -> None:
    titulo("PASO 4 de 4 · Que corra solo")
    print("Puedo programar tu PC para que el agente trabaje solo:")
    print("  · Cada hora, de lunes a viernes de 7 a 15: revisa precios y noticias.")
    print("  · Todos los días a las 7:00 de la mañana: publica el resumen en tu canal.")
    if input("\n¿Lo programo ahora? (sí / no): ").strip().lower() in ("no", "n"):
        print("\nSin problema. Cuando quieras, doble clic en «Automatizar.bat».")
        return
    import subprocess
    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(RAIZ / "scripts" / "automatizar.ps1")],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())


def main() -> int:
    cargar_llaves()
    print("\n⛽  GASOLINA GT · Conectar tu bot de Telegram")
    print("Esto toma 2 minutos y solo se hace una vez.")

    token = paso_token()
    if not token:
        print("\nNo pudimos conectar el bot. Vuelve a intentar cuando tengas el token a mano.")
        return 1

    canal = paso_canal(token)
    if not canal:
        print("\nGuardé el bot, pero sin canal no puedo publicar. Corre esto otra vez cuando lo tengas.")
        guardar({"TELEGRAM_BOT_TOKEN": token})
        return 1

    guardar({"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHANNEL_ID": canal})
    print(f"\n🔒 Llaves guardadas en {ARCHIVO_LLAVES} (privado, no se sube a internet).")
    paso_prueba(token, canal)
    paso_menu(token)
    paso_automatizar()

    titulo("¡Todo listo!")
    print("Ahora puedes:")
    print("  · Escribirle a tu bot en Telegram: /hoy, /precio Quetzaltenango, /tanque 10")
    print("  · Doble clic en «Gasolina GT.bat» para ver el tablero cuando quieras.")
    print("  · Olvidarte: él solo publica cada mañana en tu canal.\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado. No se guardó nada nuevo.")
        sys.exit(1)
