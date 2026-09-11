# -*- coding: utf-8 -*-
"""Plantillas de mensajes de Gasolina GT. Edita el texto aquí sin tocar la lógica.

Reglas de estilo: frases cortas que entienda un niño. Máximo 5 líneas. Primera línea = qué hacer.
Un solo emoji al inicio (🔴 va a subir, 🟢 va a bajar, 🟡 se queda igual). Sin tecnicismos.

Variables disponibles (se rellenan con str.format):
  emoji, veredicto, cambio, superior, regular, diesel, razon,
  depto_barato, cabecera_barata, precio_barato, noticias (3 titulares en una línea),
  fecha, fecha_mem, puntaje, proximo_martes
"""

# Mensaje corto diario (canal de Telegram, WhatsApp, tablero). 5 líneas.
MENSAJE_DIARIO = (
    "{emoji} {veredicto}. {cambio}\n"
    "Hoy el galón cuesta: Súper {superior} · Regular {regular} · Diésel {diesel}\n"
    "{razon}\n"
    "Lo más barato: {depto_barato}, regular a {precio_barato}\n"
    "Noticias: {noticias}"
)

# Respuesta a /senal
MENSAJE_SENAL = (
    "{emoji} {veredicto}. {cambio}\n"
    "{razon}\n"
    "El precio cambia el martes {proximo_martes}."
)

# Respuesta a /precio <departamento>
MENSAJE_PRECIO = (
    "⛽ Hoy en {departamento} ({cabecera}):\n"
    "Súper {superior} · Regular {regular} · Diésel {diesel}\n"
    "{comparacion}\n"
    "Dato del {fecha_mem}.{estimado}"
)
COMPARACION_MAS_BARATO = "Es el lugar más barato del país. 🎉"
COMPARACION_OTRO = "Pagas {diferencia} más por galón que en {depto_barato}, el más barato."
NOTA_ESTIMADO = " Es un cálculo: precio de la capital hoy más lo que suele costar de más en tu departamento."

# Cuando /precio no reconoce el departamento
MENSAJE_PRECIO_NO_ENCONTRADO = (
    "No conozco ese lugar. Escribe /precio y uno de estos:\n{lista}"
)

# Respuesta a /start y /ayuda
MENSAJE_AYUDA = (
    "⛽ Hola. Te digo si conviene llenar hoy y cuánto cuesta.\n"
    "/senal → ¿lleno hoy o espero?\n"
    "/precio Quetzaltenango → precio en tu departamento\n"
    "Cada mañana a las 7 te mando el resumen."
)

# Respuesta a /plus cuando plus_activo es true en config/plan.json
MENSAJE_PLUS = (
    "🚚 Plus para flotillas: avisos para tus camiones, reporte mensual en Excel y precio a 4 semanas.\n"
    "{moneda} {precio} al mes.\n"
    "{link}"
)
# Respuesta a /plus cuando el plan no está activo
MENSAJE_PLUS_INACTIVO = "Todo Gasolina GT es gratis. 🙌"

# Línea extra de los martes: lo que publicó el MEM vs lo que predijimos
MENSAJE_MARTES = "Martes: el precio {real}. Nosotros dijimos {predicho}. {resultado}"
RESULTADO_ACIERTO = "✅ Le atinamos."
RESULTADO_FALLO = "❌ Fallamos. Seguimos aprendiendo."
RESULTADO_SIN_DATO = "⏳ Todavía no sale el precio oficial."

# Texto del veredicto por tendencia (por si quieres cambiar las palabras)
VEREDICTOS = {"alza": "Llena HOY", "baja": "Espera", "estable": "Sin apuro"}

# Reporte largo en Markdown (data/reportes/AAAA-MM-DD.md)
REPORTE_MD = """# Reporte Gasolina GT · {fecha}

{emoji} **{veredicto}.** {cambio}

| Producto | Precio hoy (Q/galón, autoservicio) |
|---|---|
| Súper | {superior} |
| Regular | {regular} |
| Diésel | {diesel} |

Dato del {fecha_mem}.

**Por qué:** {razon}

**Puntaje de señal:** {puntaje} (de -100 a +100). Gasolina en EE.UU. a 7 días: {rbob_pct}. Dólar a 7 días: {fx_pct}.
Noticias últimos 7 días: {n_alza} al alza, {n_baja} a la baja.

**Más barato:** {depto_barato} ({cabecera_barata}), regular {precio_barato}. **Más caro:** {depto_caro}, regular {precio_caro}.

## Noticias que mueven el precio
{noticias_md}

{seccion_martes}
"""
