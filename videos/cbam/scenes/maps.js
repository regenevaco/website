// Builds the EU and world maps from geo.js before the engine scans for cues.
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    if (parent) parent.appendChild(e);
    return e;
  };
  const prev = window.beforeInit;
  window.beforeInit = function (T) {
    const G = window.GEO;
    // ---- EU map (who): reports filed, Germany / Italy / Poland
    const eu = document.getElementById('euSvg');
    if (eu && !eu.children.length) {
      const base = el('g', { class: 'base' }, eu);
      Object.entries(G.eu.p).forEach(([id, d]) => el('path', { d, class: G.eu.eu.includes(id) ? 'eu' : 'non' }, base));
      const hot = [['276', 'Germany', 15.1, [0, -6]], ['380', 'Italy', 15.8, [-30, 8]], ['616', 'Poland', 16.5, [10, -4]]];
      hot.forEach(([id, name, o, dxy]) => {
        el('path', { d: G.eu.p[id], class: 'hot a fade', 'data-c': '3', 'data-o': String(o) }, eu);
      });
      hot.forEach(([id, name, o, dxy]) => {
        const [x, y] = G.eu.c[id];
        const t = el('text', { x: x + dxy[0], y: y + dxy[1], class: 'lab a fade', 'data-c': '3', 'data-o': String(o + 0.3) }, eu);
        t.textContent = name;
      });
    }
    // ---- world map (global): shares and main origins
    const w = document.getElementById('worldSvg');
    if (w && !w.children.length) {
      const base = el('g', { class: 'base' }, w);
      Object.entries(G.world.p).forEach(([id, d]) => el('path', { d, class: G.eu.eu.includes(id) ? 'eu' : 'non' }, base));
      [['156', 5.6], ['356', 11.0], ['643', 13.1]].forEach(([id, o]) =>
        el('path', { d: G.world.p[id], class: 'hot a fade', 'data-c': '4', 'data-o': String(o) }, w));
      const [ex, ey] = G.world.eu;
      const orig = [['792', 'Türkiye', [0, -30]], ['156', 'China', [10, -34]], ['356', 'India', [-6, 44]], ['124', 'Canada', [0, -30]], ['158', 'Taiwan', [44, 6]], ['704', 'Vietnam', [8, 44]]];
      const arcs = el('g', { class: 'arcs' }, w);
      orig.forEach(([id, name, dxy], i) => {
        const [x, y] = G.world.c[id];
        const o = [6.7, 7.2, 8.0, 8.7, 9.2, 9.9][i].toFixed(1);       // as each country is named
        const mx = (x + ex) / 2, my = Math.min(y, ey) - 60 - Math.abs(x - ex) * 0.12;
        el('path', { d: `M${x} ${y} Q${mx} ${my} ${ex} ${ey}`, class: 'arc a draw', pathLength: '1000', 'data-c': '5', 'data-o': o, 'data-cd': '1.2' }, arcs);
        el('circle', { cx: x, cy: y, r: 9, class: 'dot a pop', 'data-c': '5', 'data-o': o }, w);
        const t = el('text', { x: x + dxy[0], y: y + dxy[1], class: 'olab a fade', 'data-c': '5', 'data-o': o }, w);
        t.textContent = name;
      });
      el('circle', { cx: ex, cy: ey, r: 12, class: 'eud a pop', 'data-c': '4', 'data-o': '0.6' }, w);
      const t = el('text', { x: ex - 4, y: ey - 22, class: 'eulab a fade', 'data-c': '4', 'data-o': '0.8' }, w);
      t.textContent = 'EU';
    }
    if (prev) prev(T);
  };
})();
