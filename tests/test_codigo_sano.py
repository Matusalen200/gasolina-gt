"""Guarda que no se nos escape un nombre inexistente (como llamar a una función que nunca definimos).

Ese tipo de error no lo atrapan las otras pruebas porque solo revienta cuando la persona corre el
programa. Aquí se revisa todo el código de una vez.
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ["agente", "bot", "scripts", "reportes", "tests"]


def test_no_hay_nombres_indefinidos_ni_imports_rotos():
    archivos = [str(p) for c in CARPETAS for p in (RAIZ / c).rglob("*.py")]
    assert archivos, "no encontré archivos de Python"
    r = subprocess.run([sys.executable, "-m", "pyflakes", *archivos], capture_output=True, text=True, cwd=RAIZ)
    problemas = [l for l in (r.stdout + r.stderr).splitlines()
                 if "undefined name" in l or "imported but unused" not in l and l.strip()]
    graves = [l for l in problemas if "undefined name" in l or "syntax" in l.lower()]
    assert not graves, "Código roto:\n" + "\n".join(graves)


def test_nombre_del_proyecto_no_se_come_letras():
    """rstrip('.git') se comía el final de 'gasolina-gt'. Este es el caso que falló de verdad."""
    from scripts.publicar import nombre_de_url
    assert nombre_de_url("https://github.com/Matusalen200/gasolina-gt.git") == "gasolina-gt"
    assert nombre_de_url("https://github.com/Matusalen200/gasolina-gt") == "gasolina-gt"
    assert nombre_de_url("https://github.com/alguien/git-git.git/") == "git-git"
    assert nombre_de_url("git@github.com:alguien/proyecto.git") == "proyecto"
