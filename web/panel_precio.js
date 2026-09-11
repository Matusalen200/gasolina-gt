/* Panel "precio de hoy" estilo Google Finance: número grande, cambio del día y gráfica con pestañas. */
(function () {
  "use strict";
  const NOMBRE = { superior: "Súper", regular: "Regular", diesel: "Diésel" };
  const RANGOS = { "1S": 7, "1M": 31, "3M": 92, "1A": 366 };
  let grafica = null;

  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function $(id) { return document.getElementById(id); }
  function q(n) { return n == null ? "–" : "Q" + Number(n).toFixed(2); }
  function fechaLarga(iso) {
    const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
    return d.toLocaleDateString("es-GT", { day: "numeric", month: "short" }) + (iso.length > 10 ? ", " + d.toLocaleTimeString("es-GT", { hour: "numeric", minute: "2-digit" }) : "");
  }
  function recordar(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* nada */ } }

  /** Une la serie diaria de medios con el historial semanal del MEM en una sola serie por producto. */
  function serieUnida(hoyDatos, historialMem, producto) {
    const puntos = {};
    for (const h of historialMem || []) if (h[producto] != null) puntos[h.fecha] = { v: h[producto], fuente: "MEM" };
    for (const d of (hoyDatos && hoyDatos.diario) || []) if (d[producto] != null) puntos[d.fecha] = { v: d[producto], fuente: "medios" };
    return Object.keys(puntos).sort().map(f => ({ fecha: f, valor: puntos[f].v, fuente: puntos[f].fuente }));
  }

  window.pintarPanelPrecio = function (hoyDatos, precios, historialMem) {
    const sec = $("precios");
    const ultimo = (hoyDatos && hoyDatos.ultimo) || {};
    const auto = (precios && precios.autoservicio) || {};
    if (!Object.keys(ultimo).length && !auto.regular) return;
    sec.hidden = false;
    let producto = recordar("gasolinagt.producto") || "regular";
    if (!NOMBRE[producto]) producto = "regular";
    let rango = recordar("gasolinagt.rango") || "1M";

    function pintar() {
      const u = ultimo[producto];
      const valor = u ? u.valor : auto[producto];
      const fecha = u ? u.fecha : precios.fecha_monitoreo;
      $("precioGrande").textContent = q(valor);
      $("precioProducto").textContent = NOMBRE[producto] + " · el galón en autoservicio";
      const c = hoyDatos && hoyDatos.cambio_dia && hoyDatos.cambio_dia[producto];
      const cambioEl = $("precioCambio");
      if (c && c.q != null) {
        const signo = c.q > 0 ? "▲ subió Q" : c.q < 0 ? "▼ bajó Q" : "= igual, Q";
        cambioEl.textContent = signo + Math.abs(c.q).toFixed(2) + " (" + (c.pct > 0 ? "+" : "") + c.pct.toFixed(1) + " %) desde el " + fechaLarga(c.vs_fecha);
        cambioEl.className = "precio-cambio " + (c.q > 0 ? "up" : c.q < 0 ? "down" : "");
      } else if (precios && precios.cambio_semanal && precios.cambio_semanal[producto] != null && !u) {
        const s = precios.cambio_semanal[producto];
        cambioEl.textContent = (s > 0 ? "▲ subió Q" : s < 0 ? "▼ bajó Q" : "= igual, Q") + Math.abs(s).toFixed(2) + " en la semana";
        cambioEl.className = "precio-cambio " + (s > 0 ? "up" : s < 0 ? "down" : "");
      } else {
        cambioEl.textContent = "Primer dato de hoy; mañana verás el cambio.";
        cambioEl.className = "precio-cambio";
      }
      $("precioFuente").textContent = u
        ? "Dato del " + fechaLarga(fecha) + " · " + u.fuente + (u.tipo === "estacion" ? " (precio en gasolineras)" : "")
        : "Informe del MEM del " + fechaLarga(fecha || "");
      if (u && u.url) { $("precioFuente").innerHTML += ' · <a href="' + u.url + '" target="_blank" rel="noopener">ver nota</a>'; }

      const otros = Object.keys(NOMBRE).filter(p => p !== producto).map(p => {
        const x = ultimo[p] ? ultimo[p].valor : auto[p];
        return NOMBRE[p] + " " + q(x);
      });
      $("precioOtros").textContent = otros.join(" · ");

      const tope = hoyDatos && hoyDatos.tope;
      const topeEl = $("precioTope");
      if (tope && tope[producto] != null) {
        topeEl.hidden = false;
        topeEl.textContent = "Precio tope aprobado por el Congreso: " + q(tope[producto]) + ". Cuando entre en vigor, ninguna gasolinera debería cobrar más.";
      } else { topeEl.hidden = true; }

      const serie = serieUnida(hoyDatos, historialMem, producto);
      const desde = new Date(); desde.setDate(desde.getDate() - RANGOS[rango]);
      let visible = serie.filter(s => new Date(s.fecha + "T12:00:00") >= desde);
      if (visible.length < 2) visible = serie.slice(-8);
      const hayHueco = visible.length >= 2 && (new Date(visible[visible.length - 1].fecha) - new Date(visible[0].fecha)) / 864e5 > RANGOS[rango] * 1.5;
      $("precioHueco").hidden = !hayHueco;
      const ctx = $("graficaPrecio").getContext("2d");
      if (grafica) grafica.destroy();
      const sube = visible.length >= 2 && visible[visible.length - 1].valor >= visible[0].valor;
      const color = sube ? css("--alza") : css("--baja");
      grafica = new Chart(ctx, {
        type: "line",
        data: {
          labels: visible.map(s => s.fecha),
          datasets: [
            { label: NOMBRE[producto], data: visible.map(s => s.valor), borderColor: color, backgroundColor: color + "22", fill: true, tension: 0.25, pointRadius: visible.length > 40 ? 0 : 3, pointBackgroundColor: color, borderWidth: 2.5 },
          ].concat(tope && tope[producto] != null ? [{ label: "Tope legal", data: visible.map(() => tope[producto]), borderColor: css("--texto-suave"), borderDash: [5, 5], pointRadius: 0, borderWidth: 1.5, fill: false }] : []),
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { title: items => fechaLarga(items[0].label), label: c => " " + c.dataset.label + ": " + q(c.raw) + (c.datasetIndex === 0 ? " (" + visible[c.dataIndex].fuente + ")" : "") } },
          },
          scales: {
            y: { grid: { color: css("--borde") }, ticks: { callback: v => "Q" + v, maxTicksLimit: 5 } },
            x: { grid: { display: false }, ticks: { maxTicksLimit: 4, maxRotation: 0, callback: (v, i) => { const d = new Date(visible[i].fecha + "T12:00:00"); return d.toLocaleDateString("es-GT", { day: "numeric", month: "short" }); } } },
          },
        },
      });
    }

    document.querySelectorAll("#chipsPrecio button").forEach(b => {
      b.classList.toggle("activo", b.dataset.p === producto);
      b.addEventListener("click", () => {
        producto = b.dataset.p; guardar("gasolinagt.producto", producto);
        document.querySelectorAll("#chipsPrecio button").forEach(x => x.classList.toggle("activo", x === b));
        document.querySelectorAll("#chipsProducto button").forEach(x => x.classList.toggle("activo", x.dataset.p === producto));
        pintar();
      });
    });
    document.querySelectorAll("#tabsRango button").forEach(b => {
      b.classList.toggle("activo", b.dataset.r === rango);
      b.addEventListener("click", () => {
        rango = b.dataset.r; guardar("gasolinagt.rango", rango);
        document.querySelectorAll("#tabsRango button").forEach(x => x.classList.toggle("activo", x === b));
        pintar();
      });
    });
    pintar();
  };
})();
