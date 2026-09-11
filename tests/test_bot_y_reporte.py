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
    m = reporte.mensaje_corto(SENAL, PRECIOS, DEPTOS, NOTICIAS)
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
    assert telegram.responder("hola") is None
    assert telegram.responder("/start").startswith("⛽")
    assert "gratis" in telegram.responder("/plus").lower()
    r = telegram.responder("/precio peten")
    assert r is not None and ("Petén" in r or "No encontré" in r)


def test_ahorro_por_semana():
    assert ahorro_semana("alza", 0.40) == 0.40
    assert ahorro_semana("baja", -0.30) == 0.30
    assert ahorro_semana("alza", -0.30) == -0.30
    assert ahorro_semana("estable", 0.40) == 0.0
    assert ahorro_semana(None, 0.40) == 0.0
