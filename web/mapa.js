/* Mapa de gasolineras: todas las del país (OpenStreetMap) con el precio que les toca.
   Verde = precio verificado por el MEM esta semana. Azul = precio de referencia de su departamento. */
(function () {
  "use strict";
  const CENTRO_GT = [14.6349, -90.5069];
  const NOMBRE = { s: "Súper", r: "Normal", d: "Diésel" };
  let mapa = null, capa = null, marcadorYo = null, datos = null, deptos = null;

  function $(id) { return document.getElementById(id); }
  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function q(n) { return n == null ? "–" : "Q" + Number(n).toFixed(2); }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* nada */ } }
  function recordar(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  /** Distancia en línea recta, para ordenar por cercanía. */
  function distancia(a, b) {
    const R = 6371, rad = x => x * Math.PI / 180;
    const dLat = rad(b[0] - a[0]), dLon = rad(b[1] - a[1]);
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  /** Precio de una gasolinera: el verificado si lo tiene, si no el de referencia de su departamento. */
  function precios(g) {
    if (g.p) return { valores: { superior: g.p.s, regular: g.p.r, diesel: g.p.d }, verificado: true };
    const fila = (deptos || []).find(d => d.departamento === g.d);
    if (!fila) return { valores: null, verificado: false };
    return { valores: { superior: fila.superior, regular: fila.regular, diesel: fila.diesel }, verificado: false };
  }

  function globo(g, desdeYo) {
    const p = precios(g);
    const v = p.valores;
    const lineas = [`<b>${g.n}</b>`];
    if (v) {
      lineas.push(`Súper ${q(v.superior)} · Normal ${q(v.regular)} · Diésel ${q(v.diesel)}`);
      lineas.push(p.verificado
        ? '<span class="verificado">✓ Precio verificado por el MEM esta semana</span>'
        : `<span class="referencia">Precio de referencia de ${g.d}. El de esta gasolinera puede variar.</span>`);
    } else {
      lineas.push("Sin precio todavía.");
    }
    if (desdeYo != null) lineas.push(`A ${desdeYo.toFixed(1)} km de ti`);
    if (g.aprox) lineas.push('<span class="referencia">Ubicación aproximada de la zona.</span>');
    lineas.push(`<a href="https://www.google.com/maps/dir/?api=1&destination=${g.lat},${g.lon}" target="_blank" rel="noopener">Cómo llegar →</a>`);
    return lineas.join("<br>");
  }

  function pintar(centro, radioKm) {
    if (capa) capa.remove();
    capa = L.layerGroup().addTo(mapa);
    const cerca = datos.gasolineras
      .map(g => ({ g, km: centro ? distancia(centro, [g.lat, g.lon]) : 0 }))
      .filter(x => !centro || x.km <= radioKm)
      .sort((a, b) => a.km - b.km)
      .slice(0, 400);

    for (const { g, km } of cerca) {
      const verificado = !!g.p;
      L.circleMarker([g.lat, g.lon], {
        radius: verificado ? 9 : 6,
        color: verificado ? "#2e9e5b" : "#1f5fbf",
        fillColor: verificado ? "#2e9e5b" : "#1f5fbf",
        fillOpacity: verificado ? 0.95 : 0.55, weight: verificado ? 3 : 1,
      }).addTo(capa).bindPopup(globo(g, centro ? km : null));
    }

    const conPrecio = cerca.filter(x => x.g.p).sort((a, b) => a.g.p.r - b.g.p.r);
    const lista = $("listaMapa");
    lista.innerHTML = "";
    if (conPrecio.length) {
      for (const { g, km } of conPrecio.slice(0, 5)) {
        const li = document.createElement("li");
        li.innerHTML = `<span><b>${g.n}</b><br><span class="meta">Normal ${q(g.p.r)}${centro ? " · a " + km.toFixed(1) + " km" : ""}</span></span>` +
          `<a class="ir" href="https://www.google.com/maps/dir/?api=1&destination=${g.lat},${g.lon}" target="_blank" rel="noopener">Ir</a>`;
        li.addEventListener("click", () => { mapa.setView([g.lat, g.lon], 16); });
        lista.appendChild(li);
      }
      $("mapaResumen").textContent = "Las verdes tienen precio verificado por el MEM esta semana. Toca cualquier punto para ver sus precios.";
    } else {
      $("mapaResumen").textContent = `${cerca.length} gasolineras por aquí. El MEM solo verifica precios en la capital, así que estas muestran el precio de referencia de su departamento.`;
    }
  }

  function ubicarme() {
    const btn = $("btnUbicarme");
    if (!navigator.geolocation) { btn.textContent = "Tu navegador no da la ubicación"; return; }
    btn.textContent = "Buscando dónde estás…";
    navigator.geolocation.getCurrentPosition(
      pos => {
        const yo = [pos.coords.latitude, pos.coords.longitude];
        btn.textContent = "📍 Ver las más cercanas";
        mapa.setView(yo, 13);
        if (marcadorYo) marcadorYo.remove();
        marcadorYo = L.circleMarker(yo, { radius: 8, color: "#ff8c1a", fillColor: "#ff8c1a", fillOpacity: 1, weight: 3 })
          .addTo(mapa).bindPopup("Aquí estás");
        pintar(yo, 25);
      },
      () => { btn.textContent = "No me diste permiso de ubicación"; },
      { timeout: 10000, maximumAge: 300000 }
    );
  }

  window.pintarMapa = function (gasolineras, departamentosHoy) {
    if (!gasolineras || !gasolineras.gasolineras || !gasolineras.gasolineras.length) return;
    if (typeof L === "undefined") return;   // si el mapa no cargó, la sección no aparece
    datos = gasolineras;
    deptos = (departamentosHoy && departamentosHoy.departamentos) || [];
    $("mapa").hidden = false;

    mapa = L.map("lienzoMapa", { scrollWheelZoom: false }).setView(CENTRO_GT, 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18, attribution: "© OpenStreetMap",
    }).addTo(mapa);

    const sel = $("selDeptoMapa");
    const nombres = [...new Set(datos.gasolineras.map(g => g.d))].sort((a, b) => a.localeCompare(b, "es"));
    for (const n of nombres) {
      const o = document.createElement("option");
      o.value = n; o.textContent = n + " (" + datos.gasolineras.filter(g => g.d === n).length + ")";
      sel.appendChild(o);
    }
    const guardado = recordar("gasolinagt.depto");
    sel.value = nombres.includes(guardado) ? guardado : "Guatemala";

    function verDepartamento() {
      const dep = sel.value;
      guardar("gasolinagt.depto", dep);
      const suyas = datos.gasolineras.filter(g => g.d === dep);
      if (!suyas.length) return;
      const centro = [suyas.reduce((a, g) => a + g.lat, 0) / suyas.length,
                      suyas.reduce((a, g) => a + g.lon, 0) / suyas.length];
      mapa.setView(centro, dep === "Guatemala" ? 12 : 10);
      pintar(centro, 60);
    }
    sel.addEventListener("change", verDepartamento);
    $("btnUbicarme").addEventListener("click", ubicarme);
    $("mapaTotal").textContent = datos.total + " gasolineras de todo el país";
    verDepartamento();
  };
})();
