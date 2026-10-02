from agente import hoy


def test_extrae_precio_de_ciudad_primero():
    t = ("en la ciudad de Guatemala el diésel se cotiza esta semana a 35.93 quetzales el galón, la gasolina regular a 38.33 quetzales, "
         "mientras que la superior se encuentra a 39.33 quetzales. En Flores, Petén, el diésel es de 37.08 quetzales, la regular 39.48 y la superior 40.48.")
    assert hoy.extraer_precios(t) == {"superior": 39.33, "regular": 38.33, "diesel": 35.93}


def test_extrae_con_simbolo_q_y_titular():
    assert hoy.extraer_precios("Gasolinas suben otro Q1 por galón y la regular llega a Q41.09 en el área metropolitana") == {"regular": 41.09}
    t = "Texaco Pesa Tivoli, zona 9: superior Q42.05, regular Q40.05 y diésel Q46.35."
    assert hoy.extraer_precios(t) == {"superior": 42.05, "regular": 40.05, "diesel": 46.35}


def test_ignora_numeros_fuera_de_rango_y_sin_producto():
    assert hoy.extraer_precios("El subsidio costará Q1,200 millones y durará 90 días. La gasolina bajó.") == {}


def test_clasifica_tipo():
    assert hoy.clasificar_tipo("El Congreso aprobó un precio tope de Q41 para la superior mediante decreto") == "tope"
    assert hoy.clasificar_tipo("Tras el decreto del tope, hoy los precios promedio son...", "Así están los precios este viernes") == "promedio"
    assert hoy.clasificar_tipo("Según el monitoreo del MEM, el precio promedio de la regular es Q40.93") == "promedio"
    assert hoy.clasificar_tipo("La gasolinera Texaco de zona 9 vende la regular a Q40.05") == "estacion"


def test_consolidar_prefiere_promedio_y_calcula_cambio():
    serie = [
        {"t": "2026-09-09T10:00", "fecha_dato": "2026-09-09", "tipo": "estacion", "superior": 42.0, "regular": 40.0, "diesel": 46.0, "fuente": "A", "url": "a", "titulo": "a"},
        {"t": "2026-09-10T08:00", "fecha_dato": "2026-09-10", "tipo": "estacion", "superior": 42.5, "regular": 40.5, "diesel": None, "fuente": "B", "url": "b", "titulo": "b"},
        {"t": "2026-09-10T09:00", "fecha_dato": "2026-09-10", "tipo": "promedio", "superior": 43.06, "regular": 40.93, "diesel": 46.37, "fuente": "C", "url": "c", "titulo": "c"},
        {"t": "2026-09-09T12:00", "fecha_dato": "2026-09-09", "tipo": "tope", "superior": 41.0, "regular": 39.0, "diesel": 39.0, "fuente": "D", "url": "d", "titulo": "Decreto"},
    ]
    c = hoy.consolidar(serie)
    assert c["ultimo"]["regular"]["valor"] == 40.93 and c["ultimo"]["regular"]["tipo"] == "promedio"
    assert c["cambio_dia"]["regular"]["q"] == 0.93
    assert c["tope"]["superior"] == 41.0
    assert [d["fecha"] for d in c["diario"]] == ["2026-09-09", "2026-09-10"]


def test_un_cambio_grande_y_real_no_se_rechaza():
    """El Decreto 22-2026 quitó impuestos y el galón bajó como Q8 de un día para otro.
    Un filtro de banda fija lo habría tomado por error y habríamos publicado precios viejos
    durante semanas. Por eso lo único que se rechaza es lo IMPOSIBLE, no lo sorprendente."""
    nuevo = {"superior": 36.18, "regular": 34.85, "diesel": 41.72, "tipo": "promedio"}
    viejo = {"superior": 44.66, "regular": 42.58, "diesel": 49.36}
    assert hoy._coherente(nuevo, viejo) is True          # se acepta
    assert hoy._fuera_de_banda(nuevo, viejo) is True     # pero se marca para que otra fuente confirme


def test_se_rechaza_lo_que_es_imposible():
    ref = {"superior": 36.18, "regular": 34.85, "diesel": 41.72}
    assert hoy._coherente({"superior": 45.29, "regular": 45.29}, ref) is False   # iguales
    assert hoy._coherente({"superior": 34.96, "regular": 42.94}, ref) is False   # normal sobre súper
    assert hoy._coherente({"superior": 40.00, "regular": 34.85}, ref) is False   # brecha de Q5
    assert hoy._coherente({"superior": 36.18, "regular": 34.85}, ref) is True    # brecha normal


def test_la_referencia_usa_el_dato_mas_reciente(monkeypatch, tmp_path):
    """Si el informe oficial tiene semanas, la referencia es la serie diaria; si no, nunca
    podríamos salir de un precio viejo."""
    archivos = {
        "precios.json": {"fecha_monitoreo": "2026-09-16",
                         "autoservicio": {"superior": 44.66, "regular": 42.58, "diesel": 49.36}},
        "precio_hoy.json": {"ultimo": {"regular": {"valor": 34.89, "fecha": "2026-10-01"}}},
    }
    monkeypatch.setattr(hoy, "leer_json", lambda ruta, defecto=None: archivos.get(getattr(ruta, "name", ""), defecto))
    assert hoy._referencia() == {"regular": 34.89}
