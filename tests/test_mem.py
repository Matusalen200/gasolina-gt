from datetime import date
from pathlib import Path

from agente import mem

FIX = Path(__file__).parent / "fixtures"


def test_parsear_ejecutivo_metropolitano():
    info = mem.parsear_ejecutivo(FIX / "informe-ejecutivo-area-metropolitana-2026-01-19.pdf")
    assert info["fecha_monitoreo"] == "2026-01-19"
    assert info["autoservicio"]["superior"] == 27.49
    assert info["autoservicio"]["regular"] == 26.53
    assert info["autoservicio"]["diesel"] == 25.10
    assert info["autoservicio"]["_anterior"]["superior"] == 27.29
    assert info["servicio_completo"]["kerosene"] == 37.00
    assert info["tipo_cambio"] == 7.6621
    assert len(info["historial"]) == 7
    assert info["historial"][0] == {"fecha": "2025-12-08", "superior": 28.41, "regular": 27.41, "diesel": 26.38}


def test_parsear_departamental():
    info = mem.parsear_departamental(FIX / "precios-referencia-departamental-2026-01-19.pdf")
    assert info["vigencia_inicio"] == "2026-01-19"
    assert info["vigencia_fin"] == "2026-01-25"
    assert len(info["departamentos"]) == 22
    guate = next(d for d in info["departamentos"] if d["departamento"] == "Guatemala")
    assert guate["cabecera"] == "Ciudad de Guatemala"
    assert guate["superior"] == 27.59
    peten = next(d for d in info["departamentos"] if d["departamento"] == "Petén")
    assert peten["diesel"] == 26.38
    assert info["departamentos"][0]["departamento"] == "Guatemala"


def test_deteccion_tipo_por_contenido():
    assert mem.parsear_pdf(FIX / "precios-referencia-departamental-2026-01-19.pdf")["tipo"] == "departamental"
    assert mem.parsear_pdf(FIX / "informe-ejecutivo-area-metropolitana-2026-01-19.pdf")["tipo"] == "ejecutivo"


def test_extraer_enlaces_del_listado():
    html = (FIX / "listado-mem-2026-05-14.html").read_text(encoding="utf-8", errors="ignore")
    enlaces = mem.extraer_enlaces(html)
    tipos = {e["tipo"] for e in enlaces}
    assert "ejecutivo" in tipos and "departamental" in tipos
    assert enlaces[0]["fecha"] >= "2026-05-05"
    assert all(e["url"].startswith("https://mem.gob.gt/wp-content/uploads/") for e in enlaces)


def test_clasificar_nombre():
    assert mem.clasificar_nombre("https://x/INFORME-EJECUTIVO-DE-PRECIOS-DE-LOS-COMBUSTIBLES-2026-04-20.pdf") == ("ejecutivo", "2026-04-20")
    assert mem.clasificar_nombre("Informe-de-precios-de-combustible-a-nivel-nacional-AST-2026-05-05-1.pdf") == ("departamental", "2026-05-05")
    assert mem.clasificar_nombre("otro.pdf") == (None, None)


def test_candidatos_por_fecha_solo_dias_habiles():
    cands = mem.candidatos_por_fecha(date(2026, 9, 11), dias=7)
    fechas = {c["fecha"] for c in cands}
    assert "2026-09-06" not in fechas and "2026-09-05" not in fechas  # fin de semana
    assert any("INFORME-EJECUTIVO-DE-PRECIOS-DE-LOS-COMBUSTIBLES-2026-09-11.pdf" in c["url"] for c in cands)
