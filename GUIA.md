# Guía de Gasolina GT (para cualquier persona)

No hace falta saber nada de computación. Son dos pasos y se hacen una sola vez.

---

## Antes de empezar: dos cosas que conviene entender

**1. Hay archivos que se LEEN y archivos que se USAN.**

Los archivos que terminan en `.bat` son como un botón. Tú les haces **doble clic** y ellos trabajan.
Si en vez de eso se te abre una pantalla con letras de colores y numeritos al lado izquierdo, eso es
el "adentro" del botón. No sirve de nada tocarlo. Ciérralo sin guardar y vuelve a intentar el doble clic.

**2. El token es la llave de tu bot.**

Cuando creaste tu bot en Telegram, @BotFather te dio un texto largo parecido a esto:

```
123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Eso es el token. Es como la llave de tu casa: con eso, el programa puede escribir en tu canal.

- **Nunca** se lo mandes a nadie por chat.
- **Nunca** lo escribas dentro de un archivo.
- Solo lo pegas **una vez**, en la ventana negra que te lo pida.

Si alguna vez crees que alguien más lo vio, en Telegram le escribes a @BotFather `/revoke` y te da
una llave nueva. La vieja deja de servir.

---

## Paso 1 · Conectar tu bot

1. Abre la carpeta **Gasolina Gt** (está en tu carpeta de usuario, `C:\Users\darwi`).
2. Busca el archivo que se llama **Conectar bot**.
3. Haz **doble clic**.
4. Se abre una **ventana negra**. Eso está bien, así se ve.

La ventana te va a hacer tres preguntas. Nada más contestas:

**Pregunta 1: el token.**
Abre Telegram, entra al chat de @BotFather, busca el texto largo que te dio y cópialo.
Vuelve a la ventana negra y pégalo. Para pegar ahí se hace **clic derecho** (no funciona Ctrl+V).
Luego presiona Enter.

Si te dice *"Conectado con tu bot: Gasolina GT"*, vas bien.
Si te dice que no sirve, seguramente copiaste de más o de menos. Vuelve a copiarlo completo.

**Pregunta 2: el canal.**
Primero te va a recordar algo importante. En Telegram, entra a tu canal *Gasolina GT*, toca el nombre
arriba, entra a **Administradores**, toca **Agregar administrador**, busca tu bot y dale permiso de
**Publicar mensajes**. Guarda.

Después vuelve a la ventana negra y presiona Enter. Él busca tu canal solo.
Si lo encuentra, te pregunta si es ese. Escribes `si` y Enter.

**Pregunta 3: si quieres que trabaje solo.**
Escribes `si` y Enter.

Cuando termine, **mira tu canal de Telegram**. Debe haber llegado un mensaje que dice que ya está listo.
Si llegó, funcionó.

---

## Paso 2 · Que funcione con tu computadora apagada

Esto es lo que hace que no dependas de tener la PC prendida.

1. En la misma carpeta, busca **Publicar en internet**.
2. Doble clic.
3. Te va a pedir entrar a tu cuenta de GitHub. Es un sitio gratis donde va a vivir el programa.
   - Si no tienes cuenta, créala en https://github.com/signup y vuelve a empezar este paso.
4. Te da un **código de 8 letras** y te abre el navegador. Pega el código ahí y autoriza.
5. Vuelve a la ventana negra y espera. Él hace todo lo demás.

Al final te da tres direcciones. Guárdalas:

- La del **tablero**: es tu página web, la puedes abrir desde el celular y compartirla.
- La del **proyecto**: ahí vive el código.
- La de **corridas**: ahí puedes ver que está trabajando.

Desde ese momento, con tu computadora apagada:

- Cada hora, de lunes a viernes, revisa los precios y las noticias.
- Todos los días a las 7 de la mañana, publica el resumen en tu canal.

---

## Los demás botones (por si los necesitas)

| Archivo | Para qué sirve |
|---|---|
| **Gasolina GT** | Busca los precios de ahorita y te abre el tablero. |
| **Ver tablero** | Solo abre el tablero, sin buscar nada. |
| **Bot al instante** | El bot contesta al segundo. Solo mientras la ventana esté abierta. |
| **Automatizar** | Hace que tu propia PC trabaje sola. Solo sirve si la dejas prendida. |

---

## ¿Qué le puedo escribir al bot?

Abre Telegram, entra al chat de tu bot y escribe cualquiera de estas:

- `/hoy` — el resumen del día
- `/senal` — ¿lleno hoy o espero?
- `/precio Quetzaltenango` — el precio en tu departamento
- `/baratos` — dónde está más barata
- `/tanque 10` — cuánto te cuesta llenar 10 galones
- `/ayuda` — la lista completa

También le puedes escribir normal, como *"¿va a subir la gasolina?"* o *"Petén"*.

---

## Si algo sale mal

**Se abrió una pantalla con código en vez de la ventana negra.**
Ciérrala sin guardar. Haz clic derecho en el archivo y elige **Abrir**.

**La ventana negra se cierra sola muy rápido.**
Algo falló. Vuelve a abrirla y toma una foto de lo que dice antes de cerrarse.

**El mensaje de prueba no llegó al canal.**
Casi siempre es porque al bot le falta ser administrador del canal, o le falta el permiso de
*Publicar mensajes*. Revisa eso y vuelve a correr **Conectar bot**.

**Los precios se ven viejos.**
El sitio del Ministerio bloquea a los programas. El agente saca los precios de las noticias, que traen
los mismos números. Si quieres el dato oficial exacto, abre **Gasolina GT** en tu PC los martes.

---

## Lo que nunca hay que hacer

- No pegues el token dentro de ningún archivo.
- No le mandes el token a nadie, ni a mí.
- No borres la carpeta `config`, ahí está guardada tu llave.
