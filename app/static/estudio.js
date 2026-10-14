(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  // Construcción de DOM con textContent: el contenido del Excel nunca se interpreta como HTML.
  const h = (tag, props = {}, ...kids) => {
    const n = Object.assign(document.createElement(tag), props);
    kids.flat().forEach((k) => n.append(k));
    return n;
  };
  const icon = (name, cls = "ic") => {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("class", cls);
    s.innerHTML = `<use href="#i-${name}"/>`; // nombre de ícono propio, no viene del Excel
    return s;
  };
  const toast = (msg, type = "info") => {
    const t = h("div", { className: "toast " + type, textContent: msg });
    $("#toasts").append(t);
    setTimeout(() => t.remove(), 5000);
  };

  const state = {
    meta: null, records: [], mode: "filters", page: 1, pageSize: 25,
    sort: { key: null, desc: false }, current: null, uploadTarget: null,
  };
  const ADJ_WIDTH = 130;
  // En la pestaña Filtros se ocultan las columnas que tienen filtro propio (p. ej. "Otros síntomas");
  // en Registros y en la ficha se muestran todas.
  const tableFields = () => state.meta.fields.filter((f) => !(state.mode === "filters" && f.hide_in_filters));
  const editable = () => state.mode === "all"; // las imágenes solo se gestionan desde "Registros"

  const api = async (url, opts) => {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error((await r.text()) || r.statusText);
    return r.json();
  };

  // ---------------------------------------------------------------- tabla
  // Anchos efectivos: las columnas de texto largo se encogen (hasta un mínimo legible) para
  // aprovechar el ancho disponible y reducir el scroll horizontal; las cortas no cambian.
  function effectiveWidths() {
    const fields = tableFields();
    const avail = $("#table-scroll").clientWidth || 0;
    const isLong = (f) => f.width >= 220;
    const fixed = fields.filter((f) => !isLong(f)).reduce((t, f) => t + f.width, ADJ_WIDTH);
    const flex = fields.filter(isLong).reduce((t, f) => t + f.width, 0);
    const factor = flex && avail ? Math.min(1, Math.max(0.6, (avail - fixed) / flex)) : 1;
    return Object.fromEntries(fields.map((f) => [f.key, Math.round(isLong(f) ? f.width * factor : f.width)]));
  }

  function renderHead() {
    const fields = tableFields();
    const widths = effectiveWidths();
    $("#records-table").style.minWidth = fields.reduce((t, f) => t + widths[f.key], ADJ_WIDTH) + "px"; // se estira si sobra espacio
    $("#records-table thead").replaceChildren(
      h("tr", {}, ...fields.map((f, i) => {
        const th = h("th", { className: (i === 0 ? "sticky " : "") + (state.sort.key === f.key ? "sorted" + (state.sort.desc ? " desc" : "") : "") },
          h("div", { className: "th-in" }, h("span", { textContent: f.label }), h("i", { className: "sort" })));
        th.style.width = widths[f.key] + "px";
        th.onclick = () => {
          state.sort = { key: f.key, desc: state.sort.key === f.key && !state.sort.desc };
          state.page = 1;
          renderTable();
        };
        return th;
      }), Object.assign(h("th", { className: "col-adjuntos", style: `width:${ADJ_WIDTH}px;cursor:default` }), { textContent: "Imágenes" }))
    );
  }

  function pageList(cur, total) {
    const set = new Set([1, total, cur - 1, cur, cur + 1].filter((p) => p >= 1 && p <= total));
    const pages = [...set].sort((a, b) => a - b);
    return pages.flatMap((p, i) => (i && p - pages[i - 1] > 1 ? ["…", p] : [p]));
  }

  function renderPager(total, pages) {
    const go = (p) => { state.page = p; renderTable(); };
    const btn = (content, label, onclick, extra = {}) =>
      h("button", Object.assign({ className: "pg", type: "button", title: label, ariaLabel: label, onclick }, extra), content);
    $("#pager-nav").replaceChildren(
      btn(icon("left"), "Página anterior", () => go(state.page - 1), { disabled: state.page <= 1 }),
      ...pageList(state.page, pages).map((p) => p === "…"
        ? h("span", { className: "pg-gap", textContent: "…" })
        : btn(String(p), `Ir a la página ${p}`, () => go(p), p === state.page ? { className: "pg current", disabled: false } : {})),
      btn(icon("right"), "Página siguiente", () => go(state.page + 1), { disabled: state.page >= pages })
    );
  }

  function renderTable(keepScroll = false) {
    const fields = tableFields();
    const box = $("#table-scroll"), pos = { top: box.scrollTop, left: box.scrollLeft };
    renderHead();

    const rows = [...state.records];
    if (state.sort.key) {
      const k = state.sort.key;
      rows.sort((a, b) => a[k].localeCompare(b[k], "es", { sensitivity: "base", numeric: true }));
      if (state.sort.desc) rows.reverse();
    }
    const pages = Math.max(1, Math.ceil(rows.length / state.pageSize));
    state.page = Math.min(state.page, pages);
    const start = (state.page - 1) * state.pageSize;
    const end = Math.min(start + state.pageSize, rows.length);

    $("#records-table").setAttribute("aria-busy", "false");
    $("#records-table tbody").replaceChildren(
      ...rows.slice(start, end).map((r) => {
        const tr = h("tr", {}, ...fields.map((f, i) =>
          h("td", { className: i === 0 ? "sticky" : "" }, h("div", { className: "pre", textContent: r[f.key] }))),
          h("td", { className: "col-adjuntos" }, imageCell(r)));
        tr.onclick = () => openDetail(r);
        return tr;
      })
    );
    $("#empty").hidden = rows.length > 0;
    $("#records-table").hidden = rows.length === 0;
    $("#pager").hidden = rows.length === 0;
    $("#summary").textContent = rows.length ? `${start + 1}–${end} de ${rows.length}` : "";
    $("#result-chip").textContent = `${rows.length} ${rows.length === 1 ? "resultado" : "resultados"}`;
    renderPager(rows.length, pages);
    if (keepScroll) { box.scrollTop = pos.top; box.scrollLeft = pos.left; } else box.scrollTop = 0;
  }

  // Celda "Imágenes": en Filtros solo ver; en Registros además agregar.
  function imageCell(r) {
    const act = (name, text, title, cls, onclick, count) => {
      const b = h("button", { type: "button", className: "icon-btn " + cls, title });
      b.append(icon(name), text);
      if (count > 1) b.append(h("span", { className: "n", textContent: String(count) }));
      b.onclick = (e) => { e.stopPropagation(); onclick(); };
      return b;
    };
    const view = r.adjuntos ? act("eye", "Ver imagen", r.adjuntos > 1 ? "Ver imágenes" : "Ver imagen", "", () => openViewer(r), r.adjuntos) : null;
    if (!editable()) return h("div", { className: "img-cell" }, view || h("span", { className: "none", textContent: "—" }));
    const add = act("plus", "Agregar", "Agregar imágenes", "primary", () => {
      state.uploadTarget = r;
      $("#row-file-input").click();
    });
    return h("div", { className: "img-cell" }, add, view || "");
  }

  function renderSkeleton() {
    const n = tableFields().length + 1;
    renderHead();
    $("#records-table tbody").replaceChildren(...Array.from({ length: 6 }, () =>
      h("tr", { className: "skeleton" }, ...Array.from({ length: n }, () => h("td", {}, h("i")))))
    );
  }

  async function load() {
    const params = new URLSearchParams();
    if (state.mode === "filters") {
      new FormData($("#filter-form")).forEach((v, k) => v && params.set(k, v));
    }
    const data = await api("/api/records?" + params);
    state.records = data.records;
    state.page = 1;
    renderTable();
  }
  let timer;
  const loadSoon = () => { clearTimeout(timer); timer = setTimeout(() => load().catch((e) => toast(e.message, "error")), 200); };

  // -------------------------------------------------------------- filtros
  const stripAccents = (c) => c.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

  // Resalta la coincidencia (sin acentos ni mayúsculas) usando solo nodos de texto.
  function highlight(text, q) {
    let norm = "", map = [];
    [...text].forEach((ch, i) => { for (const c of stripAccents(ch)) { norm += c; map.push(i); } });
    const nq = [...q.trim()].map(stripAccents).join("");
    const at = nq ? norm.indexOf(nq) : -1;
    if (at < 0) return [text];
    const from = map[at], to = map[at + nq.length - 1] + 1;
    return [text.slice(0, from), h("mark", { textContent: text.slice(from, to) }), text.slice(to)];
  }

  // Cuadro de texto con sugerencias propias: solo aparecen mientras se escribe (sin flecha ni lista al enfocar).
  function autocomplete(key, placeholder) {
    const input = h("input", { id: "f-" + key, name: key, type: "text", placeholder, autocomplete: "off" });
    const clear = h("button", { type: "button", className: "input-clear", title: "Borrar", hidden: true, ariaLabel: "Borrar" }, icon("x", "ic"));
    const list = h("ul", { className: "ac-list", hidden: true });
    let items = [], active = -1, seq = 0, t;

    const hide = () => { list.hidden = true; active = -1; };
    const mark = () => [...list.children].forEach((li, i) => li.classList.toggle("active", i === active));
    const pick = (v) => { input.value = v; clear.hidden = false; hide(); load(); };
    const show = () => {
      list.replaceChildren(...items.map((v) => {
        const li = h("li", {}, ...highlight(v, input.value));
        li.onmousedown = (e) => { e.preventDefault(); pick(v); };
        return li;
      }));
      list.hidden = items.length === 0;
      active = -1;
    };

    input.addEventListener("input", () => {
      clearTimeout(t);
      clear.hidden = !input.value;
      loadSoon();
      if (!input.value.trim()) { hide(); return; }
      const mine = ++seq;
      t = setTimeout(async () => {
        const res = await api(`/api/suggest?field=${key}&q=${encodeURIComponent(input.value)}`).catch(() => []);
        if (mine === seq) { items = res; show(); }
      }, 120);
    });
    input.addEventListener("keydown", (e) => {
      if (list.hidden) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        active = (active + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        mark();
      } else if (e.key === "Enter" && active >= 0) {
        e.preventDefault();
        pick(items[active]);
      } else if (e.key === "Escape") hide();
    });
    input.addEventListener("blur", hide);
    clear.onclick = () => { input.value = ""; clear.hidden = true; hide(); load(); input.focus(); };
    return h("div", { className: "ac" }, h("div", { className: "input-wrap" }, icon("search"), input, clear), list);
  }

  function buildFilters() {
    $("#filter-fields").replaceChildren(...state.meta.filters.map(({ key, label, placeholder }) =>
      h("div", { className: "field" }, h("label", { htmlFor: "f-" + key, textContent: label }), autocomplete(key, placeholder))));
  }

  // -------------------------------------------------------------- detalle
  const isShort = (v) => v.length <= 48 && !v.includes("\n");

  function openDetail(rec) {
    state.current = rec;
    $("#detail-title").textContent = rec.titulo;
    $("#detail-sub").textContent = `Fila ${rec.row} del Excel`;

    // Respeta el orden del Excel: campos cortos agrupados en rejilla, textos largos en bloques.
    const out = [];
    let grid = null;
    state.meta.fields.filter((f) => rec[f.key].trim()).forEach((f) => {
      const v = rec[f.key];
      if (isShort(v)) {
        if (!grid) { grid = h("div", { className: "fgrid" }); out.push(grid); }
        grid.append(h("div", { className: "fcard" },
          h("div", { className: "flabel", textContent: f.label }), h("div", { className: "fvalue", textContent: v })));
      } else {
        grid = null;
        out.push(h("div", { className: "fblock" },
          h("div", { className: "flabel", textContent: f.label }), h("div", { className: "fvalue", textContent: v })));
      }
    });
    $("#detail-fields").replaceChildren(...out);
    $("#edit-zone").hidden = !editable();
    $("#upload-msg").textContent = "";
    $("#detail .dialog-body").scrollTop = 0;
    loadGallery();
    $("#detail").showModal();
  }

  async function loadGallery() {
    const rec = state.current;
    const items = await api(`/api/records/${rec.id}/attachments`);
    $("#gallery").replaceChildren(...items.map((a, i) => {
      const img = h("img", { src: a.url, alt: a.name, loading: "lazy" });
      img.onclick = () => openViewer(rec, i);
      const thumb = h("div", { className: "thumb" }, img);
      if (editable()) {
        const del = h("button", { className: "del", title: "Eliminar", ariaLabel: "Eliminar imagen" }, icon("trash"));
        del.onclick = async () => {
          if (!confirm(`¿Eliminar la imagen "${a.name}"?`)) return;
          await api(`/api/attachments/${a.id}`, { method: "DELETE" });
          await loadGallery();
        };
        thumb.append(del);
      }
      thumb.append(h("div", { className: "cap", textContent: a.name, title: a.name }));
      return thumb;
    }));
    if (!items.length) $("#gallery").append(h("p", { className: "empty-note small", textContent: "Este registro aún no tiene imágenes." }));
    setCount(rec, items.length);
  }

  function setCount(rec, n) {
    if (rec.adjuntos !== n) { rec.adjuntos = n; renderTable(true); }
  }

  async function upload(rec, files, msgEl) {
    if (!files.length) return;
    const fd = new FormData();
    [...files].forEach((f) => fd.append("files", f));
    try {
      const res = await api(`/api/records/${rec.id}/attachments`, { method: "POST", body: fd });
      if (msgEl) msgEl.textContent = res.errors.join(" · ");
      else if (res.errors.length) toast(res.errors.join(" · "), "error");
      if (res.added.length) toast(`${res.added.length > 1 ? res.added.length + " imágenes agregadas" : "Imagen agregada"} a ${rec.titulo}`);
      setCount(rec, rec.adjuntos + res.added.length);
    } catch (e) {
      if (msgEl) msgEl.textContent = "Error al subir: " + e.message;
      else toast("Error al subir: " + e.message, "error");
    }
    if (state.current === rec && $("#detail").open) await loadGallery();
  }

  // ------------------------------------------------------- visor (modal)
  const viewer = { items: [], i: 0, rec: null };

  async function openViewer(rec, start = 0) {
    viewer.rec = rec;
    viewer.items = await api(`/api/records/${rec.id}/attachments`);
    if (!viewer.items.length) return;
    viewer.i = Math.min(start, viewer.items.length - 1);
    renderViewer();
    if (!$("#viewer").open) $("#viewer").showModal();
  }

  function renderViewer() {
    const a = viewer.items[viewer.i], n = viewer.items.length;
    $("#viewer-title").textContent = viewer.rec.titulo;
    $("#viewer-img").src = a.url;
    $("#viewer-img").alt = a.name;
    $("#viewer-caption").textContent = `${a.name} · ${viewer.i + 1} de ${n}`;
    $("#viewer-prev").hidden = $("#viewer-next").hidden = n < 2;
  }
  const stepViewer = (d) => {
    const n = viewer.items.length;
    viewer.i = (viewer.i + d + n) % n;
    renderViewer();
  };

  // ----------------------------------------------------------------- init
  function applyMeta() {
    $("#tab-count").textContent = state.meta.total;
    const at = state.meta.loaded_at && new Date(state.meta.loaded_at);
    if (at && !isNaN(at)) {
      $("#loaded-at").textContent = `Excel leído a las ${at.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })}`;
      $("#loaded-at").hidden = false;
    }
    buildFilters();
  }

  async function init() {
    state.meta = await api("/api/meta");
    applyMeta();
    renderSkeleton();

    document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => {
      document.querySelectorAll(".tab").forEach((x) => {
        x.classList.toggle("active", x === t);
        x.setAttribute("aria-selected", x === t);
      });
      state.mode = t.dataset.tab;
      if (!tableFields().some((f) => f.key === state.sort.key)) state.sort = { key: null, desc: false };
      $("#tab-filters").hidden = state.mode !== "filters";
      load();
    }));
    $("#page-size").onchange = (e) => { state.pageSize = +e.target.value; state.page = 1; renderTable(); };
    $("#btn-clear").onclick = () => {
      $("#filter-form").reset();
      document.querySelectorAll(".input-clear").forEach((b) => (b.hidden = true));
      load();
    };
    $("#filter-form").onsubmit = (e) => e.preventDefault();
    $("#btn-reload").onclick = async () => {
      try {
        await api("/api/reload", { method: "POST" });
        state.meta = await api("/api/meta");
        state.sort = { key: null, desc: false };
        applyMeta();
        await load();
        toast("Excel recargado");
      } catch (e) { toast("No se pudo recargar: " + e.message, "error"); }
    };

    $("#detail-close").onclick = () => $("#detail").close();
    $("#detail").addEventListener("click", (e) => { if (e.target.id === "detail") $("#detail").close(); });
    $("#viewer-close").onclick = () => $("#viewer").close();
    $("#viewer-prev").onclick = () => stepViewer(-1);
    $("#viewer-next").onclick = () => stepViewer(1);
    $("#viewer").addEventListener("click", (e) => { if (e.target.id === "viewer") $("#viewer").close(); });
    $("#viewer").addEventListener("keydown", (e) => {
      if (viewer.items.length > 1 && e.key === "ArrowLeft") stepViewer(-1);
      if (viewer.items.length > 1 && e.key === "ArrowRight") stepViewer(1);
    });
    $("#viewer").addEventListener("close", () => $("#viewer-img").removeAttribute("src"));
    $("#file-input").onchange = (e) => { upload(state.current, e.target.files, $("#upload-msg")); e.target.value = ""; };
    $("#row-file-input").onchange = async (e) => {
      await upload(state.uploadTarget, e.target.files, null);
      e.target.value = "";
    };
    const dz = $("#dropzone");
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
    dz.addEventListener("drop", (e) => upload(state.current, e.dataTransfer.files, $("#upload-msg")));

    let rz;
    window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => renderTable(true), 150); });

    await load();
  }
  init().catch((e) => {
    $("#empty").hidden = false;
    $("#empty strong").textContent = "No se pudo cargar la información";
    $("#empty span").textContent = e.message;
  });
})();
