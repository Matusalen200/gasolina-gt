from datetime import date

from agente import reporte
from bot import plantillas as P
from bot import telegram
from reportes.mensual import ahorro_semana

SENAL = {"emoji": "🔴", "veredicto": "Llena HOY", "cambio_estimado_texto": "El martes sube como Q0.45 el galón.", "razon": "Petróleo subió 3% esta semana.",
         "puntaje": 42, "proximo_martes": "2026-09-15", "detalle": {"rbob_cambio_7d_pct": 3.1, "usdgtq_cambio_7d_pct": 0.2, "noticias_alza_7d": 3, "noticias_baja_7d": 1}}
PRECIOS = {"fecha_monitoreo": "2026-09-14", "autoservicio": {"superior": 32.09, "regular": 31.09, "diesel": 27.29}, "cambio_semanal": {"regular": 0.40}}
DEPTOS = {"mas_barato": {"departamento": "Guatemala", "cabecera": "Ciudad de Guatemala", "regular": 30.99},
          "mas_caro": {"departamento": "Petén", "cabecera": "Flores", "regular": 32.40}}
NOTICIAS = {"noticias": [{"titulo": "Petróleo sube por tensión en Medio Oriente", "url": "https://x", "etiqueta": "ALZA", "fuente": "Reuters", "razon": "r"}]}


def test_mensaje_corto_cinco_lineas_y_estilo():
    m = reporte.mensaje_corto(SENAL, PRECIOS, DEPTOS, NOTICIAS, hoy={})
    lineas = m.splitlines()
    assert len(lineas) <= 5
    assert lineas[0] == "🔴 Llena HOY. El martes sube como Q0.45 el galón."
    assert lineas[1] == "Hoy el galón cuesta: Súper Q32.09 · Regular Q31.09 · Diésel Q27.29"
    assert "RBOB" not in m and "WTI" not in m
    assert "Guatemala" in lineas[3]


def test_todas_las_plantillas_tienen_maximo_cinco_lineas():
    for nombre in ("MENSAJE_DIARIO", "MENSAJE_SENAL", "MENSAJE_PRECIO", "MENSAJE_AYUDA", "MENSAJE_PLUS"):
        assert len(getattr(P, nombre).splitlines()) <= 5, nombre


def test_direccion_real_y_acierto():
    assert reporte.direccion_real(0.40) == "alza"
    assert reporte.direccion_real(-0.30) == "baja"
    assert reporte.direccion_real(0.05) == "estable"
    assert reporte.direccion_real(None) is None


def test_evaluar_martes_con_dato_fresco(tmp_path, monkeypatch):
    monkeypatch.setattr(reporte, "RUTA_ACIERTOS", tmp_path / "aciertos.json")
    hist = [{"fecha": "2026-09-14", "tendencia": "alza", "cambio_estimado_q": 0.45}]
    fila = reporte.evaluar_martes(date(2026, 9, 15), PRECIOS, hist)
    assert fila["real"] == "alza" and fila["acierto"] is True
    assert "✅" in reporte.texto_martes(fila)


def test_evaluar_martes_sin_dato_mem(tmp_path, monkeypatch):
    monkeypatch.setattr(reporte, "RUTA_ACIERTOS", tmp_path / "aciertos.json")
    viejo = dict(PRECIOS, fecha_monitoreo="2026-01-19")
    fila = reporte.evaluar_martes(date(2026, 9, 15), viejo, [{"fecha": "2026-09-14", "tendencia": "alza"}])
    assert fila["real"] is None and fila["acierto"] is None
    assert "⏳" in reporte.texto_martes(fila)


def test_bot_responde_comandos():
    assert telegram.responder("") is None
    assert telegram.responder("/start").startswith("⛽")
    assert "gratis" in telegram.responder("/plus").lower()
    assert telegram.responder("/comando-que-no-existe") == P.MENSAJE_NO_ENTIENDO
    r = telegram.responder("/precio peten")
    assert r is not None and ("Petén" in r or "No conozco" in r)


def test_precios_vigentes_gana_el_mas_reciente():
    hoy_nuevo = {"ultimo": {p: {"valor": v, "fecha": "2026-09-15", "tipo": "promedio", "fuente": "Medios"}
                            for p, v in (("superior", 44.59), ("regular", 42.59), ("diesel", 49.39))}}
    auto, fecha, fuente = reporte.precios_vigentes(PRECIOS, hoy_nuevo)   # medios 15 > oficial 14
    assert auto["regular"] == 42.59 and fecha == "2026-09-15" and fuente == "Medios"
    hoy_viejo = {"ultimo": {"regular": {"valor": 39.0, "fecha": "2026-09-01", "tipo": "promedio", "fuente": "Medios"}}}
    auto, fecha, _ = reporte.precios_vigentes(PRECIOS, hoy_viejo)        # oficial 14 > medios 1
    assert auto["regular"] == 31.09 and fecha == "2026-09-14"
    hoy_estacion = {"ultimo": {"regular": {"valor": 39.0, "fecha": "2026-09-20", "tipo": "estacion", "fuente": "X"}}}
    auto, _, _ = reporte.precios_vigentes(PRECIOS, hoy_estacion)          # una gasolinera suelta no manda
    assert auto["regular"] == 31.09


def test_ahorro_por_semana():
    assert ahorro_semana("alza", 0.40) == 0.40
    assert ahorro_semana("baja", -0.30) == 0.30
    assert ahorro_semana("alza", -0.30) == -0.30
    assert ahorro_semana("estable", 0.40) == 0.0
    assert ahorro_semana(None, 0.40) == 0.0


def test_cargar_llaves_desde_archivo(tmp_path, monkeypatch):
    """La 'conexión' del bot: el agente toma sus llaves de config/.env.local sin configurar nada."""
    from agente import comun
    archivo = tmp_path / ".env.local"
    archivo.write_text('# comentario\nTELEGRAM_BOT_TOKEN=123:ABC\nTELEGRAM_CHANNEL_ID="@canal"\n\nMALA\n', encoding="utf-8")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)
    puestas = comun.cargar_llaves(archivo)
    assert puestas == {"TELEGRAM_BOT_TOKEN": "123:ABC", "TELEGRAM_CHANNEL_ID": "@canal"}
    import os
    assert os.environ["TELEGRAM_CHANNEL_ID"] == "@canal"   # sin comillas


def test_cargar_llaves_no_pisa_lo_que_ya_existe(tmp_path, monkeypatch):
    from agente import comun
    archivo = tmp_path / ".env.local"
    archivo.write_text("TELEGRAM_BOT_TOKEN=del-archivo\n", encoding="utf-8")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "de-github-actions")
    assert comun.cargar_llaves(archivo) == {}
    import os
    assert os.environ["TELEGRAM_BOT_TOKEN"] == "de-github-actions"


def test_cargar_llaves_sin_archivo_no_rompe(tmp_path):
    from agente import comun
    assert comun.cargar_llaves(tmp_path / "no-existe") == {}
