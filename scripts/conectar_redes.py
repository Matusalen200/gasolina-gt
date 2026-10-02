"""Asistente para conectar Facebook, Instagram y X. No hay que saber programar.

Doble clic en «Conectar redes.bat», o:
    .venv\\Scripts\\python.exe scripts\\conectar_redes.py

Igual que el de Telegram: te pide una llave, encuentra tu página solo, hace una prueba y guarda
todo en config/.env.local, que es privado y nunca se sube a internet.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import requests  # noqa: E402

from agente.comun import ARCHIVO_LLAVES, cargar_llaves  # noqa: E402
from scripts.conectar import guardar, leer_guardadas, titulo  # noqa: E402

GRAFO = "https://graph.facebook.com/v21.0"


def esperando(texto: str) -> None:
    print(f"   {texto}...", flush=True)


def grafo(ruta: str, **params):
    """Llama a la API de Meta. Devuelve (ok, datos o mensaje de error)."""
    try:
        r = requests.get(f"{GRAFO}/{ruta}", params=params, timeout=40)
        d = r.json()
        if "error" in d:
            return False, d["error"].get("message", "error desconocido")
        return True, d
    except Exception as e:
        return False, f"no pude conectarme a Facebook ({e})"


def explicar() -> None:
    titulo("ANTES DE EMPEZAR · lo que hace falta")
    print("Para que el agente publique solo en Facebook e Instagram necesitas tres cosas:")
    print()
    print("  1. Una PÁGINA de Facebook para Gasolina GT (no tu perfil personal).")
    print("     Se crea en facebook.com/pages/create, es gratis y toma 2 minutos.")
    print()
    print("  2. Tu Instagram en cuenta de EMPRESA o CREADOR, ligada a esa página.")
    print("     En la app de Instagram: Configuración → Tipo de cuenta → Cambiar a profesional.")
    print("     Instagram solo deja publicar automático si es de empresa. Es regla de Meta.")
    print()
    print("  3. Una LLAVE (token) que te da Meta. Eso es lo que te voy a pedir ahorita.")
    print()
    print("Si te falta la página o la cuenta de empresa, cierra esto, créalas y vuelve.")
    print("Si solo quieres Facebook y no Instagram, también sirve: Instagram se salta.", flush=True)


def paso_token() -> str | None:
    titulo("PASO 1 de 4 · La llave de Meta")
    guardadas = leer_guardadas()
    if guardadas.get("FACEBOOK_TOKEN"):
        esperando("Comprobando la llave que ya tenías")
        ok, datos = grafo("me", access_token=guardadas["FACEBOOK_TOKEN"], fields="name")
        if ok:
            print(f"Ya tenías una llave conectada ({datos.get('name')}).")
            if input("¿La dejamos así? (sí / no): ").strip().lower() not in ("no", "n"):
                return guardadas["FACEBOOK_TOKEN"]
        else:
            print(f"La llave que tenías ya no sirve: {datos}")

    print("Ahora hay que sacar la llave. Son cinco clics:")
    print()
    print("  1. Abre:  https://developers.facebook.com/tools/explorer")
    print("     (si te pide registrarte como desarrollador, acepta: es gratis)")
    print("  2. Arriba a la derecha, en «Aplicación de Meta», elige o crea una. Cualquier nombre sirve.")
    print("  3. En «Permisos», agrega estos cuatro, uno por uno:")
    print("        pages_show_list")
    print("        pages_read_engagement")
    print("        pages_manage_posts")
    print("        instagram_content_publish")
    print("  4. Dale al botón azul «Generar token de acceso» y acepta lo que te pregunte.")
    print("  5. Copia el texto largo que aparece en «Token de acceso».")
    print()
    for intento in range(3):
        token = input("Pega aquí la llave y dale Enter: ").strip()
        if not token:
            print("No escribiste nada.")
            continue
        esperando("Comprobando la llave con Meta")
        ok, datos = grafo("me", access_token=token, fields="name")
        if ok:
            print(f"\n✅ Llave buena. Estás como: {datos.get('name')}")
            return token
        print(f"❌ Esa llave no sirve: {datos}")
        if intento < 2:
            print("   Cópiala completa. Ojo: la llave caduca en un par de horas, así que")
            print("   genérala de nuevo si pasó mucho rato.")
    return None


def paso_pagina(token: str):
    titulo("PASO 2 de 4 · Tu página de Facebook")
    esperando("Buscando tus páginas")
    ok, datos = grafo("me/accounts", access_token=token, fields="name,id,access_token")
    paginas = (datos or {}).get("data", []) if ok else []
    if not paginas:
        print("No encontré ninguna página tuya.")
        print("Revisa que diste el permiso pages_show_list y que la página existe.")
        return None, None
    if len(paginas) == 1:
        p = paginas[0]
        print(f"Encontré tu página: «{p['name']}»")
        if input("¿Es esa? (sí / no): ").strip().lower() in ("no", "n"):
            return None, None
    else:
        print("Tienes varias páginas:")
        for i, p in enumerate(paginas, 1):
            print(f"  {i}. {p['name']}")
        try:
            elegida = int(input(f"\n¿Cuál usamos? (1 a {len(paginas)}): ").strip())
            p = paginas[elegida - 1]
        except Exception:
            print("No entendí el número.")
            return None, None
    # El token DE LA PÁGINA es el que sirve para publicar, no el tuyo personal.
    return p["id"], p.get("access_token") or token


def paso_instagram(pagina: str, token: str):
    titulo("PASO 3 de 4 · Tu Instagram")
    esperando("Buscando la cuenta de Instagram ligada a esa página")
    ok, datos = grafo(pagina, access_token=token, fields="instagram_business_account{id,username}")
    cuenta = (datos or {}).get("instagram_business_account") if ok else None
    if cuenta:
        print(f"✅ Encontré Instagram: @{cuenta.get('username', cuenta['id'])}")
        return cuenta["id"]
    print("No hay ningún Instagram de empresa ligado a esa página.")
    print("No es grave: Facebook va a publicar igual. Si quieres Instagram después:")
    print("  · pon tu Instagram en cuenta de empresa o creador")
    print("  · en la página de Facebook → Configuración → Instagram vinculado")
    print("  · y vuelve a correr esto")
    return None


def paso_prueba(pagina: str, token: str, instagram: str | None) -> None:
    titulo("PASO 4 de 4 · Prueba")
    if input("¿Publico algo de prueba en tu página ahora? (sí / no): ").strip().lower() in ("no", "n"):
        print("Está bien, no publico nada. Se publicará mañana a las 7 con el reporte del día.")
        return
    esperando("Publicando")
    try:
        r = requests.post(f"{GRAFO}/{pagina}/feed",
                          data={"message": "⛽ Gasolina GT ya está conectado. Desde mañana publico "
                                           "aquí cada día si conviene llenar el tanque.",
                                "access_token": token}, timeout=60)
        d = r.json()
        if d.get("id"):
            print("✅ Publicado. Revisa tu página de Facebook.")
        else:
            print(f"❌ No pude publicar: {d.get('error', {}).get('message', d)}")
            print("   Casi siempre falta el permiso pages_manage_posts.")
    except Exception as e:
        print(f"❌ No pude publicar: {e}")
    if instagram:
        print("\nInstagram no se prueba ahora porque exige una imagen publicada en internet.")
        print("Se publicará solo con el reporte de mañana, usando la tarjeta del tablero.")


def aviso_caducidad() -> None:
    titulo("IMPORTANTE · que la llave no se venza")
    print("La llave que da Meta dura unas dos horas. Para que sirva siempre hay que extenderla:")
    print()
    print("  1. Abre:  https://developers.facebook.com/tools/debug/accesstoken")
    print("  2. Pega la llave y dale a «Depurar».")
    print("  3. Abajo, botón «Extender token de acceso». Te da una nueva.")
    print("  4. Vuelve a correr este asistente y pega la nueva.")
    print()
    print("La llave extendida de una página no se vence mientras no cambies tu contraseña.")
    print("Si un día deja de publicar, es casi seguro esto: repite los cuatro pasos.", flush=True)


def main() -> int:
    cargar_llaves()
    print("\n📣  GASOLINA GT · Conectar Facebook e Instagram")
    print("Se hace una sola vez. Si la ventana se queda quieta, haz clic y presiona Esc.")
    explicar()
    if input("\n¿Seguimos? (sí / no): ").strip().lower() in ("no", "n"):
        print("\nSin problema. Cuando tengas la página lista, vuelve.")
        return 0

    token = paso_token()
    if not token:
        print("\nSin la llave no puedo seguir. Vuelve a intentar cuando la tengas.")
        return 1
    pagina, token_pagina = paso_pagina(token)
    if not pagina:
        print("\nGuardo la llave, pero sin página no puedo publicar.")
        guardar({"FACEBOOK_TOKEN": token})
        return 1
    instagram = paso_instagram(pagina, token_pagina)

    guardar({"FACEBOOK_PAGE_ID": pagina, "FACEBOOK_TOKEN": token_pagina,
             **({"INSTAGRAM_USER_ID": instagram} if instagram else {})})
    print(f"\n🔒 Llaves guardadas en {ARCHIVO_LLAVES} (privado, no se sube a internet).")
    paso_prueba(pagina, token_pagina, instagram)
    aviso_caducidad()

    titulo("TERMINASTE")
    print("Ya quedó conectado:")
    print(f"  Facebook   página {pagina}")
    print(f"  Instagram  {'cuenta ' + instagram if instagram else 'no conectado (opcional)'}")
    print("\n👉 LO SIGUIENTE: doble clic en «Publicar en internet» para que estas llaves")
    print("   lleguen a GitHub y publique solo, con tu computadora apagada.")
    print("\nPara X (Twitter) mira docs/redes.md: son cuatro llaves que se pegan a mano.\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado. No se guardó nada nuevo.")
        sys.exit(1)
    except EOFError:
        print("\nEsta ventana no me deja escribir. Abre la carpeta en el Explorador y haz")
        print("DOBLE CLIC en «Conectar redes.bat».")
        sys.exit(1)
