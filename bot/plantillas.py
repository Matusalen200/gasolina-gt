# -*- coding: utf-8 -*-
"""Plantillas de mensajes de Gasolina GT. Edita el texto aquí sin tocar la lógica.

Reglas de estilo: frases cortas que entienda un niño. La primera línea dice qué hacer.
Un solo emoji al inicio (🔴 va a subir, 🟢 va a bajar, 🟡 se queda igual). Sin tecnicismos.

Variables disponibles (se rellenan con str.format):
  emoji, veredicto, cambio, superior, regular, diesel, razon,
  depto_barato, cabecera_barata, precio_barato, noticias (3 titulares en una línea),
  fecha, fecha_mem, puntaje, proximo_martes
"""

# ---------------------------------------------------------------- mensajes principales

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
NOTA_ESTIMADO = " Es un cálculo: precio oficial de la capital más lo que suele costar de más en tu departamento."

# Cuando /precio no reconoce el departamento
MENSAJE_PRECIO_NO_ENCONTRADO = (
    "No conozco ese lugar. Escribe /precio y uno de estos:\n{lista}"
)

# ---------------------------------------------------------------- listas

MENSAJE_BARATOS = "💚 Donde más barata está la {producto} hoy:\n{lista}\n{nota}"
MENSAJE_CAROS = "💸 Donde más cara está la {producto} hoy:\n{lista}\n{nota}"
FILA_LISTA = "{puesto}. {departamento} — {precio}"

# ---------------------------------------------------------------- calculadora

MENSAJE_TANQUE = (
    "⛽ Llenar {galones} galones de {producto} en {departamento}:\n"
    "Te cuesta como {total}.\n"
    "{ahorro}"
)
AHORRO_TANQUE = "Si llenaras en {depto_barato} pagarías {total_barato}: ahorras {ahorro}."
AHORRO_YA_BARATO = "Ya estás en el lugar más barato del país. 🎉"

# ---------------------------------------------------------------- información

MENSAJE_NOTICIAS = "📰 Lo que está moviendo el precio:\n{lista}"
FILA_NOTICIA = "{emoji} {titulo}"

MENSAJE_FUTURO = (
    "🔮 Lo que esperamos para las próximas 4 semanas (regular):\n"
    "{lista}\n"
    "{nota}"
)
FILA_FUTURO = "{fecha}: {precio}"
FUTURO_CALIBRANDO = "Todavía estamos aprendiendo; tómalo como una idea, no como promesa."

MENSAJE_ACIERTOS_OK = (
    "🎯 Le atinamos {aciertos} de {total} semanas ({porcentaje} %).\n"
    "Acierto = dijimos que subía, bajaba o seguía igual, y el martes pasó justo eso."
)
MENSAJE_ACIERTOS_CALIBRANDO = (
    "🎯 Todavía estamos contando.\n"
    "Cada martes vemos si adivinamos. Llevamos {total} de 4 semanas para darte un número."
)

MENSAJE_MERCADO = (
    "🌎 Lo que mueve el precio (para curiosos):\n"
    "Gasolina en EE.UU.: {rbob}\n"
    "Petróleo: {wti}\n"
    "Dólar: {dolar}\n"
    "Cambio de los últimos 7 días."
)

MENSAJE_TOPE = (
    "⚖️ Precio tope aprobado por el Congreso:\n"
    "Súper {superior} · Regular {regular} · Diésel {diesel}\n"
    "Cuando entre en vigor, ninguna gasolinera debería cobrar más."
)
MENSAJE_TOPE_SIN_DATO = "Todavía no hay un precio tope vigente que yo conozca."

MENSAJE_HISTORIAL = "📅 Así ha estado la {producto} las últimas semanas:\n{lista}"
FILA_HISTORIAL = "{fecha}: {precio}"

# ---------------------------------------------------------------- personal

MENSAJE_DEPTO_GUARDADO = (
    "✅ Listo, te anoté en {departamento}.\n"
    "Ahora escribe /precio y te doy el de tu depa sin repetirlo."
)
MENSAJE_SIN_DEPTO = (
    "Primero dime dónde vives: /midepto Quetzaltenango\n"
    "O escribe /precio y el nombre, por ejemplo /precio Petén."
)

# ---------------------------------------------------------------- ayuda y varios

MENSAJE_AYUDA = (
    "⛽ Hola. Te digo si conviene llenar hoy y cuánto cuesta.\n"
    "/hoy resumen · /senal ¿lleno o espero? · /precio tu departamento\n"
    "/baratos y /caros · /tanque 10 cuánto te cuesta llenar\n"
    "/noticias · /futuro · /aciertos · /mercado · /tope · /historial\n"
    "También puedes escribirme normal, como «¿subirá la gasolina?»."
)

MENSAJE_TABLERO = "📊 Todo con gráficas aquí:\n{url}"

# Respuesta a /plus cuando plus_activo es true en config/plan.json
MENSAJE_PLUS = (
    "🚚 Plus para flotillas: avisos para tus camiones, reporte mensual en Excel y precio a 4 semanas.\n"
    "{moneda} {precio} al mes.\n"
    "{link}"
)
# Respuesta a /plus cuando el plan no está activo
MENSAJE_PLUS_INACTIVO = "Todo Gasolina GT es gratis. 🙌"

MENSAJE_NO_ENTIENDO = (
    "No te entendí. 🤔\n"
    "Prueba /hoy, /senal o /precio Quetzaltenango.\n"
    "Escribe /ayuda para ver todo lo que sé hacer."
)
MENSAJE_SIN_DATOS = "Todavía no tengo ese dato. Vuelve en un rato."

# Línea extra de los martes: lo que publicó el MEM vs lo que predijimos
MENSAJE_MARTES = "Martes: el precio {real}. Nosotros dijimos {predicho}. {resultado}"
RESULTADO_ACIERTO = "✅ Le atinamos."
RESULTADO_FALLO = "❌ Fallamos. Seguimos aprendiendo."
RESULTADO_SIN_DATO = "⏳ Todavía no sale el precio oficial."

# Texto del veredicto por tendencia (por si quieres cambiar las palabras)
VEREDICTOS = {"alza": "Llena HOY", "baja": "Espera", "estable": "Sin apuro"}

# Menú de comandos que ve la gente en Telegram (botón "/")
COMANDOS_MENU = [
    ("hoy", "Resumen de hoy"),
    ("senal", "¿Lleno hoy o espero?"),
    ("precio", "Precio en tu departamento"),
    ("baratos", "Dónde está más barata"),
    ("caros", "Dónde está más cara"),
    ("tanque", "Cuánto cuesta llenar, ej. /tanque 10"),
    ("noticias", "Qué está moviendo el precio"),
    ("futuro", "Qué esperamos en 4 semanas"),
    ("aciertos", "¿Le atinamos?"),
    ("mercado", "Petróleo y dólar"),
    ("tope", "Precio tope del Congreso"),
    ("historial", "Precios de las últimas semanas"),
    ("midepto", "Guarda tu departamento"),
    ("tablero", "Ver todo con gráficas"),
    ("ayuda", "Qué sé hacer"),
]

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
