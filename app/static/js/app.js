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
      cerrar() { this.$el.close(); },
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

    // ------------------------------------------- carga de imágenes con nombre
    // Cada imagen elegida pide su nombre descriptivo (obligatorio) y un pie opcional antes de subir.
    Alpine.data("cargaImagenes", (url) => ({
      pendientes: [], arrastrando: false, subiendo: false, progreso: 0,
      sugerido(nombre) {
        return nombre.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
      },
      agregar(lista) {
        for (const archivo of lista || []) {
          if (!archivo.type.startsWith("image/")) { avisar(`«${archivo.name}» no es una imagen.`, "error"); continue; }
          this.pendientes.push({ id: Math.random(), archivo, titulo: this.sugerido(archivo.name), pie: "",
                                 vista: URL.createObjectURL(archivo) });
        }
        this.$nextTick(() => { const c = this.$root.querySelector("form input"); if (c) { c.focus(); c.select(); } });
      },
      quitar(i) { URL.revokeObjectURL(this.pendientes[i].vista); this.pendientes.splice(i, 1); },
      limpiar() { this.pendientes.forEach((p) => URL.revokeObjectURL(p.vista)); this.pendientes = []; },
      subir() {
        if (this.pendientes.some((p) => !p.titulo.trim())) { avisar("Escribe un nombre descriptivo para cada imagen.", "error"); return; }
        const datos = new FormData();
        for (const p of this.pendientes) {
          datos.append("archivos", p.archivo);
          datos.append("titulos", p.titulo.trim());
          datos.append("pies", p.pie.trim());
        }
        const xhr = new XMLHttpRequest();
        xhr.open("POST", url);
        xhr.setRequestHeader("HX-Request", "true");
        xhr.upload.onprogress = (e) => { if (e.lengthComputable) this.progreso = Math.round((e.loaded / e.total) * 100); };
        xhr.onload = () => {
          this.subiendo = false;
          const disparo = xhr.getResponseHeader("HX-Trigger");
          if (disparo) { try { const d = JSON.parse(disparo); if (d.aviso) avisar(d.aviso.mensaje, d.aviso.tipo); } catch (e) { /* nada */ } }
          if (xhr.status >= 200 && xhr.status < 300 && xhr.responseText) {
            this.limpiar();
            const galeria = document.getElementById("galeria");
            galeria.innerHTML = xhr.responseText;
            if (window.htmx) htmx.process(galeria);
          }
        };
        xhr.onerror = () => { this.subiendo = false; avisar("No se pudo subir. ¿Sigue abierta la biblioteca?", "error"); };
        this.subiendo = true;
        this.progreso = 0;
        xhr.send(datos);
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

  // ----------------------------------------------------- atajos de teclado
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      const buscador = document.getElementById("buscador-global");
      if (buscador) { buscador.focus(); buscador.select(); }
    }
  });
})();
