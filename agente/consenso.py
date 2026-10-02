"""El consenso: qué precio dicen la mayoría de las fuentes, y qué tan de acuerdo están.

La idea es simple. Para un día y un combustible juntamos lo que dice cada fuente. Los valores que
casi coinciden se agrupan. El grupo más grande gana y ese es el precio que publicamos, diciendo
cuántas fuentes lo respaldan y cuáles dicen otra cosa.

Niveles:
  consenso      tres o más fuentes distintas coinciden. Es lo más confiable que podemos tener.
  confirmado    dos fuentes coinciden.
  sin confirmar una sola fuente lo dice. Se publica, pero avisando.
  en disputa    dos grupos parejos dicen cosas distintas. Se publica el mayor, avisando del otro.
El informe oficial del MEM, cuando lo tenemos, vale por sí solo y manda sobre todo lo demás.
"""
from __future__ import annotations

CERCA = 0.15        # dos fuentes "dicen lo mismo" si no se separan más de Q0.15
PARA_CONSENSO = 3   # fuentes distintas para llamarlo consenso
PARA_CONFIRMAR = 2


def _mediana(valores: list[float]) -> float:
    v = sorted(valores)
    n = len(v)
    return round(v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2, 2)


def agrupar(observaciones: list[dict], producto: str) -> list[dict]:
    """Junta en grupos las lecturas que dicen prácticamente el mismo precio."""
    puntos = [(o[producto], o.get("fuente", "?"), o.get("t", "")) for o in observaciones
              if o.get(producto) is not None]
    grupos: list[dict] = []
    for valor, fuente, cuando in sorted(puntos):
        for g in grupos:
            if abs(valor - g["valores"][0]) <= CERCA:
                g["valores"].append(valor)
                g["fuentes"].add(fuente)
                g["ultimo"] = max(g["ultimo"], cuando)
                break
        else:
            grupos.append({"valores": [valor], "fuentes": {fuente}, "ultimo": cuando})
    for g in grupos:
        g["valor"] = _mediana(g["valores"])
        g["fuentes"] = sorted(g["fuentes"])
    # Gana el que más FUENTES DISTINTAS lo respalden. En empate gana el MÁS RECIENTE: una nota vieja
    # que todavía trae el precio de la semana pasada no debe pesar igual que la de esta mañana.
    grupos.sort(key=lambda g: (len(g["fuentes"]), g["ultimo"], len(g["valores"])), reverse=True)
    return grupos


def calcular(observaciones: list[dict], producto: str) -> dict | None:
    """Devuelve el precio de consenso con su respaldo, o None si nadie dijo nada."""
    grupos = agrupar(observaciones, producto)
    if not grupos:
        return None
    gana = grupos[0]
    otros = grupos[1:]
    apoyos = len(gana["fuentes"])

    if apoyos >= PARA_CONSENSO:
        nivel = "consenso"
    elif apoyos >= PARA_CONFIRMAR:
        nivel = "confirmado"
    else:
        nivel = "sin confirmar"
    # Si otro grupo tiene casi el mismo respaldo, no hay acuerdo: hay que decirlo.
    if otros and len(otros[0]["fuentes"]) >= apoyos:
        nivel = "en disputa"

    return {
        "valor": gana["valor"],
        "nivel": nivel,
        "apoyos": apoyos,
        "fuentes": gana["fuentes"],
        "discrepan": [{"valor": g["valor"], "fuentes": g["fuentes"]} for g in otros],
    }


def frase(resultado: dict | None, producto: str = "") -> str:
    """Cómo se le explica el respaldo a una persona normal."""
    if not resultado:
        return "sin dato"
    n, nivel = resultado["apoyos"], resultado["nivel"]
    if nivel == "consenso":
        return f"✅ Lo dicen {n} fuentes distintas"
    if nivel == "confirmado":
        return f"✅ Confirmado por {n} fuentes"
    if nivel == "en disputa":
        otro = resultado["discrepan"][0]
        return f"⚠ No hay acuerdo: unas dicen Q{resultado['valor']:.2f} y otras Q{otro['valor']:.2f}"
    return f"⚠ Lo dice una sola fuente ({resultado['fuentes'][0]})"
