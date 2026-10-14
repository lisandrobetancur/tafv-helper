// Comportamiento compartido de la Biblioteca de Estudio (Alpine.js + HTMX, sin dependencias externas).
(() => {
  "use strict";

  const guardar = (clave, valor) => { try { localStorage.setItem(clave, valor); } catch (e) { /* sin almacenamiento */ } };
  const leer = (clave) => { try { return localStorage.getItem(clave); } catch (e) { return null; } };
  const avisar = (mensaje, tipo = "exito") =>
    window.dispatchEvent(new CustomEvent("aviso", { detail: { mensaje, tipo } }));
  window.avisar = avisar;

  // HTMX: el botón "atrás" vuelve a pedir la página (evita estados viejos de Alpine en caché).
  document.addEventListener("DOMContentLoaded", () => {
    if (window.htmx) {
      htmx.config.historyCacheSize = 0;
      htmx.config.refreshOnHistoryMiss = true;
    }
  });
  // Errores de red (servidor cerrado, etc.)
  document.addEventListener("htmx:sendError", () =>
    avisar("No hay conexión con la biblioteca. ¿Se cerró la ventana del servidor?", "error"));

  document.addEventListener("alpine:init", () => {
    // ---------------------------------------------------------------- tema
    const medio = window.matchMedia("(prefers-color-scheme: dark)");
    Alpine.store("tema", {
      valor: leer("tema") || "sistema",
      poner(valor) {
        this.valor = valor;
        guardar("tema", valor);
        this.aplicar();
      },
      aplicar() {
        const oscuro = this.valor === "oscuro" || (this.valor === "sistema" && medio.matches);
        document.documentElement.dataset.theme = oscuro ? "oscuro" : "claro";
      },
    });
    medio.addEventListener("change", () => Alpine.store("tema").aplicar());

    // ---------------------------------------------------------- menú lateral
    Alpine.store("menu", {
      plegado: leer("menu-plegado") === "1",
      alternar() {
        this.plegado = !this.plegado;
        guardar("menu-plegado", this.plegado ? "1" : "0");
        document.documentElement.dataset.menu = this.plegado ? "plegado" : "";
      },
    });

    // ---------------------------------------------------------------- modal
    // Las respuestas de HTMX traen un <dialog x-data="modal">; se abre solo y se borra al cerrar.
    Alpine.data("modal", () => ({
      init() {
        this.$el.showModal();
        this.$el.addEventListener("close", () => this.$el.remove());
        this.$el.addEventListener("click", (e) => { if (e.target === this.$el) this.$el.close(); });
        const primero = this.$el.querySelector("[autofocus], input:not([type=hidden]), textarea, button");
        if (primero) primero.focus();
      },
      // Desde un botón, $el es el botón (no el <dialog>): se busca el diálogo que lo contiene.
      cerrar() { this.$el.closest("dialog")?.close(); },
    }));

    // --------------------------------------------------------------- avisos
    Alpine.data("avisos", () => ({
      lista: [],
      init() {
        const inicial = document.getElementById("aviso-inicial");
        if (inicial) {
          try { const a = JSON.parse(inicial.textContent); if (a) this.mostrar(a); } catch (e) { /* nada */ }
        }
      },
      mostrar({ mensaje, tipo = "exito" }) {
        const id = Date.now() + Math.random();
        this.lista.push({ id, mensaje, tipo });
        setTimeout(() => this.quitar(id), tipo === "error" ? 8000 : 4500);
      },
      quitar(id) { this.lista = this.lista.filter((a) => a.id !== id); },
    }));

    // ------------------------------------------------- menú desplegable (⋮)
    Alpine.data("desplegable", () => ({
      abierto: false,
      alternar() { this.abierto = !this.abierto; },
      cerrar() { this.abierto = false; },
    }));

    // ------------------------------------------- listas ordenables arrastrando
    // <ul x-data="ordenable" data-url="/materias/orden" data-extra='{"materia_id": 1}'>
    Alpine.data("ordenable", () => ({
      init() {
        if (!window.Sortable) return;
        Sortable.create(this.$el, {
          handle: ".asa",
          animation: 150,
          onEnd: async (evento) => {
            if (evento.oldIndex === evento.newIndex) return;
            const ids = [...this.$el.children].map((n) => Number(n.dataset.id)).filter(Boolean);
            const extra = JSON.parse(this.$el.dataset.extra || "{}");
            try {
              const r = await fetch(this.$el.dataset.url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ids, ...extra }),
              });
              if (!r.ok) throw new Error();
              avisar("Orden guardado.");
            } catch (e) {
              avisar("No se pudo guardar el orden.", "error");
            }
          },
        });
      },
    }));

    // ---------------------------------------- carga de archivos con nombre
    // Cada archivo elegido pide su nombre descriptivo (obligatorio) antes de subir; las imágenes,
    // además, un pie de foto opcional. tipo: "imagen" (ficha de fila) | "galeria" (imágenes sueltas:
    // descripción y etiquetas) | "pdf". La respuesta reemplaza #destino.
    Alpine.data("carga", (url, destino, tipo = "imagen") => ({
      pendientes: [], arrastrando: false, subiendo: false, progreso: 0,
      sugerido(nombre) {
        return nombre.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
      },
      valido(archivo) {
        return tipo === "pdf" ? archivo.type === "application/pdf" || /\.pdf$/i.test(archivo.name)
                              : archivo.type.startsWith("image/");
      },
      get esImagen() { return tipo !== "pdf"; 
      },
      agregar(lista) {
        for (const archivo of lista || []) {
          if (!this.valido(archivo)) {
            avisar(`«${archivo.name}» no es ${tipo === "pdf" ? "un PDF" : "una imagen"}.`, "error"); continue;
          }
          this.pendientes.push({ id: Math.random(), archivo, titulo: this.sugerido(archivo.name), pie: "", etiquetas: "",
                                 vista: tipo !== "pdf" ? URL.createObjectURL(archivo) : "" });
        }
        this.$nextTick(() => { const c = this.$root.querySelector("form input"); if (c) { c.focus(); c.select(); } });
      },
      quitar(i) { if (this.pendientes[i].vista) URL.revokeObjectURL(this.pendientes[i].vista); this.pendientes.splice(i, 1); },
      limpiar() { this.pendientes.forEach((p) => p.vista && URL.revokeObjectURL(p.vista)); this.pendientes = []; },
      subir() {
        if (this.pendientes.some((p) => !p.titulo.trim())) { avisar("Escribe un nombre descriptivo para cada archivo.", "error"); return; }
        const datos = new FormData();
        for (const p of this.pendientes) {
          datos.append("archivos", p.archivo);
          datos.append("titulos", p.titulo.trim());
          if (tipo === "imagen") datos.append("pies", p.pie.trim());
          if (tipo === "galeria") { datos.append("descripciones", p.pie.trim()); datos.append("etiquetas", p.etiquetas.trim()); }
        }
        const ocr = this.$root.querySelector("[name=extraer_texto]");
        if (ocr && ocr.checked) datos.append("extraer_texto", "true");
        const xhr = new XMLHttpRequest();
        xhr.open("POST", url);
        xhr.setRequestHeader("HX-Request", "true");
        xhr.upload.onprogress = (e) => { if (e.lengthComputable) this.progreso = Math.round((e.loaded / e.total) * 100); };
        xhr.onload = () => {
          this.subiendo = false;
          const disparo = xhr.getResponseHeader("HX-Trigger");
          if (disparo) {
            try {
              const d = JSON.parse(disparo);
              if (d.aviso) avisar(d.aviso.mensaje, d.aviso.tipo);
              if (d["ocr-actualizado"]) document.body.dispatchEvent(new Event("ocr-actualizado"));
            } catch (e) { /* nada */ }
          }
          if (xhr.status >= 200 && xhr.status < 300 && xhr.responseText) {
            this.limpiar();
            // Si la respuesta trae el propio contenedor (#destino), lo reemplaza entero; si no, su contenido
            const zona = document.getElementById(destino);
            const plantilla = document.createElement("template");
            plantilla.innerHTML = xhr.responseText.trim();
            const raiz = plantilla.content.firstElementChild;
            if (raiz && raiz.id === destino && plantilla.content.childElementCount === 1) zona.replaceWith(raiz);
            else zona.replaceChildren(plantilla.content);
            if (window.htmx) htmx.process(document.getElementById(destino));
          }
        };
        xhr.onerror = () => { this.subiendo = false; avisar("No se pudo subir. ¿Sigue abierta la biblioteca?", "error"); };
        this.subiendo = true;
        this.progreso = 0;
        xhr.send(datos);
      },
    }));

    // ------------------------------------------------ paleta de búsqueda (⌘K)
    Alpine.data("paleta", () => ({
      q: "", activo: -1,
      abrir(texto = "") {
        const d = this.$refs.dialogo;
        if (!d.open) d.showModal();
        if (texto) this.q = texto;
        this.$nextTick(() => {
          this.$refs.entrada.focus();
          this.$refs.entrada.select();
          htmx.trigger(this.$refs.entrada, "buscar");
        });
      },
      cerrar() { this.$refs.dialogo.close(); },
      enlaces() { return [...this.$root.querySelectorAll("#paleta-resultados [data-resultado]")]; },
      marcar() {
        this.enlaces().forEach((a, i) => {
          a.toggleAttribute("data-activo", i === this.activo);
          if (i === this.activo) a.scrollIntoView({ block: "nearest" });
        });
      },
      teclas(e) {
        const lista = this.enlaces();
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          if (!lista.length) return;
          this.activo = (this.activo + (e.key === "ArrowDown" ? 1 : -1) + lista.length) % lista.length;
          this.marcar();
        } else if (e.key === "Enter") {
          e.preventDefault();
          const destino = lista[this.activo] || lista[0];
          if (destino) { this.cerrar(); destino.click(); }
          else if (this.q.trim()) { this.cerrar(); window.location.href = "/buscar?q=" + encodeURIComponent(this.q); }
        }
      },
    }));

    // ------------------------------------------------- diagnóstico por síntomas
    // Síntomas como "chips" (con autocompletado desde el material); cada cambio recalcula el resultado.
    Alpine.data("diagnostico", (iniciales = [], importantes = []) => ({
      sintomas: iniciales.map((t) => ({ texto: t, importante: importantes.includes(t) })),
      texto: "", sugerencias: [], activa: -1, seq: 0,
      norm(t) { return t.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim(); },
      recalcular() { this.$nextTick(() => htmx.trigger(this.$root, "cambio")); },
      agregar(t) {
        t = (t || "").replace(/\s+/g, " ").trim();
        this.texto = ""; this.sugerencias = []; this.activa = -1;
        if (!t || this.sintomas.some((s) => this.norm(s.texto) === this.norm(t))) return;
        this.sintomas.push({ texto: t, importante: false });
        this.recalcular();
      },
      quitar(i) { this.sintomas.splice(i, 1); this.recalcular(); },
      alternar(i) { this.sintomas[i].importante = !this.sintomas[i].importante; this.recalcular(); },
      mover(d) {
        if (!this.sugerencias.length) return;
        this.activa = (this.activa + d + this.sugerencias.length) % this.sugerencias.length;
      },
      async sugerir() {
        const q = this.texto.trim();
        const mio = ++this.seq;
        if (q.length < 2) { this.sugerencias = []; return; }
        try {
          const r = await fetch("/diagnostico/sugerencias?q=" + encodeURIComponent(q));
          const lista = await r.json();
          if (mio !== this.seq) return;
          const ya = new Set(this.sintomas.map((s) => this.norm(s.texto)));
          this.sugerencias = lista.filter((t) => !ya.has(this.norm(t)));
          this.activa = -1;
        } catch (e) { this.sugerencias = []; }
      },
    }));

    // ------------------------------------------------- modo repaso (flashcards)
    // Espacio: dar vuelta · →: lo sé · ←: repasar. Cada marca se guarda en el servidor.
    Alpine.data("repaso", (tarjetas) => ({
      tarjetas, i: 0, volteada: false, terminado: false, resultados: {},
      get actual() { return this.tarjetas[this.i] || { imagenes: [] }; },
      get loSe() { return Object.values(this.resultados).filter((e) => e === "lo_se").length; },
      get porRepasar() { return Object.values(this.resultados).filter((e) => e === "repasar").length; },
      get progreso() { return Math.round((Object.keys(this.resultados).length / this.tarjetas.length) * 100); },
      girar() { this.volteada = !this.volteada; },
      async marcar(estado) {
        const tarjeta = this.actual;
        this.resultados[tarjeta.fila_id] = estado;
        const datos = new FormData();
        datos.append("estado", estado);
        fetch(`/repaso/${tarjeta.fila_id}`, { method: "POST", body: datos })
          .catch(() => avisar("No se pudo guardar la marca de esta tarjeta.", "error"));
        if (this.i + 1 < this.tarjetas.length) { this.i++; this.volteada = false; }
        else { this.terminado = true; }
      },
      repetirFalladas() {
        this.tarjetas = this.tarjetas.filter((t) => this.resultados[t.fila_id] === "repasar");
        this.resultados = {}; this.i = 0; this.volteada = false; this.terminado = false;
      },
      teclas(e) {
        const enCampo = e.target instanceof Element && e.target.closest("input, textarea, select");
        if (this.terminado || enCampo || document.querySelector("dialog[open]")) return;
        if (e.key === " ") { e.preventDefault(); this.girar(); }
        else if (this.volteada && e.key === "ArrowRight") { e.preventDefault(); this.marcar("lo_se"); }
        else if (this.volteada && e.key === "ArrowLeft") { e.preventDefault(); this.marcar("repasar"); }
      },
    }));

    // ------------------------------------------------ visor con zoom (lightbox)
    // Se abre con: $dispatch('abrir-visor', { imagenes: [{src, titulo, pie}], indice })
    Alpine.data("visor", () => ({
      imagenes: [], i: 0, zoom: 1, x: 0, y: 0, arrastre: null,
      get actual() { return this.imagenes[this.i] || {}; },
      abrir({ imagenes, indice = 0 }) {
        this.imagenes = imagenes; this.i = indice; this.restablecer();
        this.$refs.dialogo.showModal();
      },
      cerrar() { this.$refs.dialogo.close(); },
      pasar(d) {
        const n = this.imagenes.length;
        if (n < 2) return;
        this.i = (this.i + d + n) % n; this.restablecer();
      },
      restablecer() { this.zoom = 1; this.x = 0; this.y = 0; },
      acercar(factor) {
        this.zoom = Math.min(8, Math.max(1, this.zoom * factor));
        if (this.zoom === 1) { this.x = 0; this.y = 0; }
      },
      rueda(e) { this.acercar(e.deltaY < 0 ? 1.15 : 1 / 1.15); },
      inicio(e) { if (this.zoom > 1) { this.arrastre = { x: e.clientX - this.x, y: e.clientY - this.y }; e.target.setPointerCapture?.(e.pointerId); } },
      mover(e) { if (this.arrastre) { this.x = e.clientX - this.arrastre.x; this.y = e.clientY - this.arrastre.y; } },
      fin() { this.arrastre = null; },
      teclas(e) {
        const acciones = { ArrowLeft: () => this.pasar(-1), ArrowRight: () => this.pasar(1), "+": () => this.acercar(1.4),
                           "=": () => this.acercar(1.4), "-": () => this.acercar(1 / 1.4), "0": () => this.restablecer() };
        if (acciones[e.key]) { e.preventDefault(); acciones[e.key](); }
      },
    }));
  });

  // --------------------------------------------- visor de PDF (PDF.js en iframe)
  // PDF.js avisa a la página que lo contiene antes de arrancar: se fija el español y el tema de la app.
  document.addEventListener("webviewerloaded", (e) => {
    const opciones = e.detail?.source?.PDFViewerApplicationOptions;
    if (!opciones) return;
    opciones.set("localeProperties", { lang: "es-ES" });
    opciones.set("viewerCssTheme", document.documentElement.dataset.theme === "oscuro" ? 2 : 1);
  });

  // ----------------------------------------------------- atajos de teclado
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      window.dispatchEvent(new CustomEvent("abrir-paleta", { detail: { q: "" } }));
    }
  });

  // ------------------------------- resaltar el término buscado al abrir un resultado
  // Las páginas marcan con [data-resaltar] dónde buscar; el término llega en ?buscar=…
  const sinTildes = (t) => t.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  function resaltar(raiz, termino) {
    const palabras = sinTildes(termino.replace(/"/g, " ")).split(/\s+/).filter((p) => p.length > 1);
    if (!palabras.length) return 0;
    let total = 0;
    const recorrido = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement.closest("mark, script, style, textarea, input") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    const nodos = [];
    while (recorrido.nextNode()) nodos.push(recorrido.currentNode);
    for (const nodo of nodos) {
      const texto = nodo.nodeValue;
      // texto sin tildes con el mismo largo (un carácter por carácter) para ubicar las coincidencias
      const plano = [...texto].map((c) => sinTildes(c)[0] || c).join("");
      const rangos = [];
      for (const p of palabras) {
        let i = plano.indexOf(p);
        while (i !== -1) { rangos.push([i, i + p.length]); i = plano.indexOf(p, i + p.length); }
      }
      if (!rangos.length || plano.length !== texto.length) continue;
      rangos.sort((a, b) => a[0] - b[0]);
      const fragmento = document.createDocumentFragment();
      let pos = 0;
      for (const [a, b] of rangos) {
        if (a < pos) continue;
        fragmento.append(texto.slice(pos, a));
        const marca = document.createElement("mark");
        marca.className = "rounded bg-oro-suave px-0.5 text-texto ring-1 ring-oro/40";
        marca.textContent = texto.slice(a, b);
        fragmento.append(marca);
        pos = b;
        total++;
      }
      fragmento.append(texto.slice(pos));
      nodo.replaceWith(fragmento);
    }
    return total;
  }
  // Zonas con data-resaltar="término" (lo pone el servidor desde ?buscar=) y galería con data-destacar="id"
  function resaltarPendientes() {
    let primera = null;
    document.querySelectorAll("[data-resaltar]:not([data-resaltado])").forEach((zona) => {
      zona.setAttribute("data-resaltado", "");
      if (zona.dataset.resaltar && resaltar(zona, zona.dataset.resaltar)) primera = primera || zona.querySelector("mark");
    });
    if (primera) primera.scrollIntoView({ block: "center" });
    document.querySelectorAll("[data-destacar]:not([data-destacado])").forEach((g) => {
      g.setAttribute("data-destacado", "");
      const tarjeta = g.querySelector(`li[data-id="${CSS.escape(g.dataset.destacar)}"]`);
      if (tarjeta) { tarjeta.classList.add("ring-2", "ring-oro"); tarjeta.scrollIntoView({ block: "center" }); }
    });
  }
  document.addEventListener("DOMContentLoaded", resaltarPendientes);
  document.addEventListener("htmx:afterSettle", resaltarPendientes);
})();
