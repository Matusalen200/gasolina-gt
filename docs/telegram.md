# Cómo compartir Gasolina GT con el bot de Telegram

Tiempo: 10 minutos. Todo gratis.

## 1. Crea el bot (2 minutos)

1. En Telegram busca **@BotFather** y escríbele `/newbot`.
2. Nombre: `Gasolina GT`. Usuario: algo que termine en `bot`, por ejemplo `gasolinagt_bot`.
3. BotFather te da un **token** (parecido a `123456789:AAH...`). Guárdalo, es la llave del bot.
4. Opcional: `/setcommands` y pega:
   ```
   senal - ¿Lleno hoy o espero?
   precio - Precio en tu departamento, ej. /precio Petén
   ayuda - Qué hace este bot
   ```

## 2. Crea el canal (2 minutos)

1. Telegram → Nuevo canal → nombre `Gasolina GT`, público, usuario por ejemplo `@gasolinagt`.
2. Entra al canal → Administradores → Agregar → busca tu bot → dale permiso de **publicar mensajes**.
3. El identificador del canal es `@gasolinagt` (con la arroba).

## 3. Dale las llaves al agente (1 minuto)

Si ya publicaste el repo con `scripts/publicar.ps1`, solo agrega los dos secrets:

```powershell
gh secret set TELEGRAM_BOT_TOKEN --body "123456789:AAH..."
gh secret set TELEGRAM_CHANNEL_ID --body "@gasolinagt"
```

Si todavía no lo publicaste, pásalos al script y él los guarda:

```powershell
.\scripts\publicar.ps1 -Nombre gasolina-gt -AnthropicKey "sk-ant-..." -TelegramToken "123456789:AAH..." -TelegramChannel "@gasolinagt"
```

## 4. Qué pasa después

- Cada mañana a las **7:00** el agente publica en el canal el mensaje de 5 líneas (el mismo que sale en el
  tablero con el botón "Compartir por WhatsApp").
- Cualquier persona puede escribirle al bot `/senal` o `/precio Quetzaltenango`. El bot responde en la
  siguiente corrida del agente (cada hora en horario hábil). Si quieres respuestas al instante, ese es el
  siguiente paso: un pequeño servidor gratis (Cloudflare Workers) con webhook; el código de respuestas ya
  está listo en `bot/telegram.py`.
- Para compartir el canal: manda el enlace `https://t.me/gasolinagt` por WhatsApp o ponlo en el tablero.

## 5. Probar sin publicar nada

```powershell
python bot/telegram.py "/precio Petén"
python bot/telegram.py "/senal"
```

## 6. Cambiar los textos

Todos los mensajes están en `bot/plantillas.py`. Cambia las palabras y listo; no hay que tocar nada más.
