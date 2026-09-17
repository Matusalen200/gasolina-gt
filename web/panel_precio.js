/* Panel de precios: arriba la gráfica de los tres combustibles, abajo la tabla igual que la del MEM. */
(function () {
  "use strict";
  const PRODUCTOS = ["superior", "regular", "diesel", "kerosene"];
  const NOMBRE = { superior: "Súper", regular: "Normal", diesel: "Diésel", kerosene: "Kerosene" };
  const RANGOS = { "1S": 7, "1M": 31, "3M": 92, "1A": 366 };
  let grafica = null;

  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function $(id) { return document.getElementById(id); }
  function q(n) { return n == null ? "–" : "Q" + Number(n).toFixed(2); }
  function fechaCorta(iso) {
    if (!iso) return "";
    const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
    return d.toLocaleDateString("es-GT", { day: "numeric", month: "short" });
  }
  function recordar(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* nada */ } }

  /** Degradado suave debajo de la línea, como en las gráficas de bolsa. */
  function relleno(ctx, hex) {
    const g = ctx.createLinearGradient(0, 0, 0, 240);
    g.addColorStop(0, hex + "44");
    g.addColorStop(1, hex + "05");
    return g;
  }

  function color(prod) {
    return { superior: css("--resalte"), regular: css("--acento"), diesel: "#8b5cf6", kerosene: css("--texto-suave") }[prod];
  }

  /** Une el historial semanal del MEM con la serie diaria de los medios, por producto. */
  function serie(hoyDatos, historialMem, prod) {
    const puntos = {};
    for (const h of historialMem || []) if (h[prod] != null) puntos[h.fecha] = h[prod];
    for (const d of (hoyDatos && hoyDatos.diario) || []) if (d[prod] != null) puntos[d.fecha] = d[prod];
    return puntos;
  }

  /** Precio vigente por producto: gana el más reciente entre el MEM oficial y el promedio de medios. */
  function vigente(hoyDatos, precios, prod) {
    const auto = (precios && precios.autoservicio) || {};
    const u = ((hoyDatos && hoyDatos.ultimo) || {})[prod];
    const usaOficial = auto[prod] != null && (!u || u.tipo !== "promedio" || (precios.fecha_monitoreo || "") >= u.fecha);
    if (usaOficial) return { valor: auto[prod], fecha: precios.fecha_monitoreo, oficial: true };
    if (u) return { valor: u.valor, fecha: u.fecha, oficial: false, fuente: u.fuente, url: u.url };
    return { valor: null };
  }

  window.pintarPanelPrecio = function (hoyDatos, precios, historialMem) {
    const auto = (precios && precios.autoservicio) || {};
    if (!PRODUCTOS.some(p => vigente(hoyDatos, precios, p).valor != null)) return;
    $("precios").hidden = false;
    let rango = recordar("gasolinagt.rango") || "1M";

    /* ---------------- la tabla, igual que la del MEM ---------------- */
    function pintarTabla() {
      const cambio = (precios && precios.cambio_semanal) || {};
      const vr = vigente(hoyDatos, precios, "regular");
      $("colAntes").textContent = auto.fecha_anterior ? "Antes (" + fechaCorta(auto.fecha_anterior) + ")" : "Antes";
      $("colHoy").textContent = vr.fecha ? "Hoy (" + fechaCorta(vr.fecha) + ")" : "Hoy";

      const cuerpo = $("cuerpoTabla");
      cuerpo.innerHTML = "";
      for (const prod of PRODUCTOS) {
        const v = vigente(hoyDatos, precios, prod);
        if (v.valor == null) continue;
        const dif = cambio[prod];
        const antes = dif != null ? v.valor - dif : null;
        const clase = dif > 0 ? "up" : dif < 0 ? "down" : "";
        const flecha = dif > 0 ? "▲ +Q" : dif < 0 ? "▼ −Q" : "= Q";
        const fila = document.createElement("tr");
        fila.innerHTML =
          '<td><span class="punto" style="background:' + color(prod) + '"></span>' + NOMBRE[prod] + "</td>" +
          "<td>" + q(antes) + "</td>" +
          "<td><b>" + q(v.valor) + "</b></td>" +
          '<td class="' + clase + '">' + (dif == null ? "–" : flecha + Math.abs(dif).toFixed(2)) + "</td>";
        cuerpo.appendChild(fila);
      }

      const MEM_URL = "https://mem.gob.gt/que-hacemos/hidrocarburos/comercializacion-downstream/precios-combustible-nacionales/";
      $("precioFuente").innerHTML = vr.oficial
        ? 'Precios de referencia oficiales del MEM, modalidad autoservicio. <a href="' + MEM_URL + '" target="_blank" rel="noopener">Ver en mem.gob.gt</a>'
        : "Precios del " + fechaCorta(vr.fecha) + " según " + (vr.fuente || "los medios") +
          ". El MEM aún no publica el informe de esta semana." +
          (vr.url ? ' <a href="' + vr.url + '" target="_blank" rel="noopener">Ver nota</a>' : "");

      const tope = hoyDatos && hoyDatos.tope;
      const topeEl = $("precioTope");
      if (tope && tope.regular != null) {
        topeEl.hidden = false;
        topeEl.textContent = "Precio tope aprobado por el Congreso: Súper " + q(tope.superior) + " · Normal " + q(tope.regular) +
          " · Diésel " + q(tope.diesel) + ". Cuando entre en vigor, ninguna gasolinera debería cobrar más.";
      } else { topeEl.hidden = true; }
    }

    /* ---------------- la gráfica de los tres ---------------- */
    function pintarGrafica() {
      const desde = new Date(); desde.setDate(desde.getDate() - RANGOS[rango]);
      const dibujables = ["superior", "regular", "diesel"].filter(p => Object.keys(serie(hoyDatos, historialMem, p)).length);
      const fechas = [...new Set(dibujables.flatMap(p => Object.keys(serie(hoyDatos, historialMem, p))))].sort();
      let visibles = fechas.filter(f => new Date(f + "T12:00:00") >= desde);
      if (visibles.length < 2) visibles = fechas.slice(-8);

      const datasets = dibujables.map(p => {
        const s = serie(hoyDatos, historialMem, p);
        const c = color(p);
        return {
          label: NOMBRE[p],
          data: visibles.map(f => (s[f] != null ? s[f] : null)),
          borderColor: c,
          backgroundColor: relleno($("graficaPrecio").getContext("2d"), c),
          fill: "start", tension: 0.25, spanGaps: true, borderWidth: 2.5,
          pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: c,
        };
      });

      if (grafica) grafica.destroy();
      grafica = new Chart($("graficaPrecio").getContext("2d"), {
        type: "line",
        data: { labels: visibles, datasets },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { position: "top", align: "start", labels: { boxWidth: 22, usePointStyle: true, pointStyle: "line", padding: 16 } },
            tooltip: { callbacks: { title: i => fechaCorta(i[0].label), label: c => " " + c.dataset.label + ": " + q(c.raw) } },
          },
          scales: {
            y: { border: { display: false }, grid: { color: css("--borde"), drawTicks: false },
                 ticks: { callback: v => "Q" + v, maxTicksLimit: 5, padding: 8 } },
            x: { border: { display: false }, grid: { display: false },
                 ticks: { maxTicksLimit: 4, maxRotation: 0, padding: 6, callback: (v, i) => fechaCorta(visibles[i]) } },
          },
        },
      });
    }

    document.querySelectorAll("#tabsRango button").forEach(b => {
      b.classList.toggle("activo", b.dataset.r === rango);
      b.addEventListener("click", () => {
        rango = b.dataset.r; guardar("gasolinagt.rango", rango);
        document.querySelectorAll("#tabsRango button").forEach(x => x.classList.toggle("activo", x === b));
        pintarGrafica();
      });
    });
    pintarGrafica();
    pintarTabla();
  };
})();
