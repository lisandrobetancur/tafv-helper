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
