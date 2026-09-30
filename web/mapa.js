/* Mapa de gasolineras: todas las del país (OpenStreetMap) con el precio que les toca.
   Verde = precio que el MEM verificó hace poco. Amarillo = verificado pero ya viejo.
   Azul = sin verificar, se muestra el precio de referencia de su departamento. */
(function () {
  "use strict";
  const CENTRO_GT = [14.6349, -90.5069];
  const DIAS_FRESCO = 10;   // pasado eso, un precio por gasolinera ya no sirve como "precio de hoy"
  let mapa = null, capa = null, marcadorYo = null, datos = null, deptos = null;
  let fechaVerificado = null, diasVerificado = null;

  function $(id) { return document.getElementById(id); }
  function q(n) { return n == null ? "–" : "Q" + Number(n).toFixed(2); }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* nada */ } }
  function recordar(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function fechaLarga(iso) {
    if (!iso) return "";
    return new Date(iso + "T12:00:00").toLocaleDateString("es-GT", { day: "numeric", month: "long" });
  }
  const viejo = () => diasVerificado != null && diasVerificado > DIAS_FRESCO;

  /** Distancia en línea recta, para ordenar por cercanía. */
  function distancia(a, b) {
    const R = 6371, rad = x => x * Math.PI / 180;
    const dLat = rad(b[0] - a[0]), dLon = rad(b[1] - a[1]);
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function referencia(depto) {
    return (deptos || []).find(d => d.departamento === depto);
  }

  function globo(g, desdeYo) {
    const lineas = [`<b>${g.n}</b>`];
    if (g.p) {
      lineas.push(`Súper ${q(g.p.s)} · Normal ${q(g.p.r)} · Diésel ${q(g.p.d)}`);
      if (viejo()) {
        lineas.push(`<span class="viejo">⚠ Ese precio es del ${fechaLarga(fechaVerificado)}, hace ${diasVerificado} días.</span>`);
        const ref = referencia(g.d);
        if (ref) lineas.push(`<span class="referencia">Hoy la referencia de ${g.d} es ${q(ref.regular)} la normal.</span>`);
      } else {
        lineas.push(`<span class="verificado">✓ Precio que el MEM verificó el ${fechaLarga(fechaVerificado)}</span>`);
      }
    } else {
      const ref = referencia(g.d);
      if (ref) {
        lineas.push(`Súper ${q(ref.superior)} · Normal ${q(ref.regular)} · Diésel ${q(ref.diesel)}`);
        lineas.push(`<span class="referencia">Precio de referencia de ${g.d}. El de esta bomba puede variar.</span>`);
      } else {
        lineas.push("Sin precio todavía.");
      }
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
      const tono = !g.p ? "#1f5fbf" : viejo() ? "#e0a800" : "#2e9e5b";
      L.circleMarker([g.lat, g.lon], {
        radius: g.p ? 9 : 6, color: tono, fillColor: tono,
        fillOpacity: g.p ? 0.95 : 0.55, weight: g.p ? 3 : 1,
      }).addTo(capa).bindPopup(globo(g, centro ? km : null));
    }

    const conPrecio = cerca.filter(x => x.g.p).sort((a, b) => a.g.p.r - b.g.p.r);
    const lista = $("listaMapa");
    lista.innerHTML = "";
    for (const { g, km } of conPrecio.slice(0, 5)) {
      const cuando = viejo() ? "precio del " + fechaLarga(fechaVerificado) : "verificado";
      const li = document.createElement("li");
      li.innerHTML = `<span><b>${g.n}</b><br><span class="meta">Normal ${q(g.p.r)} · ${cuando}` +
        `${centro ? " · a " + km.toFixed(1) + " km" : ""}</span></span>` +
        `<a class="ir" href="https://www.google.com/maps/dir/?api=1&destination=${g.lat},${g.lon}" target="_blank" rel="noopener">Ir</a>`;
      li.addEventListener("click", () => { mapa.setView([g.lat, g.lon], 16); });
      lista.appendChild(li);
    }

    if (!conPrecio.length) {
      $("mapaResumen").textContent = `${cerca.length} gasolineras por aquí. El MEM solo verifica precios en la capital, así que estas muestran el precio de referencia de su departamento.`;
    } else if (viejo()) {
      $("mapaResumen").textContent = `Ojo: los puntos amarillos traen el precio que el MEM verificó el ${fechaLarga(fechaVerificado)}, hace ${diasVerificado} días. Desde entonces el precio general cambió, así que tómalos como referencia vieja, no como el precio de hoy.`;
    } else {
      $("mapaResumen").textContent = `Los puntos verdes traen el precio que el MEM verificó el ${fechaLarga(fechaVerificado)}. Toca cualquier punto para ver sus precios.`;
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
    fechaVerificado = gasolineras.fecha_verificado || null;
    if (fechaVerificado) {
      diasVerificado = Math.round((Date.now() - new Date(fechaVerificado + "T12:00:00")) / 864e5);
    }
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
