# Cómo compartir Gasolina GT con el bot de Telegram

Tiempo: 10 minutos. Todo gratis.

> **¿Ya creaste el bot y el canal?** Entonces solo haz **doble clic en «Conectar bot.bat»** y sigue
> las preguntas. Te pide el token, encuentra tu canal solo, manda un mensaje de prueba y te ofrece
> programar todo para que corra sin que hagas nada. Los pasos de abajo son por si quieres entender
> qué está pasando o hacerlo a mano.

## 1. Crea el bot (2 minutos)

1. En Telegram busca **@BotFather** y escríbele `/newbot`.
2. Nombre: `Gasolina GT`. Usuario: algo que termine en `bot`, por ejemplo `gasolinagt_bot`.
3. BotFather te da un **token** (parecido a `123456789:AAH...`). Guárdalo, es la llave del bot.
4. No hace falta configurar los comandos a mano: la primera vez que corre, el bot registra solo su menú
   (el botón «/» de Telegram) con la lista de `bot/plantillas.py` → `COMANDOS_MENU`.

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

## 4. Qué sabe hacer el bot

| Comando | Qué contesta |
|---|---|
| `/hoy` | El resumen del día en 5 líneas |
| `/senal` | ¿Lleno hoy o espero? y cuánto cambia el martes |
| `/precio [departamento]` | Precio de los tres combustibles ahí. Sin nombre usa el que guardaste |
| `/baratos` · `/caros` | Los 5 departamentos más baratos o más caros. Acepta `super` o `diesel` |
| `/tanque 10` | Cuánto te cuesta llenar y cuánto ahorrarías en el lugar más barato |
| `/noticias` | Las 3 noticias que están moviendo el precio |
| `/futuro` | Lo que esperamos las próximas 4 semanas |
| `/aciertos` | Qué tan seguido le atinamos |
| `/mercado` | Petróleo, gasolina en EE.UU. y dólar |
| `/tope` | El precio tope aprobado por el Congreso |
| `/historial` | Los precios de las últimas semanas |
| `/midepto Quetzaltenango` | Guarda tu departamento para no repetirlo |
| `/tablero` | Enlace al tablero con gráficas |
| `/ayuda` | La lista completa |

También entiende texto normal: «Petén», «¿va a subir?», «dónde está más barata»,
«cuánto cuesta llenar 15 galones». Si hay `ANTHROPIC_API_KEY`, Claude responde las preguntas libres
usando **solo** los datos del agente (no inventa números); sin clave, el bot sugiere un comando.

## 5. Cuándo responde

- Cada mañana a las **7:00** publica el resumen en el canal.
- En GitHub Actions responde los mensajes pendientes **cada hora** en horario hábil.
- Para respuestas **al instante**, deja esto corriendo en tu PC:
  ```powershell
  $env:TELEGRAM_BOT_TOKEN="123456789:AAH..."
  python bot/telegram.py --escuchar
  ```
- Para compartir el canal: manda el enlace `https://t.me/gasolinagt` por WhatsApp o ponlo en el tablero.

## 6. Probar sin publicar nada

```powershell
python bot/telegram.py "/precio Petén"
python bot/telegram.py "/tanque 12 super Quetzaltenango"
python bot/telegram.py "¿va a subir la gasolina?"
```

## 7. Cambiar los textos

Todos los mensajes están en `bot/plantillas.py`. Cambia las palabras y listo; no hay que tocar nada más.
