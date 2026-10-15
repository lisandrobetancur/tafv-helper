// Comportamiento compartido de la Biblioteca de Estudio (Alpine.js + HTMX, sin dependencias externas).
(() => {
  "use strict";

  const guardar = (clave, valor) => { try { localStorage.setItem(clave, valor); } catch (e) { /* sin almacenamiento */ } };
  const leer = (clave) => { try { return localStorage.getItem(clave); } catch (e) { return null; } };
  const avisar = (mensaje, tipo = "exito") =>
    window.dispatchEvent(new CustomEvent("aviso", { detail: { mensaje, tipo } }));
  window.avisar = avisar;

  // ------------------------------------------------ pegar tablas de Excel
  // Excel copia las celdas como texto separado por tabuladores (las celdas con saltos de línea van
  // entre comillas). Se convierten en tablas Markdown: cada bloque separado por una fila vacía es una
  // tabla; una fila con una sola celda encima del bloque es su título; se quitan las columnas vacías.
  // Si el bloque tiene una sola columna, la primera celda es el título y el resto una lista.
  const leerTSV = (texto) => {
    const filas = [];
    let fila = [], celda = "", comillas = false;
    texto = texto.replace(/\r\n?/g, "\n");
    for (let i = 0; i < texto.length; i++) {
      const c = texto[i];
      if (comillas) {
        if (c === '"' && texto[i + 1] === '"') { celda += '"'; i++; }
        else if (c === '"') comillas = false;
        else celda += c;
      } else if (c === '"' && celda === "") comillas = true;
      else if (c === "\t") { fila.push(celda); celda = ""; }
      else if (c === "\n") { fila.push(celda); filas.push(fila); fila = []; celda = ""; }
      else celda += c;
    }
    if (celda !== "" || fila.length) { fila.push(celda); filas.push(fila); }
    return filas;
  };
  // Excel y Google Sheets también copian la tabla en HTML: ahí se ven las celdas combinadas y las
  // negritas. Una celda combinada hacia abajo (rowspan) se repite en cada fila que abarca (como al
  // importar); una combinada hacia el lado (colspan) queda solo en la primera columna.
  const leerHTML = (html) => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const tabla = doc.querySelector("table");
    if (!tabla) return null;
    const estilos = [...doc.querySelectorAll("style")].map((e) => e.textContent).join("\n");
    const clasesNegrita = new Set([...estilos.matchAll(/\.([\w-]+)\s*\{[^}]*font-weight\s*:\s*(?:700|bold)/gi)].map((m) => m[1]));
    const esNegrita = (td) => /font-weight\s*:\s*(?:700|bold)/i.test(td.getAttribute("style") || "") ||
      [...td.classList].some((c) => clasesNegrita.has(c)) ||
      (!!td.querySelector("b, strong") && td.textContent.trim() === (td.querySelector("b, strong")?.textContent || "").trim());
    const filas = [], negritas = [], ocupadas = [];       // ocupadas[i][j] = valor que baja de una combinada
    [...tabla.rows].forEach((tr, i) => {
      filas[i] = filas[i] || []; negritas[i] = negritas[i] || [];
      let j = 0;
      for (const td of tr.cells) {
        while (ocupadas[i]?.[j] !== undefined) { filas[i][j] = ocupadas[i][j]; negritas[i][j] = false; j++; }
        td.querySelectorAll("br").forEach((br) => br.replaceWith("\n"));
        const texto = td.textContent.replace(/[ \t\u00a0]+/g, " ").replace(/ *\n */g, "\n").trim();
        const alto = Math.max(1, Number(td.rowSpan) || 1), ancho = Math.max(1, Number(td.colSpan) || 1);
        for (let a = 0; a < ancho; a++) {
          filas[i][j + a] = a === 0 ? texto : "";
          negritas[i][j + a] = esNegrita(td);
          for (let b = 1; b < alto; b++) {
            ocupadas[i + b] = ocupadas[i + b] || [];
            ocupadas[i + b][j + a] = a === 0 ? texto : "";
          }
        }
        j += ancho;
      }
      while (ocupadas[i]?.[j] !== undefined) { filas[i][j] = ocupadas[i][j]; negritas[i][j] = false; j++; }
    });
    return { filas, negritas };
  };
  const excelAMarkdown = (texto, html = "") => {
    const limpia = (c) => (c || "").trim().replace(/\s*\n\s*/g, " / ").replace(/\|/g, "\\|");
    const deHTML = html ? leerHTML(html) : null;
    const crudas = deHTML ? deHTML.filas : leerTSV(texto);
    const filas = crudas.map((f) => [...f].map(limpia));
    const bloques = [[]];
    filas.forEach((f, i) => {
      if (f.every((c) => !c)) { if (bloques[bloques.length - 1].length) bloques.push([]); }
      else bloques[bloques.length - 1].push(i);
    });
    const partes = [];
    for (let indices of bloques.filter((b) => b.length)) {
      const llenas = (i) => filas[i].filter((c) => c);
      if (indices.length > 1 && llenas(indices[0]).length === 1) {          // título del bloque
        partes.push(`## ${llenas(indices[0])[0]}`);
        indices = indices.slice(1);
      }
      if (indices.length === 1 && llenas(indices[0]).length === 1) { partes.push(llenas(indices[0])[0]); continue; }
      const ancho = Math.max(...indices.map((i) => filas[i].length));
      const usadas = [...Array(ancho).keys()].filter((j) => indices.some((i) => filas[i][j]));   // sin columnas vacías
      if (usadas.length === 1) {                       // una sola columna: lista con viñetas
        partes.push(indices.map((i) => `- ${filas[i][usadas[0]]}`).join("\n"));
        continue;
      }
      const linea = (i) => `| ${usadas.map((j) => filas[i][j] || " ").join(" | ")} |`;
      // Encabezado: sin HTML se asume la primera fila; con HTML, solo si está en negrita (si no, la
      // tabla va sin encabezado y todas las filas son datos)
      const conEncabezado = !deHTML || usadas.every((j) => !filas[indices[0]][j] || deHTML.negritas[indices[0]][j]);
      const encabezado = conEncabezado ? linea(indices[0]) : `|${usadas.map(() => " ").join("|")}|`;
      const cuerpo = conEncabezado ? indices.slice(1) : indices;
      partes.push([encabezado, `|${usadas.map(() => "---").join("|")}|`, ...cuerpo.map(linea)].join("\n"));
    }
    return partes.join("\n\n");
  };
  window.excelAMarkdown = excelAMarkdown;
  // En el editor de notas (formato Markdown): <textarea @paste="pegarTabla($event)">
  window.pegarTabla = (e) => {
    const area = e.target;
    const formato = document.getElementById("n-formato");
    const texto = e.clipboardData?.getData("text/plain") || "";
    // Viene de una hoja de cálculo si trae tabuladores o si el HTML copiado es una tabla
    // (Excel y Google Sheets lo incluyen; así se reconoce también una lista de una sola columna)
    const deHoja = texto.includes("\t") || /<table/i.test(e.clipboardData?.getData("text/html") || "");
    if ((formato && formato.value !== "markdown") || !deHoja || !texto.trim()) return;
    e.preventDefault();
    let md = excelAMarkdown(texto, e.clipboardData?.getData("text/html") || "");
    const antes = area.value.slice(0, area.selectionStart);
    if (antes && !antes.endsWith("\n\n")) md = (antes.endsWith("\n") ? "\n" : "\n\n") + md;
    md += "\n\n";
    area.focus();
    // insertText conserva el «deshacer» (Ctrl/⌘+Z) y dispara la vista previa
    if (!document.execCommand("insertText", false, md)) {
      area.setRangeText(md, area.selectionStart, area.selectionEnd, "end");
      area.dispatchEvent(new Event("input", { bubbles: true }));
    }
    avisar("Tabla de Excel convertida a Markdown. Ctrl/⌘+Z para deshacer.");
  };

  // HTMX: el botón "atrás" vuelve a pedir la página (evita estados viejos de Alpine en caché).
  document.addEventListener("DOMContentLoaded", () => {
    if (window.htmx) {
      htmx.config.historyCacheSize = 0;
      htmx.config.refreshOnHistoryMiss = true;
    }
  });
  // ------------------------------------------------------------ confirmar
  // Ventana de confirmación con el estilo de la app. Devuelve una promesa con true/false.
  // Se usa en los botones que guardan, editan o eliminan (atributo hx-confirm o data-confirmar).
  const confirmar = (pregunta, { boton = "Sí, continuar", peligro = false } = {}) => new Promise((resolver) => {
    const dialogo = document.createElement("dialog");
    dialogo.className = "modal !w-[min(440px,calc(100vw-2rem))]";
    dialogo.setAttribute("role", "alertdialog");
    dialogo.innerHTML = `
      <div class="flex gap-4 px-6 pb-2 pt-6">
        <span class="grid size-11 shrink-0 place-items-center rounded-full ${peligro ? "bg-peligro-suave text-peligro" : "bg-marca-suave text-marca"}">
          <svg class="ic size-5"><use href="/static/vendor/lucide/sprite.svg#${peligro ? "triangle-alert" : "circle-help"}"/></svg></span>
        <p class="pt-2.5 text-base font-medium" data-pregunta></p>
      </div>
      <footer class="mt-4 flex justify-end gap-2 border-t border-borde bg-superficie-2/50 px-6 py-4">
        <button type="button" class="btn-secundario" data-no>Cancelar</button>
        <button type="button" class="${peligro ? "btn-peligro" : "btn-primario"}" data-si></button>
      </footer>`;
    dialogo.querySelector("[data-pregunta]").textContent = pregunta;
    dialogo.querySelector("[data-si]").textContent = boton;
    let respuesta = false;
    dialogo.querySelector("[data-si]").addEventListener("click", () => { respuesta = true; dialogo.close(); });
    dialogo.querySelector("[data-no]").addEventListener("click", () => dialogo.close());
    dialogo.addEventListener("close", () => { dialogo.remove(); resolver(respuesta); });
    document.body.appendChild(dialogo);
    dialogo.showModal();
    dialogo.querySelector("[data-si]").focus();
  });
  window.confirmar = confirmar;

  // Opciones desde atributos: data-confirmar-boton="Guardar" y data-confirmar-peligro
  const opcionesDe = (el) => {
    const origen = el.closest("[data-confirmar-boton], [data-confirmar-peligro]") || el;
    return { boton: origen.dataset.confirmarBoton || "Sí, continuar", peligro: origen.hasAttribute("data-confirmar-peligro") };
  };

  // HTMX: hx-confirm usa esta ventana en lugar del confirm() del navegador.
  document.addEventListener("htmx:confirm", (e) => {
    if (!e.detail.question) return;
    e.preventDefault();
    // HTMX hereda hx-confirm a lo que está dentro del formulario (p. ej. la vista previa de una nota
    // al escribir, o «Atrás» en un asistente): solo pregunta el elemento que lo declara él mismo.
    if (!e.detail.elt.hasAttribute("hx-confirm")) { e.detail.issueRequest(true); return; }
    confirmar(e.detail.question, opcionesDe(e.detail.elt)).then((si) => { if (si) e.detail.issueRequest(true); });
  });

  // Formularios normales (sin HTMX): <form data-confirmar="¿…?">
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.confirmar || form.dataset.confirmado) return;
    e.preventDefault();
    confirmar(form.dataset.confirmar, opcionesDe(form)).then((si) => {
      if (!si) return;
      form.dataset.confirmado = "1";
      form.requestSubmit(e.submitter || undefined);
    });
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
      // Un clic fuera del formulario NO lo cierra (se perdía lo escrito). Se cierra con la X,
      // «Cancelar» o Esc; si ya escribiste algo, primero pregunta si quieres descartarlo.
      init() {
        const dialogo = this.$el;
        dialogo.showModal();
        dialogo.addEventListener("close", () => dialogo.remove());
        dialogo.addEventListener("input", () => { dialogo.dataset.cambios = "1"; });
        dialogo.addEventListener("change", () => { dialogo.dataset.cambios = "1"; });
        dialogo.addEventListener("cancel", (e) => { e.preventDefault(); this.cerrar(); });   // tecla Esc
        const primero = dialogo.querySelector("[autofocus], input:not([type=hidden]), textarea, button");
        if (primero) primero.focus();
      },
      // Desde un botón, $el es el botón (no el <dialog>): se busca el diálogo que lo contiene.
      async cerrar(forzar = false) {
        const dialogo = this.$el.closest("dialog");
        if (!dialogo) return;
        if (!forzar && dialogo.dataset.cambios && !(await confirmar("¿Cerrar sin guardar? Se perderá lo que escribiste.",
                                                         { boton: "Cerrar sin guardar", peligro: true }))) return;
        dialogo.close();
      },
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
      async subir() {
        if (this.pendientes.some((p) => !p.titulo.trim())) { avisar("Escribe un nombre descriptivo para cada archivo.", "error"); return; }
        const n = this.pendientes.length;
        const que = tipo === "pdf" ? (n === 1 ? "este PDF" : `estos ${n} PDF`) : (n === 1 ? "esta imagen" : `estas ${n} imágenes`);
        if (!(await confirmar(`¿Guardar ${que} en la biblioteca?`, { boton: "Guardar" }))) return;
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
