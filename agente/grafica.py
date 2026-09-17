"""Dibuja el resumen de precios como UNA imagen (data/grafica_precios.png), para mandarla por Telegram.

Lleva arriba la gráfica de los tres combustibles y abajo la tabla igual que la del MEM
(antes, hoy y cuánto cambió). Así en el canal se ve todo de un vistazo, sin abrir ningún enlace.
"""
from __future__ import annotations

from datetime import date, timedelta

from agente.comun import DATA, ahora_gt, leer_json, log

RUTA = DATA / "grafica_precios.png"
DIAS = 35
PRODUCTOS = [("superior", "Súper", "#e8871a"), ("regular", "Normal", "#1f5fbf"),
             ("diesel", "Diésel", "#8b5cf6"), ("kerosene", "Kerosene", "#8a94a6")]
EN_GRAFICA = ("superior", "regular", "diesel")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ALZA, BAJA, SUAVE, TEXTO, BORDE = "#d64545", "#2e9e5b", "#5b6470", "#14181d", "#dfe4ea"


def _serie(historial: list[dict], diario: list[dict], prod: str) -> dict[str, float]:
    puntos = {}
    for h in historial or []:
        if h.get(prod) is not None:
            puntos[h["fecha"]] = float(h[prod])
    for d in diario or []:
        if d.get(prod) is not None:
            puntos[d["fecha"]] = float(d[prod])
    return puntos


def _etiqueta(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MESES[d.month - 1]}"


def _q(v) -> str:
    return "–" if v is None else f"Q{v:,.2f}".replace(",", "")


def filas_tabla(precios: dict, vigente: dict) -> list[tuple]:
    """(nombre, antes, hoy, cambio, color) por combustible, como la tabla del MEM."""
    auto = (precios or {}).get("autoservicio", {}) or {}
    cambio = (precios or {}).get("cambio_semanal", {}) or {}
    filas = []
    for prod, nombre, _ in PRODUCTOS:
        hoy = vigente.get(prod, auto.get(prod))
        if hoy is None:
            continue
        dif = cambio.get(prod)
        antes = round(hoy - dif, 2) if dif is not None else None
        filas.append((nombre, antes, hoy, dif))
    return filas


def generar(ruta=None):
    """Crea la imagen. Devuelve la ruta, o None si no hay datos o falta matplotlib."""
    ruta = ruta or RUTA
    historial = leer_json(DATA / "precios_historial.json", []) or []
    hoy_datos = leer_json(DATA / "precio_hoy.json", {}) or {}
    precios = leer_json(DATA / "precios.json", {}) or {}

    series = {p: _serie(historial, hoy_datos.get("diario", []), p) for p in EN_GRAFICA}
    fechas = sorted({f for s in series.values() for f in s})
    if len(fechas) < 2:
        log("Gráfica: todavía no hay suficientes precios para dibujarla", "WARN")
        return None
    limite = (ahora_gt().date() - timedelta(days=DIAS)).isoformat()
    visibles = [f for f in fechas if f >= limite] or fechas[-8:]

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        log(f"Gráfica: falta matplotlib ({e}); se manda solo el texto", "WARN")
        return None

    from agente.reporte import precios_vigentes
    vigente, fecha_dato, _ = precios_vigentes(precios, hoy_datos)

    fig = plt.figure(figsize=(9, 7.2), dpi=110, facecolor="white")
    ejes = fig.add_gridspec(2, 1, height_ratios=[1.45, 1], hspace=0.28)
    ax = fig.add_subplot(ejes[0])
    ax.set_facecolor("white")

    x = range(len(visibles))
    for prod, nombre, color in PRODUCTOS:
        if prod not in EN_GRAFICA:
            continue
        s = series[prod]
        y, ultimo = [], None
        for f in visibles:  # arrastramos el último precio conocido para que no queden huecos
            ultimo = s.get(f, ultimo)
            y.append(ultimo)
        if all(v is None for v in y):
            continue
        ax.plot(x, y, label=nombre, color=color, linewidth=2.8, marker="o", markersize=4)
        if y[-1] is not None:
            ax.annotate(f"Q{y[-1]:.2f}", (len(visibles) - 1, y[-1]), textcoords="offset points",
                        xytext=(8, 0), color=color, fontsize=11, fontweight="bold", va="center")

    ax.set_title("Gasolina GT · precio del galón", fontsize=16, fontweight="bold", color=TEXTO, pad=12)
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    ax.grid(axis="y", color=BORDE, linewidth=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(BORDE)
    ax.tick_params(colors=SUAVE, labelsize=10)
    paso = max(1, len(visibles) // 5)
    ax.set_xticks(list(x)[::paso])
    ax.set_xticklabels([_etiqueta(visibles[i]) for i in list(x)[::paso]])
    ax.yaxis.set_major_formatter(lambda v, _: f"Q{v:.0f}")
    ax.margins(x=0.08)

    # ---- la tabla, igual que la del MEM ----
    axt = fig.add_subplot(ejes[1])
    axt.axis("off")
    filas = filas_tabla(precios, vigente)
    fecha_antes = (precios.get("autoservicio") or {}).get("fecha_anterior")
    encabezados = ["Combustible", f"Antes ({_etiqueta(fecha_antes)})" if fecha_antes else "Antes",
                   f"Hoy ({_etiqueta(fecha_dato)})" if fecha_dato else "Hoy", "Cambio"]
    cols = [0.02, 0.36, 0.62, 0.86]
    alto = 0.88
    for i, (texto, cx) in enumerate(zip(encabezados, cols)):
        axt.text(cx, alto, texto, fontsize=11, color=SUAVE, fontweight="bold",
                 ha="left" if i == 0 else "right", transform=axt.transAxes)
        if i:
            pass
    axt.plot([0, 1], [alto - 0.06, alto - 0.06], color=BORDE, lw=1.2, transform=axt.transAxes, clip_on=False)

    colores = {n: c for _, n, c in PRODUCTOS}
    y = alto - 0.19
    for nombre, antes, hoy, dif in filas:
        axt.plot([0.02], [y + 0.02], marker="o", markersize=8, color=colores[nombre],
                 transform=axt.transAxes, clip_on=False)
        axt.text(0.06, y, nombre, fontsize=13, color=TEXTO, fontweight="bold", transform=axt.transAxes)
        axt.text(cols[1], y, _q(antes), fontsize=13, color=SUAVE, ha="right", transform=axt.transAxes)
        axt.text(cols[2], y, _q(hoy), fontsize=14, color=TEXTO, fontweight="bold", ha="right", transform=axt.transAxes)
        if dif is None:
            txt, col = "–", SUAVE
        elif dif > 0:
            txt, col = f"▲ +Q{dif:.2f}", ALZA
        elif dif < 0:
            txt, col = f"▼ −Q{abs(dif):.2f}", BAJA
        else:
            txt, col = "= Q0.00", SUAVE
        axt.text(cols[3], y, txt, fontsize=13, color=col, fontweight="bold", ha="right", transform=axt.transAxes)
        y -= 0.19

    fig.text(0.5, 0.015, "Precios de referencia del MEM (autoservicio) y lo que publican los medios · gasolinagt",
             ha="center", fontsize=9, color=SUAVE)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, facecolor="white", bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    log(f"Gráfica lista: {ruta.name} ({len(visibles)} días, {len(filas)} combustibles)")
    return ruta


if __name__ == "__main__":  # pragma: no cover
    print(generar())
