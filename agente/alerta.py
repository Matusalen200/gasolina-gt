"""Cambios radicales: en vez de publicarlos de una, te pregunta primero.

Cuando el precio da un salto grande y todavía lo dice una sola fuente, puede ser dos cosas muy
distintas: un cambio de verdad (como el Decreto 22-2026, que bajó el galón casi Q8) o un error
de lectura. Publicar cualquiera de las dos a ciegas es malo.

Entonces: el salto se guarda como PENDIENTE, el bot te avisa por Telegram y tú decides con
/confirmar o /rechazar. Si mientras tanto otra fuente dice lo mismo, se aprueba solo: el consenso
ya resolvió la duda y no hace falta molestarte.
"""
from __future__ import annotations

from agente.comun import DATA, ahora_gt, guardar_json, leer_json, log

RUTA = DATA / "pendientes.json"
SALTO = 3.0          # un cambio de más de Q3 el galón se considera radical
MAX_GUARDADOS = 30


def _clave(fecha: str, producto: str) -> str:
    return f"{fecha}|{producto}"


def revisar(ultimo: dict, referencia: dict) -> list[dict]:
    """Compara el precio nuevo contra el anterior y guarda los saltos que haga falta consultar.

    Devuelve los pendientes nuevos (los que todavía nadie ha visto).
    """
    pendientes = leer_json(RUTA, {}) or {}
    nuevos = []
    for producto, dato in (ultimo or {}).items():
        valor, antes = dato.get("valor"), (referencia or {}).get(producto)
        if valor is None or antes is None:
            continue
        salto = round(valor - antes, 2)
        if abs(salto) < SALTO:
            continue
        clave = _clave(dato.get("fecha", ""), producto)
        ya = pendientes.get(clave)
        if ya and ya.get("estado") != "pendiente":
            continue          # ya lo resolviste antes, no se vuelve a preguntar
        # Si varias fuentes ya coinciden, el consenso resolvió la duda y no hay que molestar a nadie.
        if dato.get("nivel") in ("consenso", "confirmado"):
            pendientes[clave] = {**(ya or {}), "estado": "aprobado por consenso",
                                 "producto": producto, "fecha": dato.get("fecha"),
                                 "valor": valor, "antes": antes, "salto": salto,
                                 "fuentes": dato.get("fuentes", []),
                                 "resuelto": ahora_gt().isoformat(timespec="minutes")}
            log(f"Cambio radical en {producto} ({antes} → {valor}) aprobado solo: "
                f"lo confirman {dato.get('apoyos')} fuentes")
            continue
        if ya:
            continue          # ya está anotado y esperando tu respuesta
        pendientes[clave] = {
            "estado": "pendiente", "producto": producto, "fecha": dato.get("fecha"),
            "valor": valor, "antes": antes, "salto": salto,
            "fuente": dato.get("fuente"), "url": dato.get("url"),
            "detectado": ahora_gt().isoformat(timespec="minutes"), "avisado": False,
        }
        nuevos.append(pendientes[clave])
        log(f"Cambio radical en {producto}: {antes} → {valor} ({salto:+.2f}). "
            f"Lo dice solo {dato.get('fuente')}. Queda pendiente de tu confirmación.", "WARN")

    if len(pendientes) > MAX_GUARDADOS:
        viejas = sorted(pendientes, key=lambda k: pendientes[k].get("detectado", ""))[:-MAX_GUARDADOS]
        for k in viejas:
            pendientes.pop(k, None)
    guardar_json(RUTA, pendientes)
    return nuevos


def sin_avisar() -> list[dict]:
    """Los cambios radicales que todavía no te hemos contado."""
    p = leer_json(RUTA, {}) or {}
    return [v for v in p.values() if v.get("estado") == "pendiente" and not v.get("avisado")]


def marcar_avisados() -> None:
    p = leer_json(RUTA, {}) or {}
    for v in p.values():
        if v.get("estado") == "pendiente":
            v["avisado"] = True
    guardar_json(RUTA, p)


def pendientes() -> list[dict]:
    p = leer_json(RUTA, {}) or {}
    return [v for v in p.values() if v.get("estado") == "pendiente"]


def resolver(aprobar: bool) -> list[dict]:
    """Aprueba o rechaza todo lo que esté esperando. Devuelve lo que se resolvió."""
    p = leer_json(RUTA, {}) or {}
    tocados = []
    for v in p.values():
        if v.get("estado") == "pendiente":
            v["estado"] = "aprobado" if aprobar else "rechazado"
            v["resuelto"] = ahora_gt().isoformat(timespec="minutes")
            tocados.append(v)
    guardar_json(RUTA, p)
    if tocados:
        log(f"Cambios radicales {'aprobados' if aprobar else 'rechazados'}: {len(tocados)}")
    return tocados


def rechazados() -> set:
    """Claves (fecha|producto) que decidiste no publicar."""
    p = leer_json(RUTA, {}) or {}
    return {k for k, v in p.items() if v.get("estado") == "rechazado"}
