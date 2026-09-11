/* Tablero Gasolina GT. JS vanilla + Chart.js. Lenguaje llano; lo técnico va en "Para curiosos". */
(function () {
  "use strict";

  const RUTA_DATOS = "../data/";
  const COLOR = {
    alza: css("--alza"), baja: css("--baja"), estable: css("--estable"),
    acento: css("--acento"), resalte: css("--resalte"), suave: css("--texto-suave"), texto: css("--texto"), borde: css("--borde"),
  };
  const NOMBRE_PRODUCTO = { superior: "Súper", regular: "Regular", diesel: "Diésel" };
  const SEMANA = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  const EMOJI = { alza: "🔴", baja: "🟢", estable: "🟡" };

  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function $(id) { return document.getElementById(id); }
  function q(n) { return n == null ? "–" : "Q" + Number(n).toFixed(2); }
  function fechaCorta(iso) {
    if (!iso) return "";
    const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
    return d.toLocaleDateString("es-GT", { day: "numeric", month: "long" });
  }
  async function cargar(nombre) {
    try {
      const r = await fetch(RUTA_DATOS + nombre + "?t=" + Math.floor(Date.now() / 300000));
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento */ } }
  function recordar(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  Chart.defaults.color = COLOR.suave;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 13;

  /* ---------------------------------------------------------------- 1. veredicto */
  function pintarVeredicto(senal, ultimoReporte) {
    const sec = $("veredicto");
    if (!senal || senal.puntaje == null) return;
    sec.classList.add(senal.tendencia || "estable");
    sec.querySelector(".semaforo").textContent = senal.emoji || "🟡";
    const frases = { alza: "Llena HOY, va a subir", baja: "Espera, va a bajar", estable: "Sin apuro, se queda igual" };
    sec.querySelector(".decision").textContent = frases[senal.tendencia] || senal.veredicto || "";
    sec.querySelector(".explicacion").textContent = senal.razon || "";
    const cambio = sec.querySelector(".cambio");
    if (senal.cambio_estimado_texto) { cambio.hidden = false; cambio.textContent = senal.cambio_estimado_texto.replace(/^El martes/, "El martes " + fechaCorta(senal.proximo_martes)); }
    if (ultimoReporte && ultimoReporte.mensaje) {
      const btn = $("btnCompartir");
      btn.hidden = false;
      btn.addEventListener("click", () => {
        const texto = ultimoReporte.mensaje + "\n\nMás en " + location.href.split("?")[0];
        window.open("https://wa.me/?text=" + encodeURIComponent(texto), "_blank", "noopener");
      });
    }
    if (ultimoReporte && ultimoReporte.fecha) $("subtitulo").textContent = "Actualizado el " + fechaCorta(ultimoReporte.fecha) + ".";
  }

  /* ---------------------------------------------------------------- 2. precios */
  function pintarPrecios(precios) {
    if (!precios || !precios.autoservicio) return;
    const a = precios.autoservicio, c = precios.cambio_semanal || {};
    $("precios").hidden = false;
    $("preciosFecha").textContent = "Precio de referencia del MEM en la ciudad, del " + fechaCorta(precios.fecha_monitoreo) + ". En tu gasolinera puede variar unos centavos.";
    for (const k of ["superior", "regular", "diesel"]) {
      const K = k[0].toUpperCase() + k.slice(1);
      $("p" + K).textContent = q(a[k]);
      const el = $("c" + K);
      if (c[k] != null) {
        el.textContent = c[k] > 0 ? "subió Q" + c[k].toFixed(2) : c[k] < 0 ? "bajó Q" + Math.abs(c[k]).toFixed(2) : "igual que la semana pasada";
        el.className = "cambio-chico " + (c[k] > 0 ? "up" : c[k] < 0 ? "down" : "");
      }
    }
    const dias = (Date.now() - new Date(precios.fecha_monitoreo + "T12:00:00")) / 864e5;
    if (dias > 10) {
      $("preciosAviso").hidden = false;
      $("preciosAviso").textContent = "Ojo: estos precios son del " + fechaCorta(precios.fecha_monitoreo) + ". El sitio del MEM no nos deja bajar el informe nuevo; seguimos intentando cada hora.";
    }
  }

  /* ---------------------------------------------------------------- 3. dónde (lista simple) */
  function pintarDeptos(deptosOficial, deptosHoy) {
    const deptos = (deptosHoy && deptosHoy.departamentos && deptosHoy.departamentos.length) ? deptosHoy : deptosOficial;
    if (!deptos || !deptos.departamentos || !deptos.departamentos.length) return;
    $("donde").hidden = false;
    const fecha = deptos.fecha || deptos.vigencia_inicio;
    $("dondeFecha").textContent = deptos.estimado
      ? "Dato de hoy (" + fechaCorta(fecha) + "). Es un cálculo: el precio de la capital hoy más lo que suele costar de más en cada departamento, según la última tabla oficial del MEM (" + fechaCorta(deptos.tabla_oficial_fecha) + ")."
      : "Tabla oficial del MEM, vigente desde el " + fechaCorta(fecha) + ".";
    const sel = $("selDepto");
    const nombres = deptos.departamentos.map(d => d.departamento).sort((a, b) => a.localeCompare(b, "es"));
    for (const n of nombres) { const o = document.createElement("option"); o.value = n; o.textContent = n; sel.appendChild(o); }
    const guardado = recordar("gasolinagt.depto");
    if (guardado && nombres.includes(guardado)) sel.value = guardado;
    let producto = recordar("gasolinagt.producto") || "regular";
    if (!NOMBRE_PRODUCTO[producto]) producto = "regular";
    let todos = false;

    function dibujar() {
      const filas = deptos.departamentos.slice().sort((a, b) => a[producto] - b[producto]);
      const mio = sel.value;
      const barato = filas[0], caro = filas[filas.length - 1];
      const nombre = NOMBRE_PRODUCTO[producto].toLowerCase();
      $("dondeBarato").textContent = "Lo más barato: " + barato.departamento + ", " + q(barato[producto]) + " el galón de " + nombre + ". Lo más caro: " + caro.departamento + ", " + q(caro[producto]) + ".";
      const mioEl = $("dondeMio");
      if (mio) {
        const d = filas.find(x => x.departamento === mio);
        const pos = filas.indexOf(d) + 1;
        const dif = d[producto] - barato[producto];
        mioEl.hidden = false;
        mioEl.innerHTML = "En <b>" + mio + "</b> el galón de " + nombre + " cuesta <b>" + q(d[producto]) + "</b> hoy. " +
          (pos === 1 ? "¡Es el más barato del país! 🎉" : dif < 0.3 ? "Casi igual que lo más barato." : "Pagas Q" + dif.toFixed(2) + " más que en " + barato.departamento + ".");
      } else {
        mioEl.hidden = true;
      }
      const lista = $("listaDeptos");
      lista.innerHTML = "";
      const mioFila = mio ? filas.find(x => x.departamento === mio) : null;
      const mostrar = todos ? filas : filas.slice(0, 5).concat(mioFila && filas.indexOf(mioFila) >= 5 ? [mioFila] : []);
      for (const d of mostrar) {
        const li = document.createElement("li");
        const pos = filas.indexOf(d) + 1;
        if (d.departamento === mio) li.className = "mio";
        li.innerHTML = "<span><span class='pos'>" + pos + ".</span>" + d.departamento + (pos === 1 ? " 🏆" : "") + "</span><b>" + q(d[producto]) + "</b>";
        lista.appendChild(li);
      }
      $("btnTodos").textContent = todos ? "Ver solo los más baratos" : "Ver los " + filas.length + " departamentos";
    }
    $("btnTodos").addEventListener("click", () => { todos = !todos; dibujar(); });
    document.querySelectorAll("#chipsProducto button").forEach(b => {
      b.classList.toggle("activo", b.dataset.p === producto);
      b.addEventListener("click", () => {
        producto = b.dataset.p; guardar("gasolinagt.producto", producto);
        document.querySelectorAll("#chipsProducto button").forEach(x => x.classList.toggle("activo", x === b));
        dibujar();
      });
    });
    sel.addEventListener("change", () => { guardar("gasolinagt.depto", sel.value); dibujar(); });
    dibujar();
  }

  /* ---------------------------------------------------------------- 4. tira de días */
  function pintarTira(historial) {
    if (!historial || !historial.length) return;
    $("cuando").hidden = false;
    const porFecha = {};
    for (const h of historial) porFecha[h.fecha] = h;
    const hoy = new Date(); hoy.setHours(12, 0, 0, 0);
    const tira = $("tiraDias");
    for (let i = 13; i >= 0; i--) {
      const d = new Date(hoy); d.setDate(hoy.getDate() - i);
      const iso = d.toISOString().slice(0, 10);
      const h = porFecha[iso];
      const div = document.createElement("div");
      div.className = "dia" + (d.getDay() === 2 ? " martes" : "");
      div.innerHTML = "<div class='punto'>" + (h ? EMOJI[h.tendencia] || "🟡" : "·") + "</div>" + SEMANA[d.getDay()] + " " + d.getDate();
      div.title = h ? h.veredicto : "sin dato";
      tira.appendChild(div);
    }
  }

  /* ---------------------------------------------------------------- 5. noticias en frases */
  function pintarNoticias(datos, senal) {
    if (!datos || !datos.noticias || !datos.noticias.length) return;
    const lista = $("listaNoticias");
    // Primero las que mueven el precio; entre ellas, las que ya están en español (o traducidas por Claude).
    const puntaje = n => (n.etiqueta !== "NEUTRAL" ? 2 : 0) + (n.idioma === "es" || n.titulo_es ? 1 : 0);
    const mostrar = datos.noticias.slice(0, 20).sort((a, b) => puntaje(b) - puntaje(a)).slice(0, 3);
    $("noticias").hidden = false;
    for (const n of mostrar) {
      const div = document.createElement("div"); div.className = "noticia";
      const p = document.createElement("p"); p.className = "frase";
      const prefijo = n.etiqueta === "ALZA" ? "🔴 Esto hace que suba: " : n.etiqueta === "BAJA" ? "🟢 Esto ayuda a que baje: " : "🟡 Para saber: ";
      const a = document.createElement("a"); a.href = n.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = n.titulo_es || n.titulo;
      p.appendChild(document.createTextNode(prefijo)); p.appendChild(a);
      if (!n.titulo_es && n.idioma !== "es") { const en = document.createElement("span"); en.className = "meta"; en.textContent = " (en inglés)"; p.appendChild(en); }
      const meta = document.createElement("p"); meta.className = "meta";
      meta.textContent = (n.razon && n.clasificado_por !== "reglas" ? n.razon + " · " : "") + n.fuente + " · " + fechaCorta(n.fecha);
      div.appendChild(p); div.appendChild(meta); lista.appendChild(div);
    }
  }

  /* ---------------------------------------------------------------- 6. aciertos */
  function pintarAciertos(a) {
    if (!a) return;
    $("aciertos").hidden = false;
    if (a.estado !== "ok" || !a.total) {
      $("aciertoValor").textContent = "Estamos empezando a contar.";
      $("aciertoDetalle").textContent = "Cada martes vemos si adivinamos. Llevamos " + (a.total || 0) + " de 4 semanas para darte un número.";
    } else {
      $("aciertoValor").textContent = "Acertamos " + a.aciertos + " de " + a.total + " semanas (" + a.porcentaje + " %).";
      $("aciertoDetalle").textContent = "Acierto = dijimos que subía, bajaba o seguía igual, y el martes pasó justo eso.";
    }
  }

  /* ---------------------------------------------------------------- 7. plus */
  function pintarPlus(plan) {
    if (!plan || !plan.plus_activo || !plan.precio_mensual_q) return;
    $("plus").hidden = false;
    $("plusTexto").textContent = "Alertas para tu flotilla, reporte mensual en Excel y proyección a 4 semanas por " + plan.moneda + " " + plan.precio_mensual_q + " al mes.";
    if (plan.link_pago) $("plusLink").href = plan.link_pago; else $("plusLink").hidden = true;
  }

  /* ---------------------------------------------------------------- 8. curiosos */
  function pintarProyeccion(p, historial) {
    if (!p || !p.semanas || !p.semanas.length) return;
    $("proyeccion").hidden = false;
    $("proyeccionNota").textContent = p.nota || "";
    const pasado = (historial || []).slice(-8);
    const etiquetas = pasado.map(h => fechaCorta(h.fecha)).concat(p.semanas.map(s => fechaCorta(s.fecha)));
    const nulos = pasado.map(() => null);
    new Chart($("graficaProyeccion").getContext("2d"), {
      type: "line",
      data: {
        labels: etiquetas,
        datasets: [
          { label: "Regular según el MEM", data: pasado.map(h => h.regular).concat(p.semanas.map(() => null)), borderColor: COLOR.acento, backgroundColor: COLOR.acento, tension: 0.3, pointRadius: 3 },
          { label: "Lo que esperamos", data: nulos.concat(p.semanas.map(s => s.regular)), borderColor: COLOR.resalte, borderDash: [6, 4], tension: 0.3, pointRadius: 3 },
          { label: "Rango alto", data: nulos.concat(p.semanas.map(s => s.rango_alto)), borderColor: "transparent", backgroundColor: "rgba(255,140,26,0.18)", fill: "+1", pointRadius: 0 },
          { label: "Rango bajo", data: nulos.concat(p.semanas.map(s => s.rango_bajo)), borderColor: "transparent", pointRadius: 0 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, spanGaps: false,
        plugins: { legend: { labels: { filter: i => i.text !== "Rango bajo" && i.text !== "Rango alto", boxWidth: 12 } }, tooltip: { callbacks: { label: c => " " + c.dataset.label + ": " + q(c.raw) } } },
        scales: { y: { grid: { color: COLOR.borde }, ticks: { callback: v => "Q" + v } }, x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0 } } },
      },
    });
  }

  function pintarMercado(m) {
    if (!m || !m.ultimo) return;
    $("mercado").hidden = false;
    const nombres = { "RB=F": "Gasolina en EE.UU. (US$ por galón)", "CL=F": "Petróleo (US$ por barril)", "GTQ=X": "Dólar (quetzales por US$)" };
    const lista = $("listaMercado");
    for (const [sym, u] of Object.entries(m.ultimo)) {
      if (!u || u.precio == null) continue;
      const fila = document.createElement("div"); fila.className = "fila";
      const c = u.cambio_7d_pct;
      fila.innerHTML = "<span>" + (nombres[sym] || sym) + "</span><span><b>" + Number(u.precio).toFixed(sym === "GTQ=X" ? 3 : 2) + "</b> <span class='cambio-chico " + (c > 0 ? "up" : c < 0 ? "down" : "") + "'>" + (c == null ? "" : (c > 0 ? "+" : "") + c.toFixed(1) + " %") + "</span></span>";
      lista.appendChild(fila);
    }
    const serie = (m.series && m.series["RB=F"]) || [];
    if (!serie.length) return;
    const porDia = {};
    for (const p of serie) porDia[p.t.slice(0, 10)] = p.p;
    const dias = Object.keys(porDia).sort().slice(-30);
    new Chart($("graficaMercado").getContext("2d"), {
      type: "line",
      data: { labels: dias.map(d => fechaCorta(d)), datasets: [{ label: "Gasolina en EE.UU., cierre diario", data: dias.map(d => porDia[d]), borderColor: COLOR.acento, tension: 0.3, pointRadius: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 12 } } }, scales: { y: { grid: { color: COLOR.borde } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 5, maxRotation: 0 } } } },
    });
  }

  function pintarDetalleSenal(s) {
    if (!s || !s.componentes) return;
    $("detalleSenal").hidden = false;
    const lista = $("listaSenal");
    const filas = [
      ["Puntaje total (−100 a +100)", (s.puntaje > 0 ? "+" : "") + s.puntaje],
      ["Aporte de la gasolina en EE.UU.", s.componentes.gasolina_eeuu],
      ["Aporte del dólar", s.componentes.dolar],
      ["Aporte de las noticias", s.componentes.noticias],
      ["Noticias de la semana", s.detalle.noticias_alza_7d + " al alza · " + s.detalle.noticias_baja_7d + " a la baja"],
      ["Redactado por", s.redactado_por || "plantilla"],
    ];
    for (const [k, v] of filas) { const f = document.createElement("div"); f.className = "fila"; f.innerHTML = "<span>" + k + "</span><b>" + v + "</b>"; lista.appendChild(f); }
  }

  /* ---------------------------------------------------------------- arranque */
  async function iniciar() {
    const [precios, deptos, senal, historialSenal, noticias, aciertos, proyeccion, mercado, plan, ultimoReporte, precioHist] = await Promise.all([
      cargar("precios.json"), cargar("departamentos.json"), cargar("senal.json"), cargar("senal_historial.json"),
      cargar("noticias.json"), cargar("aciertos.json"), cargar("proyeccion.json"), cargar("mercado_horario.json"),
      cargar("../config/plan.json"), cargar("reportes/ultimo.json"), cargar("precios_historial.json"),
    ]);
    const precioHoy = await cargar("precio_hoy.json");
    const deptosHoy = await cargar("departamentos_hoy.json");
    pintarVeredicto(senal, ultimoReporte);
    if (window.pintarPanelPrecio) window.pintarPanelPrecio(precioHoy, precios, precioHist); else pintarPrecios(precios);
    pintarDeptos(deptos, deptosHoy);
    pintarTira(historialSenal);
    pintarNoticias(noticias, senal);
    pintarAciertos(aciertos);
    pintarPlus(plan);
    pintarProyeccion(proyeccion, precioHist);
    pintarMercado(mercado);
    pintarDetalleSenal(senal);
    const act = (senal && senal.actualizado) || (precios && precios.actualizado);
    if (act) $("pie").textContent = "Última revisión: " + new Date(act).toLocaleString("es-GT", { dateStyle: "long", timeStyle: "short" }) + ".";
    if (location.hostname.endsWith("github.io")) {
      const partes = location.pathname.split("/").filter(Boolean);
      $("linkRepo").href = "https://github.com/" + location.hostname.split(".")[0] + "/" + (partes[0] || "");
    }
  }
  iniciar();
})();
