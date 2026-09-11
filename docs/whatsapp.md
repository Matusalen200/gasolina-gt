# WhatsApp para Gasolina GT: evaluación (sin implementar)

Objetivo: enviar cada mañana el mismo mensaje de 5 líneas que va al canal de Telegram, y opcionalmente
responder `/precio` y `/senal`. Cifras en dólares de septiembre de 2026; el tipo de cambio usado es Q7.65 por US$.

## Resumen

| Opción | Costo/mes 1,000 usuarios | Costo/mes 10,000 usuarios | Aprobación | Riesgo de bloqueo | Recomendación |
|---|---|---|---|---|---|
| 1. Canal de WhatsApp (manual) | US$0 | US$0 | Inmediata (minutos) | Muy bajo | **Empezar aquí, hoy** |
| 2a. WhatsApp Business API, Meta directo (Cloud API) | US$8–25 (solo si hay conversaciones de marketing) | US$80–250 | 1–7 días verificación de negocio; 2–4 semanas para plantillas de marketing y límite de envío alto | Bajo si se respeta el opt-in | Segunda fase, cuando haya Plus |
| 2b. WhatsApp Business API vía Twilio | US$20–45 (Meta + US$0.005/msg Twilio) | US$150–400 | Igual que Meta + registro Twilio (1–3 días) | Bajo | Solo si ya usas Twilio |
| 3. Librerías no oficiales (Baileys, whatsapp-web.js) | US$5–15 (VPS) | US$5–15 (VPS) pero técnicamente inviable | Ninguna | **Muy alto**: baneo del número en días o semanas | No usar |

## 1. Canal de WhatsApp (manual)

Cómo funciona: creas un Canal de WhatsApp desde la app (Novedades → Canales → Crear canal). Es difusión
unidireccional, igual que un canal de Telegram. Los seguidores no ven tu número ni entre ellos.

- Costo: US$0 a cualquier escala. WhatsApp no cobra por canales ni limita seguidores.
- Aprobación: ninguna. El canal existe en minutos. Verificación (palomita) opcional, semanas.
- Riesgo de bloqueo: muy bajo; es contenido editorial propio, sin mensajes no solicitados.
- Automatización: **no hay API pública para publicar en canales.** El bot puede dejar el mensaje listo
  (ya lo hace en `data/reportes/ultimo.json`) y tú lo pegas en 20 segundos cada mañana, o se usa un
  atajo del teléfono. Existe API para canales solo en el programa cerrado de socios de Meta.
- Sin comandos `/precio`; los usuarios van al tablero para "dónde".

Costo real: 1 minuto diario de tu tiempo. Con 1,000 o 10,000 seguidores es igual.

## 2. WhatsApp Business API

### 2a. Meta directo (WhatsApp Cloud API)

Cómo funciona: cuenta de Meta Business verificada, número dedicado (no puede estar en la app normal),
plantillas de mensaje aprobadas por Meta, envío por HTTP desde GitHub Actions. Requiere que cada usuario
dé opt-in (escribirte primero o marcar una casilla en el tablero) y guardar esos números en algún lado
(hoy no tenemos base de datos: haría falta, por ejemplo, un webhook que guarde números en un JSON del repo
o en un servicio como Supabase gratis).

Precios de Meta (desde julio 2025 cobran por mensaje de plantilla, no por conversación; México/Centroamérica
"resto de Latinoamérica"):
- Plantilla de marketing: ≈ US$0.0250 por mensaje. Un reporte diario es "marketing" salvo que el usuario lo
  haya pedido en las últimas 24 h.
- Plantilla de utilidad: ≈ US$0.0068 por mensaje. Respuestas a `/precio` dentro de la ventana de 24 h
  después de que el usuario escribe: **gratis**.
- Los primeros 1,000 mensajes de servicio (respuestas) al mes son gratis.

Estimación reporte diario, 22 días hábiles al mes:
- 1,000 usuarios × 22 × US$0.025 = **US$550/mes** si se clasifica como marketing.
  Si Meta acepta la plantilla como "utilidad" (aviso de precio solicitado por el usuario): 1,000 × 22 ×
  US$0.0068 = **US$150/mes**. Realista: US$150–550.
- 10,000 usuarios: **US$1,500–5,500/mes**.
- Más número dedicado (chip prepago Q50/mes) y, si quieres verificación, US$0.

Corrección a la tabla resumen: los US$8–25 y US$80–250 de la tabla corresponden a enviar el reporte solo
**una vez por semana** (el lunes, antes del cambio del martes) y responder comandos gratis dentro de la
ventana de 24 h. El envío diario cuesta lo de arriba. Ese es el diseño recomendado si algún día se usa la API:
un mensaje semanal proactivo y todo lo demás como respuesta.

- Aprobación: verificación de negocio 1–7 días (necesita documentos de una empresa o comerciante
  individual con NIT); plantillas 1–48 h cada una; límite inicial de 250 conversaciones nuevas por día,
  sube a 1,000 y 10,000 conforme la calidad se mantenga verde (2–4 semanas).
- Riesgo de bloqueo: bajo si hay opt-in claro y baja tasa de "reportar/bloquear". Un lote de mensajes
  no solicitados puede bajar la calidad y congelar el número.

### 2b. Twilio (u otro BSP como 360dialog, Wati)

Mismo costo de Meta más la comisión del proveedor: Twilio cobra US$0.005 por mensaje enviado o recibido.
- 1,000 usuarios, reporte semanal + comandos: Meta US$8–25 + Twilio US$20 ≈ **US$30–45/mes**.
- 10,000 usuarios: Meta US$80–250 + Twilio US$200 ≈ **US$280–450/mes**.
- Con reporte diario: sumar US$110/mes (1,000) o US$1,100/mes (10,000) de comisión Twilio a lo de 2a.
- Ventaja: consola, registro de mensajes, sandbox de pruebas sin verificación, soporte. Desventaja: paga
  dos veces. 360dialog cobra tarifa fija (≈ US$49/mes) sin comisión por mensaje, mejor a partir de
  ~10,000 mensajes/mes.
- Aprobación: igual que Meta (Twilio tramita la verificación por ti) más 1–3 días de registro.

## 3. Librerías no oficiales (Baileys, whatsapp-web.js, venom)

Cómo funciona: un servidor emula WhatsApp Web con tu número personal y manda mensajes por script.
- Costo: un VPS de US$5–15/mes. No escala: WhatsApp limita a ~256 destinatarios por lista de difusión y
  detecta patrones de envío masivo.
- Aprobación: ninguna.
- Riesgo de bloqueo: **muy alto**. Meta banea números que usan clientes no oficiales, normalmente en días
  o pocas semanas cuando el volumen sube; pierdes el número y con él a todos los usuarios. Viola los
  términos de servicio. Además, no puede correr en GitHub Actions (necesita sesión persistente).
- No lo recomiendo para nada que tenga usuarios reales.

## Recomendación

1. **Hoy**: Canal de WhatsApp manual + canal de Telegram automático. Cero costo, cero riesgo. El bot deja
   el mensaje listo; copiar y pegar toma un minuto. Poner el enlace del canal en el tablero.
2. **Cuando haya ingresos Plus** (o más de ~2,000 seguidores que pidan alertas personales): WhatsApp
   Cloud API directo con Meta, con diseño de "un mensaje proactivo semanal + respuestas gratis en
   ventana de 24 h". Presupuesto US$10–50/mes hasta 1,000 usuarios. Requiere: número dedicado, NIT,
   almacenar los opt-in y un pequeño webhook (Cloudflare Workers gratis) para recibir mensajes.
3. **Nunca** librerías no oficiales con el número del proyecto.

Nota sobre precios: Meta cambia tarifas cada pocos meses; verificar en developers.facebook.com/docs/whatsapp/pricing
antes de decidir. Las cifras aquí son estimaciones de orden de magnitud para comparar opciones, no cotizaciones.
