"""Pruebas del mapa de gasolineras: leer la lista del MEM y ubicarlas en el país."""
from pathlib import Path

from agente import estaciones, mapa

FIX = Path(__file__).parent / "fixtures"


def texto_de_la_nota() -> str:
    from agente.hoy import _texto_articulo
    return _texto_articulo((FIX / "gasolineras-mas-baratas-2026-09-07.html").read_text(encoding="utf-8", errors="ignore"))


def test_lee_las_quince_gasolineras_del_monitoreo():
    d = estaciones.parsear(texto_de_la_nota())
    assert len(d["autoservicio"]) == 15
    assert len(d["servicio_completo"]) >= 10
    primera = d["autoservicio"][0]
    assert primera["nombre"] == "Texaco Pesa Tivoli" and primera["zona"] == "zona 9"
    assert primera["regular"] == 40.05 and primera["superior"] == 42.05 and primera["diesel"] == 46.35
    assert "google.com/maps" in primera["mapa"]


def test_los_precios_no_arrastran_el_punto_final():
    """El bug real: 'Q46.35.' se convertía en un número imposible y se perdía la estación."""
    d = estaciones.parsear("Shell Prueba, zona 4: superior Q43.09, regular Q41.09 y diésel Q46.39.")
    assert d["autoservicio"][0]["diesel"] == 46.39


def test_limpia_nombres_pegados_a_la_oracion_anterior():
    sucio = "La estación no vende regular y diésel Q46.99. Shell San José, zona 4: superior Q43.09, regular Q41.09 y diésel Q46.39."
    d = estaciones.parsear(sucio)
    assert d["autoservicio"][0]["nombre"] == "Shell San José"


def test_saca_la_fecha_del_monitoreo():
    assert estaciones.fecha_monitoreo(texto_de_la_nota()) == "2026-09-07"
    assert estaciones.fecha_monitoreo("una nota sin fecha") is None


def test_departamento_por_cercania():
    assert mapa.departamento_de(14.6349, -90.5069) == "Guatemala"
    assert mapa.departamento_de(14.8347, -91.5181) == "Quetzaltenango"
    assert mapa.departamento_de(16.9283, -89.8925) == "Petén"
    assert mapa.departamento_de(15.4708, -90.3711) == "Alta Verapaz"


def test_distancia_entre_dos_puntos():
    capital, xela = (14.6349, -90.5069), (14.8347, -91.5181)
    assert 100 < mapa.distancia_km(capital, xela) < 120     # son unos 110 km en línea recta
    assert mapa.distancia_km(capital, capital) == 0


def test_no_aparea_gasolineras_de_departamentos_distintos():
    """Antes, palabras como 'estación' o 'servicio' juntaban estaciones a 200 km de distancia."""
    del_mapa = [
        {"n": "Estación de Servicio El Cerro", "lat": 14.80, "lon": -89.54, "d": "Chiquimula"},
        {"n": "Texaco Pesa Tivoli", "lat": 14.6071, "lon": -90.5208, "d": "Guatemala"},
    ]
    monitoreada = [{"nombre": "Texaco Pesa Tivoli", "zona": "zona 9", "superior": 42.05,
                    "regular": 40.05, "diesel": 46.35, "lat": 14.6071, "lon": -90.5208}]
    pegadas = mapa.marcar_con_precio(del_mapa, monitoreada)
    assert pegadas == 1
    assert del_mapa[1].get("p", {}).get("r") == 40.05     # la correcta sí recibió el precio
    assert "p" not in del_mapa[0]                          # la de Chiquimula no


def test_una_estacion_que_no_esta_en_el_mapa_se_agrega_igual():
    del_mapa = [{"n": "Otra cosa", "lat": 14.60, "lon": -90.50, "d": "Guatemala"}]
    monitoreada = [{"nombre": "Gasolinera Nueva Nunca Vista", "zona": "zona 9", "superior": 43.0,
                    "regular": 41.0, "diesel": 47.0, "lat": 14.61, "lon": -90.52,
                    "ubicacion_exacta": False}]
    assert mapa.marcar_con_precio(del_mapa, monitoreada) == 1
    agregada = del_mapa[-1]
    assert agregada["n"] == "Gasolinera Nueva Nunca Vista" and agregada["aprox"] is True
