# -*- coding: utf-8 -*-
"""Plantillas de mensajes de Gasolina GT. Edita el texto aquí sin tocar la lógica.

Reglas de estilo: máximo 5 líneas, primera línea = la decisión, un solo emoji al inicio
(🔴 alza, 🟢 baja, 🟡 estable), sin tickers ni porcentajes técnicos.

Variables disponibles (se rellenan con str.format):
  emoji, veredicto, cambio, superior, regular, diesel, razon,
  depto_barato, cabecera_barata, precio_barato, noticias (3 titulares en una línea),
  fecha, fecha_mem, puntaje, proximo_martes
"""

# Mensaje corto diario (canal de Telegram, WhatsApp, tablero). 5 líneas.
MENSAJE_DIARIO = (
    "{emoji} {veredicto}. {cambio}\n"
    "Súper {superior} · Regular {regular} · Diésel {diesel}\n"
    "{razon}\n"
    "Más barato: {depto_barato} (regular {precio_barato})\n"
    "Noticias: {noticias}"
)

# Respuesta a /senal
MENSAJE_SENAL = (
    "{emoji} {veredicto}. {cambio}\n"
    "{razon}\n"
    "Próximo cambio del MEM: martes {proximo_martes}."
)

# Respuesta a /precio <departamento>
MENSAJE_PRECIO = (
    "⛽ {departamento} ({cabecera})\n"
    "Súper {superior} · Regular {regular} · Diésel {diesel}\n"
    "{comparacion}\n"
    "Precio de referencia MEM, autoservicio, vigente desde {fecha_mem}."
)
COMPARACION_MAS_BARATO = "Es el departamento más barato del país."
COMPARACION_OTRO = "{diferencia} más caro que {depto_barato}, el más barato."

# Cuando /precio no reconoce el departamento
MENSAJE_PRECIO_NO_ENCONTRADO = (
    "No encontré ese departamento. Prueba con uno de estos:\n{lista}"
)

# Respuesta a /start y /ayuda
MENSAJE_AYUDA = (
    "⛽ Gasolina GT te dice dónde y cuándo llenar.\n"
    "/senal → ¿lleno hoy o espero?\n"
    "/precio Quetzaltenango → precio en tu departamento\n"
    "Cada mañana a las 7:00 publico el reporte en el canal."
)

# Respuesta a /plus cuando plus_activo es true en config/plan.json
MENSAJE_PLUS = (
    "🚚 Plus para flotillas: alertas por flotilla, reporte mensual en Excel y proyección a 4 semanas.\n"
    "{moneda} {precio} al mes.\n"
    "{link}"
)
# Respuesta a /plus cuando el plan no está activo
MENSAJE_PLUS_INACTIVO = "Por ahora todo Gasolina GT es gratis. 🙌"

# Línea extra de los martes: lo que publicó el MEM vs lo que predijimos
MENSAJE_MARTES = "Martes: el MEM publicó {real}; nosotros dijimos {predicho}. {resultado}"
RESULTADO_ACIERTO = "✅ Acertamos."
RESULTADO_FALLO = "❌ Fallamos, seguimos ajustando."
RESULTADO_SIN_DATO = "⏳ Aún sin el informe del MEM de esta semana."

# Texto del veredicto por tendencia (por si quieres cambiar las palabras)
VEREDICTOS = {"alza": "Llena HOY", "baja": "Espera", "estable": "Llena esta semana"}

# Reporte largo en Markdown (data/reportes/AAAA-MM-DD.md)
REPORTE_MD = """# Reporte Gasolina GT · {fecha}

{emoji} **{veredicto}.** {cambio}

| Producto | Precio de referencia (Q/galón, autoservicio) |
|---|---|
| Súper | {superior} |
| Regular | {regular} |
| Diésel | {diesel} |

Datos del MEM del {fecha_mem}.

**Por qué:** {razon}

**Puntaje de señal:** {puntaje} (de -100 a +100). Gasolina en EE.UU. a 7 días: {rbob_pct}. Dólar a 7 días: {fx_pct}.
Noticias últimos 7 días: {n_alza} al alza, {n_baja} a la baja.

**Más barato:** {depto_barato} ({cabecera_barata}), regular {precio_barato}. **Más caro:** {depto_caro}, regular {precio_caro}.

## Noticias que mueven el precio
{noticias_md}

{seccion_martes}
"""
