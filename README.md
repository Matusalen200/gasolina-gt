# ⛽ Gasolina GT

Te dice **dónde y cuándo llenar el tanque** en Guatemala, antes que los medios, con gráficas que se
entienden en el celular. Todo corre gratis en GitHub Actions + GitHub Pages: el agente vigila, el bot
publica, nadie toca nada.

- Tablero: `https://<usuario>.github.io/gasolina-gt/web/`
- Canal de Telegram: el bot publica cada día a las 7:00 am y responde `/senal` y `/precio <departamento>`.

## Qué hace

| Cada hora (lun–vie 7:00–15:00 GT) | Cada día 7:00 GT | Martes | Día 1 del mes |
|---|---|---|---|
| Busca el informe semanal del MEM y lo lee (`agente/mem.py`) y saca el **precio de hoy** de las noticias y comunicados del día (`agente/hoy.py`) | Genera el reporte en `data/reportes/AAAA-MM-DD.md` y el mensaje corto | Compara lo que publicó el MEM con lo que predijimos → `data/aciertos.json` | Excel mensual en `reportes/mensual-AAAA-MM.xlsx` |
| Baja gasolina EE.UU. (RBOB), petróleo (WTI) y dólar (`agente/mercado.py`) | Publica el mensaje en el canal de Telegram (`bot/telegram.py`) | | |
| Lee noticias y Claude las clasifica ALZA / BAJA / NEUTRAL (`agente/noticias.py`) | Recalcula la proyección a 4 semanas (`agente/proyeccion.py`) | | |
| Calcula la señal y el veredicto (`agente/senal.py`) | | | |

Todo se guarda como JSON en `data/` y el tablero (`web/`) los lee directo. Si un servicio externo falla,
el agente conserva el último dato bueno y lo anota en `data/log.txt`; nunca se rompe la corrida completa.

## La regla de la señal (explícita; Claude redacta, no decide)

```
c_gasolina = limitar(cambio_7d_%_RBOB  x 10, -60, +60)   # 6 % en una semana satura
c_dolar    = limitar(cambio_7d_%_USDGTQ x 20, -20, +20)  # 1 % de depreciación del quetzal = +20
c_noticias = limitar((noticias ALZA - noticias BAJA en 7 días) x 5, -20, +20)
puntaje    = limitar(c_gasolina + c_dolar + c_noticias, -100, +100)

puntaje >= +15  →  🔴 "Llena HOY"           (sube el martes)
puntaje <= -15  →  🟢 "Espera"              (baja el martes)
entre medio     →  🟡 "Llena esta semana"   (estable)

cambio estimado del martes (Q/gal) = cambio_7d_abs_RBOB (US$/gal) x tipo de cambio x 0.85, redondeado a Q0.05
```

El 0.85 es el traslado típico del precio internacional al surtidor en Guatemala. Los umbrales están en
`agente/senal.py`; los tests en `tests/test_senal.py` fijan el comportamiento.

**Acierto**: cada martes se toma la última señal antes del martes y se compara con el cambio real del precio
regular que publica el MEM (> +Q0.10 alza, < −Q0.10 baja, si no estable). El tablero muestra el % de acierto
con 4 o más martes evaluados; antes dice "calibrando". Si el informe del MEM de esa semana no se pudo
leer, la semana queda como "sin dato" y no cuenta.

## Proyección a 4 semanas (honestidad primero)

`agente/proyeccion.py` ajusta una regresión lineal (mínimos cuadrados, sin numpy) del precio MEM de la
semana *t* contra RBOB×USD/GTQ y WTI de la semana *t−1* y RBOB×USD/GTQ de *t−2*. Se valida walk-forward:
para cada semana se entrena con las anteriores y se predice esa semana; el error absoluto medio (MAE) se
guarda en `data/proyeccion.json` y se muestra en el tablero.

**Estado actual: calibrando.** Solo tenemos 7 semanas de historial del MEM (diciembre 2025 a enero 2026,
sacadas del informe archivado) y el modelo exige 10. Hasta entonces la proyección es un traslado simple
del cambio de la gasolina en EE.UU. sobre el último precio MEM conocido, con rango ±Q0.75×√semanas.
No hay error medio que reportar todavía; cuando lo haya se escribe aquí y en el tablero, sea bueno o malo.

## El precio de hoy (`agente/hoy.py`)

Cada hora lee los feeds de Prensa Libre, La Hora, TV Azteca Guatemala, Emisoras Unidas, República, la Diaco
y Google News (Guatemala), toma las notas de los últimos 30 días que hablan de combustibles, baja el texto y
extrae los precios del galón (súper, regular, diésel). Cada observación se guarda con hora, fuente, enlace y
tipo: `promedio` (monitoreo o referencia del MEM), `estacion` (gasolineras concretas), `tope` (precio máximo
legal del Congreso). Por día se toma la mediana del mejor tipo disponible. Con `ANTHROPIC_API_KEY` la
extracción la hace Claude leyendo la nota; sin clave, expresiones regulares (más ruidosas). El tablero muestra
el último valor, el cambio contra el día anterior y una gráfica con pestañas de 1 semana a 1 año que une esta
serie diaria con el historial semanal del MEM.

## El problema del MEM (y qué hacemos)

Desde mediados de 2026 `mem.gob.gt` está detrás de un reto de Cloudflare que bloquea cualquier descarga
automática (curl, Python, GitHub Actions e incluso el crawler de Wayback devuelven 403). No intentamos
saltarlo. `agente/mem.py` prueba en orden:

1. La página oficial de precios (por si vuelve a abrirse).
2. URLs adivinadas por fecha con los nombres que usa el MEM
   (`INFORME-EJECUTIVO-DE-PRECIOS-DE-LOS-COMBUSTIBLES-AAAA-MM-DD.pdf`,
   `Precios-de-referencia-departamental-semanal-AAAA-MM-DD.pdf`, etc.).
3. El índice de Wayback Machine del mes actual y el anterior.
4. **Carpeta manual**: cualquier PDF que pongas en `data/pdf/` o una URL en el campo `pdf_url` de
   *Actions → Agente Gasolina GT → Run workflow*. Bajar el PDF desde el navegador y subirlo toma un minuto.

Si nada funciona se conserva el último informe leído y el tablero lo avisa. Los parsers están probados
con dos PDFs reales del 19/01/2026 en `tests/fixtures/`.

## Estructura

```
agente/       agente.py (orquestador), comun.py, mem.py, hoy.py, mercado.py, noticias.py, senal.py, reporte.py, proyeccion.py
bot/          plantillas.py (edita los textos aquí), telegram.py
web/          index.html, app.js, estilos.css  (JS vanilla + Chart.js desde CDN)
data/         JSON que produce el agente (precios, departamentos, mercado, noticias, señal, aciertos, proyección, reportes/)
config/       plan.json (Plus)
reportes/     mensual.py y los Excel generados
docs/         whatsapp.md (evaluación de opciones)
tests/        pytest con fixtures reales
scripts/      publicar.ps1 (crear repo, secrets, Pages y primera corrida)
.github/workflows/agente.yml
```

## Correr en tu máquina

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...                     # opcional: sin clave usa reglas en vez de Claude
python agente/agente.py --semilla tests/fixtures     # carga los PDFs de ejemplo
python agente/agente.py                              # corrida horaria completa
python agente/agente.py --diario                     # + reporte, proyección, Telegram
python agente/agente.py --solo noticias              # una etapa
python bot/telegram.py "/precio Petén"               # probar una respuesta del bot sin token
python -m pytest tests -q
python -m http.server 8765                           # abre http://127.0.0.1:8765/web/
```

## Publicar en GitHub (una vez)

```powershell
gh auth login
.\scripts\publicar.ps1 -Nombre gasolina-gt -AnthropicKey "sk-ant-..." -TelegramToken "123:abc" -TelegramChannel "@gasolinagt"
```

Crea el repo público (Actions ilimitado), sube los secrets `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHANNEL_ID`, activa Pages (rama `main`, raíz) y lanza la primera corrida. El bot de Telegram se
crea con @BotFather; agrégalo como administrador del canal.

## Cobro: gratis por defecto

`config/plan.json`:

```json
{"plus_activo": false, "precio_mensual_q": 0, "moneda": "GTQ", "link_pago": ""}
```

Mientras `plus_activo` sea `false` no se menciona ningún pago en el tablero, el bot ni los reportes.
Al ponerlo en `true` con un precio y un link, el tablero muestra "Plus para flotillas" y el bot responde
`/plus` con el mismo texto. No hay pasarela de pago integrada, solo el link.

## Estilo de mensajes

Máximo 5 líneas. Primera línea = la decisión. Un solo emoji al inicio (🔴 alza, 🟢 baja, 🟡 estable).
Sin tickers ni porcentajes técnicos: "petróleo", "gasolina en EE.UU.". Las plantillas viven en
`bot/plantillas.py`.

## Modelo de Claude

Clasificación de noticias y redacción de la razón usan `claude-opus-5` (cambia con la variable
`CLAUDE_MODELO`). Sin `ANTHROPIC_API_KEY` el agente funciona igual con reglas por palabras clave y lo
marca en cada noticia (`clasificado_por: "reglas"`).
