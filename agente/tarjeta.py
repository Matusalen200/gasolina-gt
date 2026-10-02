"""La tarjeta para redes sociales: una imagen cuadrada con el precio grande, como las de los medios.

Está pensada para que alguien que pasa por su muro entienda en dos segundos si la gasolina sube o
baja, y al final le diga dónde seguir recibiendo el dato. Es distinta de la gráfica de Telegram:
esa explica, esta llama la atención.

Guarda data/tarjeta_redes.png (1080x1080, que es lo que piden Instagram y Facebook).
"""
from __future__ import annotations

from datetime import date

from agente.comun import DATA, ahora_gt, leer_json, log

RUTA = DATA / "tarjeta_redes.png"
LADO = 1080
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

FONDO = (17, 20, 25)
BLANCO = (245, 247, 250)
GRIS = (150, 160, 175)
ALZA = (226, 74, 74)
BAJA = (52, 180, 102)
ESTABLE = (235, 178, 20)
LINEA = (42, 48, 58)

TITULOS = {"alza": "LLENA HOY", "baja": "ESPERA, VA A BAJAR", "estable": "SIN APURO"}
PRODUCTOS = [("superior", "SÚPER"), ("regular", "NORMAL"), ("diesel", "DIÉSEL")]


def _fuentes():
    """Tipografías que existen igual en Windows y en los servidores de GitHub."""
    from matplotlib import font_manager
    from PIL import ImageFont

    def buscar(peso):
        try:
            ruta = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight=peso))
            return ruta
        except Exception:
            return None

    normal, negrita = buscar("normal"), buscar("bold")
    def f(tam, gorda=False):
        ruta = negrita if gorda else normal
        try:
            return ImageFont.truetype(ruta, tam)
        except Exception:
            return ImageFont.load_default()
    return f


def _fecha_larga(iso: str | None) -> str:
    try:
        d = date.fromisoformat(str(iso))
        return f"{d.day} de {MESES[d.month - 1]}"
    except Exception:
        return ""


def _centrar(dibujo, texto, fuente, y, color, ancho=LADO):
    izq, arriba, der, abajo = dibujo.textbbox((0, 0), texto, font=fuente)
    dibujo.text(((ancho - (der - izq)) / 2 - izq, y), texto, font=fuente, fill=color)
    return abajo - arriba


def generar(ruta=None):
    """Crea la tarjeta. Devuelve la ruta, o None si falta algún dato o la librería."""
    ruta = ruta or RUTA
    senal = leer_json(DATA / "senal.json", {}) or {}
    precios = leer_json(DATA / "precios.json", {}) or {}
    if not senal:
        log("Tarjeta: todavía no hay señal del día", "WARN")
        return None
    try:
        from PIL import Image, ImageDraw
    except Exception as e:
        log(f"Tarjeta: falta Pillow ({e})", "WARN")
        return None

    from agente.reporte import precios_vigentes
    auto, fecha_dato, _ = precios_vigentes(precios)
    if not auto.get("regular"):
        log("Tarjeta: todavía no hay precios", "WARN")
        return None

    tendencia = senal.get("tendencia", "estable")
    color = {"alza": ALZA, "baja": BAJA, "estable": ESTABLE}[tendencia]
    cambio = (precios or {}).get("cambio_semanal", {}) or {}

    f = _fuentes()
    img = Image.new("RGB", (LADO, LADO), FONDO)
    d = ImageDraw.Draw(img)

    # Barra de marca
    d.rectangle([0, 0, LADO, 14], fill=color)
    _centrar(d, "GASOLINA GT", f(40, True), 52, BLANCO)
    _centrar(d, _fecha_larga(fecha_dato or ahora_gt().date().isoformat()).upper(), f(26), 104, GRIS)

    # El veredicto, que es lo que debe entenderse de un vistazo
    d.rectangle([90, 165, LADO - 90, 300], fill=color)
    _centrar(d, TITULOS.get(tendencia, ""), f(62, True), 200, (255, 255, 255))

    # Los tres precios
    y = 360
    ancho = (LADO - 160) // 3
    for i, (clave, nombre) in enumerate(PRODUCTOS):
        valor = auto.get(clave)
        if valor is None:
            continue
        x = 80 + i * ancho
        izq, arr, der, ab = d.textbbox((0, 0), nombre, font=f(26))
        d.text((x + (ancho - (der - izq)) / 2 - izq, y), nombre, font=f(26), fill=GRIS)
        texto = f"Q{valor:.2f}"
        izq, arr, der, ab = d.textbbox((0, 0), texto, font=f(64, True))
        d.text((x + (ancho - (der - izq)) / 2 - izq, y + 44), texto, font=f(64, True), fill=BLANCO)
        dif = cambio.get(clave)
        if dif is not None:
            flecha = "▲" if dif > 0 else "▼" if dif < 0 else "="
            tono = ALZA if dif > 0 else BAJA if dif < 0 else GRIS
            sub = f"{flecha} Q{abs(dif):.2f}"
            izq, arr, der, ab = d.textbbox((0, 0), sub, font=f(28, True))
            d.text((x + (ancho - (der - izq)) / 2 - izq, y + 126), sub, font=f(28, True), fill=tono)

    d.line([90, 560, LADO - 90, 560], fill=LINEA, width=2)

    # El porqué, en palabras simples
    razon = senal.get("razon", "")
    palabras, linea, lineas = razon.split(), "", []
    for p in palabras:
        prueba = (linea + " " + p).strip()
        izq, arr, der, ab = d.textbbox((0, 0), prueba, font=f(32))
        if der - izq > LADO - 200 and linea:
            lineas.append(linea)
            linea = p
        else:
            linea = prueba
    if linea:
        lineas.append(linea)
    y = 610
    for l in lineas[:3]:
        _centrar(d, l, f(32), y, BLANCO)
        y += 46

    # Lo que esperamos para el martes
    if senal.get("cambio_estimado_texto"):
        _centrar(d, senal["cambio_estimado_texto"], f(30, True), y + 18, color)

    # Pie: de dónde salen los datos y dónde seguirnos
    d.line([90, LADO - 190, LADO - 90, LADO - 190], fill=LINEA, width=2)
    _centrar(d, "Precios de referencia del Ministerio de Energía y Minas", f(24), LADO - 165, GRIS)
    import os
    canal = os.environ.get("CANAL_URL", "").strip()
    llamado = f"Recíbelo cada mañana: {canal}" if canal else "Recíbelo cada mañana en nuestro canal"
    _centrar(d, llamado, f(30, True), LADO - 118, BLANCO)
    d.rectangle([0, LADO - 14, LADO, LADO], fill=color)

    ruta.parent.mkdir(parents=True, exist_ok=True)
    img.save(ruta, "PNG")
    log(f"Tarjeta para redes lista: {ruta.name} ({tendencia})")
    return ruta


if __name__ == "__main__":  # pragma: no cover
    print(generar())
