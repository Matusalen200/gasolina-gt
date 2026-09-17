"""Pruebas de todos los comandos del bot, con datos de mentira (sin red, sin Claude)."""
import pytest

from bot import plantillas as P
from bot import telegram

DEPTOS = {
    "estimado": True, "fecha": "2026-09-15", "tabla_oficial_fecha": "2026-01-19",
    "mas_barato": {"cabecera": "Ciudad de Guatemala", "departamento": "Guatemala", "superior": 44.59, "regular": 42.59, "diesel": 49.39},
    "mas_caro": {"cabecera": "Flores", "departamento": "Petén", "superior": 45.88, "regular": 43.88, "diesel": 50.68},
    "departamentos": [
        {"cabecera": "Ciudad de Guatemala", "departamento": "Guatemala", "superior": 44.59, "regular": 42.59, "diesel": 49.39},
        {"cabecera": "Quetzaltenango", "departamento": "Quetzaltenango", "superior": 44.93, "regular": 42.93, "diesel": 49.73},
        {"cabecera": "Flores", "departamento": "Petén", "superior": 45.88, "regular": 43.88, "diesel": 50.68},
    ],
}
SENAL = {"emoji": "🔴", "veredicto": "Llena HOY", "cambio_estimado_texto": "El martes sube como Q0.45 el galón.",
         "razon": "Porque el petróleo subió.", "proximo_martes": "2026-09-22", "tendencia": "alza", "puntaje": 40}
NOTICIAS = {"noticias": [
    {"titulo": "Oil jumps", "titulo_es": "El petróleo sube fuerte", "etiqueta": "ALZA", "url": "u", "fuente": "F", "idioma": "en"},
    {"titulo": "Baja el crudo", "etiqueta": "BAJA", "url": "u2", "fuente": "F2", "idioma": "es"},
    {"titulo": "Nota cualquiera", "etiqueta": "NEUTRAL", "url": "u3", "fuente": "F3", "idioma": "es"},
]}
PROYECCION = {"estado": "calibrando", "semanas": [{"fecha": "2026-09-22", "regular": 42.9}, {"fecha": "2026-09-29", "regular": 43.1}]}
MERCADO = {"ultimo": {"RB=F": {"precio": 3.13, "cambio_7d_pct": -2.7}, "CL=F": {"precio": 99.99, "cambio_7d_pct": 9.3},
                      "GTQ=X": {"precio": 7.628, "cambio_7d_pct": 0.03}}}
PRECIO_HOY = {"tope": {"superior": 41.0, "regular": 39.0, "diesel": 39.0, "fecha": "2026-09-09"}}
HISTORIAL = [{"fecha": "2026-09-07", "superior": 43.06, "regular": 40.93, "diesel": 46.37},
             {"fecha": "2026-09-15", "superior": 44.59, "regular": 42.59, "diesel": 49.39}]
ACIERTOS = {"estado": "ok", "total": 5, "aciertos": 4, "porcentaje": 80}

POR_ARCHIVO = {
    "departamentos_hoy.json": DEPTOS, "departamentos.json": DEPTOS, "senal.json": SENAL,
    "noticias.json": NOTICIAS, "proyeccion.json": PROYECCION, "mercado_horario.json": MERCADO,
    "precio_hoy.json": PRECIO_HOY, "precios_historial.json": HISTORIAL, "aciertos.json": ACIERTOS,
    "telegram_usuarios.json": {},
}


@pytest.fixture(autouse=True)
def datos_falsos(monkeypatch, tmp_path):
    def leer(ruta, defecto=None):
        return POR_ARCHIVO.get(getattr(ruta, "name", str(ruta)), defecto)
    monkeypatch.setattr(telegram, "leer_json", leer)
    monkeypatch.setattr(telegram, "RUTA_USUARIOS", tmp_path / "usuarios.json")
    monkeypatch.setattr(telegram, "cliente_claude", lambda: None)   # sin Claude en las pruebas


def test_senal_y_ayuda():
    assert telegram.responder("/senal").startswith("🔴 Llena HOY")
    assert "2026-09-22" not in telegram.responder("/senal")       # fecha bonita, no ISO
    assert "22 de septiembre" in telegram.responder("/senal")
    assert telegram.responder("/ayuda").startswith("⛽")


def test_precio_por_departamento_y_apodo():
    r = telegram.responder("/precio Petén")
    assert "Petén" in r and "Q43.88" in r and "Pagas Q1.29 más" in r
    assert "Quetzaltenango" in telegram.responder("/precio xela")
    assert "más barato del país" in telegram.responder("/precio guatemala")
    assert "No conozco ese lugar" in telegram.responder("/precio Narnia")


def test_baratos_y_caros_por_producto():
    baratos = telegram.responder("/baratos")
    assert baratos.startswith("💚") and "1. Guatemala — Q42.59" in baratos
    caros = telegram.responder("/caros diesel")
    assert caros.startswith("💸") and "1. Petén — Q50.68" in caros
    assert "súper" in telegram.responder("/caros super")


def test_tanque_calcula_y_compara():
    r = telegram.responder("/tanque 10 Petén")
    assert "10 galones de normal en Petén" in r and "Q438.80" in r
    assert "ahorras Q12.90" in r          # 10 gal x (43.88 - 42.59)
    assert "Ya estás en el lugar más barato" in telegram.responder("/tanque 5 Guatemala")
    assert "súper" in telegram.responder("/tanque 12 super Quetzaltenango")
    assert "10 galones" in telegram.responder("/tanque")   # sin número usa 10


def test_noticias_prefiere_espanol_y_las_que_mueven():
    r = telegram.responder("/noticias")
    assert "El petróleo sube fuerte" in r and "🔴" in r
    assert "Oil jumps" not in r           # usa el titular traducido


def test_futuro_aciertos_mercado_tope_historial():
    assert "22 de septiembre: Q42.90" in telegram.responder("/futuro")
    assert "4 de 5 semanas (80 %)" in telegram.responder("/aciertos")
    m = telegram.responder("/mercado")
    assert "bajó 2.7 %" in m and "7.628 quetzales por dólar" in m
    assert "Q39.00" in telegram.responder("/tope")
    h = telegram.responder("/historial diesel")
    assert "7 de septiembre: Q46.37" in h and "diésel" in h


def test_midepto_recuerda_al_usuario():
    assert "Quetzaltenango" in telegram.responder("/midepto xela", uid=7)
    assert "Quetzaltenango" in telegram.responder("/precio", uid=7)      # ya no hace falta repetirlo
    assert telegram.responder("/precio", uid=99) == P.MENSAJE_SIN_DEPTO  # otro usuario, sin guardar


def test_texto_normal_sin_comando():
    assert "Petén" in telegram.responder("Petén")
    assert telegram.responder("¿va a subir?").startswith("🔴")
    assert "💚" in telegram.responder("dónde está más barata")
    assert "galones de normal" in telegram.responder("cuánto cuesta llenar 15 galones")
    assert telegram.responder("cualquier cosa rara") == P.MENSAJE_NO_ENTIENDO  # sin Claude, cae aquí


def test_menu_de_comandos_coincide_con_el_router():
    for comando, _ in P.COMANDOS_MENU:
        assert telegram.responder("/" + comando) != P.MENSAJE_NO_ENTIENDO, comando
