/* Tablero Gasolina GT. JS vanilla + Chart.js. Cada sección se muestra solo si existe su archivo de datos. */
(function () {
  "use strict";

  const RUTA_DATOS = "../data/";
  const COLOR = {
    alza: css("--alza"), baja: css("--baja"), estable: css("--estable"),
    acento: css("--acento"), resalte: css("--resalte"), suave: css("--texto-suave"), texto: css("--texto"), borde: css("--borde"),
  };
  const NOMBRE_PRODUCTO = { superior: "Súper", regular: "Regular", diesel: "Diésel" };
  const SEMANA = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function $(id) { return document.getElementById(id); }
  function q(n) { return n == null ? "–" : "Q" + Number(n).toFixed(2); }
  function fechaCorta(iso) {
    if (!iso) return "";
    const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
    return d.toLocaleDateString("es-GT", { day: "numeric", month: "short", year: "numeric" });
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

  /* ---------------------------------------------------------------- veredicto */
  function pintarVeredicto(senal, ultimoReporte) {
    const sec = $("veredicto");
    if (!senal || senal.puntaje == null) return;
    sec.classList.add(senal.tendencia || "estable");
    sec.querySelector(".semaforo").textContent = senal.emoji || "🟡";
    sec.querySelector(".decision").textContent = senal.veredicto || "Calibrando…";
    sec.querySelector(".razon").textContent = senal.razon || "";
    const p = sec.querySelector(".puntaje");
    p.hidden = false;
    p.textContent = "Puntaje " + (senal.puntaje > 0 ? "+" : "") + senal.puntaje + " · " + (senal.cambio_estimado_texto || "");
    if (ultimoReporte && ultimoReporte.fecha) $("subtitulo").textContent = "Reporte del " + fechaCorta(ultimoReporte.fecha) + ", 7:00 am.";
  }

  /* ---------------------------------------------------------------- precios */
  function pintarPrecios(precios) {
    if (!precios || !precios.autoservicio) return;
    const a = precios.autoservicio, c = precios.cambio_semanal || {};
    $("precios").hidden = false;
    $("preciosFecha").textContent = "Monitoreo del MEM: " + fechaCorta(precios.fecha_monitoreo) + " · " + (precios.fuente || "");
    for (const k of ["superior", "regular", "diesel"]) {
      const K = k[0].toUpperCase() + k.slice(1);
      $("p" + K).textContent = q(a[k]);
      const el = $("c" + K);
      if (c[k] != null) {
        el.textContent = (c[k] > 0 ? "▲ +" : c[k] < 0 ? "▼ " : "= ") + "Q" + Math.abs(c[k]).toFixed(2) + " vs. semana pasada";
        el.className = "cambio " + (c[k] > 0 ? "up" : c[k] < 0 ? "down" : "");
      }
    }
    const dias = (Date.now() - new Date(precios.fecha_monitoreo + "T12:00:00")) / 864e5;
    if (dias > 10) {
      $("preciosAviso").hidden = false;
      $("preciosAviso").textContent = "Ojo: el último informe del MEM que pudimos leer es del " + fechaCorta(precios.fecha_monitoreo) + ". El sitio del MEM bloquea las descargas automáticas; el agente sigue intentando cada hora.";
    }
  }

  /* ---------------------------------------------------------------- dónde */
  let graficaDeptos = null;
  function pintarDeptos(deptos) {
    if (!deptos || !deptos.departamentos || !deptos.departamentos.length) return;
    $("donde").hidden = false;
    $("dondeFecha").textContent = "Precios de referencia MEM, cabeceras departamentales, vigencia " + fechaCorta(deptos.vigencia_inicio) + " al " + fechaCorta(deptos.vigencia_fin) + ".";
    const sel = $("selDepto");
    const nombres = deptos.departamentos.map(d => d.departamento).sort((a, b) => a.localeCompare(b, "es"));
    for (const n of nombres) { const o = document.createElement("option"); o.value = n; o.textContent = n; sel.appendChild(o); }
    const guardado = recordar("gasolinagt.depto");
    if (guardado && nombres.includes(guardado)) sel.value = guardado;
    let producto = recordar("gasolinagt.producto") || "regular";
    if (!NOMBRE_PRODUCTO[producto]) producto = "regular";

    function dibujar() {
      const filas = deptos.departamentos.slice().sort((a, b) => a[producto] - b[producto]);
      const mio = sel.value;
      const etiquetas = filas.map(d => d.departamento);
      const valores = filas.map(d => d[producto]);
      const colores = filas.map(d => d.departamento === mio ? COLOR.resalte : COLOR.acento);
      const min = Math.min(...valores), max = Math.max(...valores);
      const ctx = $("graficaDeptos").getContext("2d");
      if (graficaDeptos) graficaDeptos.destroy();
      graficaDeptos = new Chart(ctx, {
        type: "bar",
        data: { labels: etiquetas, datasets: [{ data: valores, backgroundColor: colores, borderRadius: 4, barPercentage: 0.8, categoryPercentage: 0.9 }] },
        options: {
          indexAxis: "y", responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: c => " " + q(c.raw) + " por galón" } },
          },
          scales: {
            x: { min: Math.floor(min - 0.5), max: Math.ceil(max + 0.3), grid: { color: COLOR.borde }, ticks: { callback: v => "Q" + v } },
            y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 12 } } },
          },
        },
        plugins: [{
          id: "valores",
          afterDatasetsDraw(chart) {
            const { ctx } = chart; ctx.save(); ctx.font = "600 11px " + Chart.defaults.font.family; ctx.textBaseline = "middle"; ctx.fillStyle = COLOR.texto;
            chart.getDatasetMeta(0).data.forEach((b, i) => ctx.fillText(valores[i].toFixed(2), b.x + 4, b.y));
            ctx.restore();
          },
        }],
      });
      const barato = filas[0], caro = filas[filas.length - 1];
      let resumen = "Más barato: " + barato.departamento + " (" + q(barato[producto]) + "). Más caro: " + caro.departamento + " (" + q(caro[producto]) + ").";
      if (mio) {
        const d = filas.find(x => x.departamento === mio);
        const pos = filas.indexOf(d) + 1;
        resumen += " " + mio + ": " + q(d[producto]) + ", puesto " + pos + " de " + filas.length + (pos === 1 ? ", ¡el más barato!" : ", Q" + (d[producto] - barato[producto]).toFixed(2) + " más que el más barato.");
      }
      $("dondeResumen").textContent = resumen;
    }
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

  /* ---------------------------------------------------------------- cuándo (señal 14 días) */
  function pintarSenal(historial) {
    if (!historial || !historial.length) return;
    const filas = historial.slice(-14);
    $("cuando").hidden = false;
    const etiquetas = filas.map(f => { const d = new Date(f.fecha + "T12:00:00"); return (d.getDay() === 2 ? "▲ " : "") + SEMANA[d.getDay()] + " " + d.getDate(); });
    const colores = filas.map(f => f.puntaje >= 15 ? COLOR.alza : f.puntaje <= -15 ? COLOR.baja : COLOR.estable);
    new Chart($("graficaSenal").getContext("2d"), {
      type: "bar",
      data: { labels: etiquetas, datasets: [{ data: filas.map(f => f.puntaje), backgroundColor: colores, borderRadius: 4 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => " " + (c.raw > 0 ? "+" : "") + c.raw + " · " + (filas[c.dataIndex].veredicto || "") } } },
        scales: {
          y: { min: -100, max: 100, grid: { color: COLOR.borde }, ticks: { stepSize: 50 } },
          x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0, autoSkip: false } },
        },
      },
    });
  }

  /* ---------------------------------------------------------------- noticias */
  function pintarNoticias(datos) {
    if (!datos || !datos.noticias || !datos.noticias.length) return;
    $("noticias").hidden = false;
    const lista = $("listaNoticias");
    for (const n of datos.noticias.slice(0, 5)) {
      const div = document.createElement("div"); div.className = "noticia";
      const et = document.createElement("span"); et.className = "etiqueta " + n.etiqueta; et.textContent = n.etiqueta === "ALZA" ? "🔴 SUBE" : n.etiqueta === "BAJA" ? "🟢 BAJA" : "🟡 NEUTRAL";
      const cuerpo = document.createElement("div");
      const a = document.createElement("a"); a.href = n.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = n.titulo;
      const meta = document.createElement("div"); meta.className = "meta"; meta.textContent = (n.razon ? n.razon + " · " : "") + n.fuente + " · " + fechaCorta(n.fecha);
      cuerpo.appendChild(a); cuerpo.appendChild(meta); div.appendChild(et); div.appendChild(cuerpo); lista.appendChild(div);
    }
  }

  /* ---------------------------------------------------------------- aciertos */
  function pintarAciertos(a) {
    if (!a) return;
    $("aciertos").hidden = false;
    if (a.estado !== "ok" || !a.total) {
      $("aciertoValor").textContent = "Calibrando";
      $("aciertoDetalle").textContent = "Necesitamos al menos 4 martes de historial para medir. Llevamos " + (a.total || 0) + ".";
    } else {
      $("aciertoValor").textContent = a.porcentaje + " % de aciertos";
      $("aciertoDetalle").textContent = a.aciertos + " de " + a.total + " semanas: la dirección que anunciamos coincidió con lo que publicó el MEM el martes.";
    }
  }

  /* ---------------------------------------------------------------- proyección */
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
          { label: "Regular MEM", data: pasado.map(h => h.regular).concat(p.semanas.map(() => null)), borderColor: COLOR.acento, backgroundColor: COLOR.acento, tension: 0.3, pointRadius: 3 },
          { label: "Proyección", data: nulos.concat(p.semanas.map(s => s.regular)), borderColor: COLOR.resalte, borderDash: [6, 4], tension: 0.3, pointRadius: 3 },
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

  /* ---------------------------------------------------------------- mercado */
  function pintarMercado(m) {
    if (!m || !m.ultimo) return;
    $("mercado").hidden = false;
    const nombres = { "RB=F": "Gasolina EE.UU. (US$/gal)", "CL=F": "Petróleo WTI (US$/barril)", "GTQ=X": "Dólar (Q por US$)" };
    const lista = $("listaMercado");
    for (const [sym, u] of Object.entries(m.ultimo)) {
      if (!u || u.precio == null) continue;
      const fila = document.createElement("div"); fila.className = "fila";
      const c = u.cambio_7d_pct;
      fila.innerHTML = "<span>" + (nombres[sym] || sym) + "</span><span><b>" + Number(u.precio).toFixed(sym === "GTQ=X" ? 3 : 2) + "</b> <span class='cambio " + (c > 0 ? "up" : c < 0 ? "down" : "") + "'>" + (c == null ? "" : (c > 0 ? "+" : "") + c.toFixed(1) + " %") + "</span></span>";
      lista.appendChild(fila);
    }
    const serie = (m.series && m.series["RB=F"]) || [];
    if (!serie.length) return;
    const porDia = {};
    for (const p of serie) porDia[p.t.slice(0, 10)] = p.p;
    const dias = Object.keys(porDia).sort().slice(-30);
    new Chart($("graficaMercado").getContext("2d"), {
      type: "line",
      data: { labels: dias.map(d => fechaCorta(d)), datasets: [{ label: "Gasolina EE.UU. (RBOB), cierre diario", data: dias.map(d => porDia[d]), borderColor: COLOR.acento, tension: 0.3, pointRadius: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { boxWidth: 12 } } }, scales: { y: { grid: { color: COLOR.borde } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 5, maxRotation: 0 } } } },
    });
  }

  /* ---------------------------------------------------------------- plus */
  function pintarPlus(plan) {
    if (!plan || !plan.plus_activo || !plan.precio_mensual_q) return;
    $("plus").hidden = false;
    $("plusTexto").textContent = "Alertas por flotilla, reporte mensual en Excel y proyección a 4 semanas por " + plan.moneda + " " + plan.precio_mensual_q + " al mes.";
    if (plan.link_pago) $("plusLink").href = plan.link_pago; else $("plusLink").hidden = true;
  }

  /* ---------------------------------------------------------------- arranque */
  async function iniciar() {
    const [precios, deptos, senal, historialSenal, noticias, aciertos, proyeccion, mercado, plan, ultimoReporte, precioHist] = await Promise.all([
      cargar("precios.json"), cargar("departamentos.json"), cargar("senal.json"), cargar("senal_historial.json"),
      cargar("noticias.json"), cargar("aciertos.json"), cargar("proyeccion.json"), cargar("mercado_horario.json"),
      cargar("../config/plan.json"), cargar("reportes/ultimo.json"), cargar("precios_historial.json"),
    ]);
    pintarVeredicto(senal, ultimoReporte);
    pintarPrecios(precios);
    pintarDeptos(deptos);
    pintarSenal(historialSenal);
    pintarNoticias(noticias);
    pintarAciertos(aciertos);
    pintarProyeccion(proyeccion, precioHist);
    pintarMercado(mercado);
    pintarPlus(plan);
    const act = (senal && senal.actualizado) || (precios && precios.actualizado);
    if (act) $("pie").textContent = "Última corrida del agente: " + new Date(act).toLocaleString("es-GT") + ".";
    if (location.hostname.endsWith("github.io")) {
      const partes = location.pathname.split("/").filter(Boolean);
      $("linkRepo").href = "https://github.com/" + location.hostname.split(".")[0] + "/" + (partes[0] || "");
    }
  }
  iniciar();
})();
