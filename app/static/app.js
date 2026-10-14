// Menú lateral plegable: se recuerda la elección en este navegador.
(() => {
  "use strict";
  const root = document.documentElement;
  const btn = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  if (!btn || !sidebar) return;

  const KEY = "sidebar-collapsed";
  const sync = () => {
    const collapsed = root.dataset.sidebar === "collapsed";
    const label = collapsed ? "Desplegar menú" : "Replegar menú";
    btn.setAttribute("aria-expanded", String(!collapsed));
    btn.setAttribute("aria-label", label);
    btn.title = label;
  };
  btn.addEventListener("click", () => {
    const collapse = root.dataset.sidebar !== "collapsed";
    root.dataset.sidebar = collapse ? "collapsed" : "expanded";
    try { localStorage.setItem(KEY, collapse ? "1" : "0"); } catch (e) { /* sin almacenamiento: no se recuerda */ }
    sync();
  });
  // Al terminar la animación, avisa para que la tabla reacomode sus columnas al nuevo ancho.
  sidebar.addEventListener("transitionend", (e) => {
    if (e.propertyName === "width") window.dispatchEvent(new Event("resize"));
  });
  sync();
})();
