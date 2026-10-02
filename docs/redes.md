# Publicar solo en Facebook, Instagram y X

El agente ya publica en Telegram. Estas tres se conectan igual: se consiguen unas llaves una sola vez
y a partir de ahí publica cada mañana sin que toques nada.

**Lo primero que hay que saber, para no perder el tiempo:**

| Red | ¿Se puede automatizar? | Cuesta | Qué tan enredado |
|---|---|---|---|
| Telegram | Sí, ya está | Gratis | Ya hecho |
| **Facebook** (página) | Sí | Gratis | Medio · 20 minutos |
| **Instagram** (empresa) | Sí, con foto | Gratis | Medio · va junto con Facebook |
| **X** (Twitter) | Sí | Gratis hasta 500 al mes | Medio · 15 minutos |
| **WhatsApp Canal** | **No se puede** | — | Meta no da forma de hacerlo |
| WhatsApp Business API | Sí, pero no es canal | Se paga por mensaje | Ver [whatsapp.md](whatsapp.md) |

---

## WhatsApp: por qué el botón no "publica"

El botón del tablero que dice **Compartir por WhatsApp** no publica en tu canal. No existe ninguna
forma de hacerlo: Meta no abrió esa puerta para los canales de WhatsApp, ni a nosotros ni a nadie.

Lo que el botón hace es abrir WhatsApp con el mensaje ya escrito para que lo pegues donde quieras.
En el celular abre la aplicación. En la computadora antes no hacía nada; ahora **copia el mensaje**
y te avisa, para que lo pegues tú en el canal. Eso es un minuto al día.

---

## Facebook e Instagram: la forma fácil

**Doble clic en «Conectar redes.bat».** Igual que el del bot de Telegram: te explica qué necesitas,
te pide una sola llave, encuentra tu página sola, busca tu Instagram, publica una prueba y guarda
todo. Los pasos de abajo son por si quieres entender qué está pasando.

## Facebook e Instagram (van juntos)

Instagram solo se puede automatizar si es cuenta de **empresa o creador** y está **ligada a una
página de Facebook**. Por eso se hacen los dos de una vez.

### 1. Ten lista la página y la cuenta (5 minutos)

1. Una **página** de Facebook para Gasolina GT (no tu perfil personal).
2. Tu Instagram en **cuenta de empresa**: en la app, Configuración → Tipo de cuenta → Cambiar a
   cuenta profesional.
3. Liga las dos: en la página de Facebook → Configuración → Instagram vinculado.

### 2. Crea la aplicación de Meta (10 minutos)

1. Entra a https://developers.facebook.com y regístrate como desarrollador. Es gratis.
2. **Mis aplicaciones → Crear aplicación → Otro → Empresa.** Ponle `Gasolina GT`.
3. Dentro de la aplicación, agrega el producto **Graph API** (o "Inicio de sesión de Facebook").

### 3. Saca las llaves (5 minutos)

1. Abre el **Explorador de la API Graph**: https://developers.facebook.com/tools/explorer
2. Arriba a la derecha elige tu aplicación.
3. En **Permisos**, agrega estos cuatro:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_content_publish`
4. Botón **Generar token de acceso** y acepta.
5. Consulta `me/accounts` y dale a Enviar. En la respuesta busca tu página: copia su `id`
   (ese es **FACEBOOK_PAGE_ID**) y su `access_token` (ese es **FACEBOOK_TOKEN**).
6. Para Instagram, consulta `{FACEBOOK_PAGE_ID}?fields=instagram_business_account`.
   El `id` que salga es **INSTAGRAM_USER_ID**.

> **Importante:** el token que da el explorador dura una o dos horas. Para que sirva siempre, cámbialo
> por uno de larga duración. En la misma página de herramientas hay un **Depurador de tokens**:
> pega el token, dale a **Extender token de acceso** y usa el nuevo. El token de página así extendido
> no caduca mientras no cambies tu contraseña.

---

## X (antes Twitter)

1. Entra a https://developer.x.com y crea una cuenta de desarrollador con el usuario de Gasolina GT.
2. Crea un **Proyecto** y dentro una **App**.
3. En **User authentication settings**, activa permisos de **Lectura y escritura**.
4. En **Keys and tokens** copia cuatro cosas:
   - API Key → **X_API_KEY**
   - API Key Secret → **X_API_SECRET**
   - Access Token → **X_ACCESS_TOKEN**
   - Access Token Secret → **X_ACCESS_SECRET**

El plan gratis deja **500 publicaciones al mes**. Nosotros usamos una diaria, así que sobra.

---

## Guardar las llaves

Abre `config/.env.local` (el mismo archivo donde está la llave de Telegram) y agrega las que tengas,
una por línea:

```
FACEBOOK_PAGE_ID=123456789012345
FACEBOOK_TOKEN=EAAG...
INSTAGRAM_USER_ID=17841400000000000
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_SECRET=...
```

Ese archivo es privado y nunca se sube a internet.

Después corre **Publicar en internet.bat** otra vez: sube estas llaves a GitHub como secretos y
desde ahí el agente publica solo, con tu computadora apagada.

## Probar antes de publicar

```powershell
python bot\redes.py --probar
```

Te dice qué redes están conectadas y qué imagen usaría. Para publicar de una vez, aunque ya se haya
publicado hoy:

```powershell
python bot\redes.py --forzar
```

## Qué se publica

El mismo mensaje de cinco líneas del canal de Telegram, con la imagen de la gráfica y la tabla.
Los textos se cambian en `bot/plantillas.py`.

Instagram **exige** que la imagen esté publicada en internet, así que toma la del tablero. Si el
tablero no está publicado, Instagram se salta y las demás sí publican.
