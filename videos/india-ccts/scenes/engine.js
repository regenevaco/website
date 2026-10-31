// Deterministic timeline engine: every frame is a pure function of time t (seconds).
//
// Markup conventions inside a <section class="scene" id="...">:
//   class="a <preset>"   element animates in with a CSS preset (up, fade, pop, ...)
//   data-c="n"           cue = start of narration line n of this scene (default 0)
//   data-o="s"           extra offset in seconds after the cue
//   data-cd="s"          custom animation duration
//   data-x="n" data-xo   exit (fade out) at line n (+offset)
//   data-count="N"       number counts up to N (data-dec for decimals, data-cd duration)
//   <canvas data-draw="name">  redrawn every frame by window.DRAW[name](ctx, t, w, h, local)
(function () {
  const ENTER = { up: 0.9, down: 0.8, left: 0.9, right: 0.9, fade: 0.8, pop: 0.7, zoom: 1.1, growx: 1.1,
                  growy: 1.0, draw: 1.6, strike: 0.6, reveal: 1.0, blur: 1.0, rise: 1.2 };
  const PRESETS = Object.keys(ENTER);
  let T = null;
  const counters = [], scenes = [], canvases = [];

  window.DRAW = window.DRAW || {};

  function cueTime(info, c) {
    if (c === 'end') return info.dur;
    const l = info.lines[c];
    return l ? l.start : 0;
  }

  window.init = function (timing) {
    T = timing;
    if (window.beforeInit) window.beforeInit(T);
    T.scenes.forEach((info, i) => {
      const sec = document.getElementById(info.id);
      if (!sec) throw new Error('missing scene ' + info.id);
      const s0 = info.start;
      sec.style.zIndex = 10 + i;
      if (i > 0) sec.style.animation = `wipe 1.1s cubic-bezier(.77,0,.18,1) ${s0}s both paused`;
      scenes.push({ el: sec, start: s0, end: s0 + info.dur, info });
      if (window.decorate && window.decorate[info.id]) window.decorate[info.id](sec, info);
      sec.querySelectorAll('.a').forEach(el => {
        const preset = PRESETS.find(p => el.classList.contains(p)) || 'fade';
        const c = el.dataset.c === 'end' ? 'end' : +(el.dataset.c || 0);
        const o = +(el.dataset.o || 0);
        const dur = +(el.dataset.cd || ENTER[preset]);
        const at = s0 + cueTime(info, c) + o + (i > 0 ? 0.3 : 0);
        const ease = el.dataset.ease || 'cubic-bezier(.16,1,.3,1)';
        let anim = `${preset} ${dur}s ${ease} ${at.toFixed(3)}s both paused`;
        if (el.dataset.x !== undefined) {
          const xc = el.dataset.x === 'end' ? 'end' : +el.dataset.x;
          const xat = s0 + cueTime(info, xc) + +(el.dataset.xo || 0);
          anim += `, out 0.55s cubic-bezier(.7,0,.84,0) ${xat.toFixed(3)}s forwards paused`;
        }
        el.style.animation = anim;
      });
      sec.querySelectorAll('[data-count]').forEach(el => {
        const host = el.closest('[data-c]');
        const c = +((el.dataset.c !== undefined ? el.dataset.c : host && host.dataset.c) || 0);
        const o = +(el.dataset.o !== undefined ? el.dataset.o : (host && host.dataset.o) || 0);
        counters.push({ el, to: +el.dataset.count, dec: +(el.dataset.dec || 0), from: +(el.dataset.from || 0),
                        at: s0 + cueTime(info, c) + o + 0.35, dur: +(el.dataset.cd || 1.8) });
      });
      sec.querySelectorAll('canvas[data-draw]').forEach(cv => {
        const dpr = window.devicePixelRatio || 1;
        const r = { w: +cv.getAttribute('width'), h: +cv.getAttribute('height') };
        cv.style.width = r.w + 'px'; cv.style.height = r.h + 'px';
        cv.width = r.w * dpr; cv.height = r.h * dpr;
        const ctx = cv.getContext('2d');
        ctx.scale(dpr, dpr);
        canvases.push({ cv, ctx, w: r.w, h: r.h, fn: cv.dataset.draw, scene: scenes[scenes.length - 1] });
      });
    });
    const prog = document.getElementById('prog');
    if (prog) T.scenes.slice(1).forEach(s => {
      const m = document.createElement('s'); m.style.left = (s.start / T.total * 100) + '%'; prog.appendChild(m);
    });
    document.getAnimations().forEach(a => a.pause());
  };

  window.setTime = function (t) {
    scenes.forEach((s, i) => {
      const next = scenes[i + 1];
      const visible = t >= s.start - 0.05 && t < (next ? next.start + 1.2 : Infinity);
      const d = visible ? 'block' : 'none';
      if (s.el.style.display !== d) s.el.style.display = d;
    });
    document.getAnimations().forEach(a => { a.currentTime = t * 1000; });
    counters.forEach(c => {
      const p = Math.min(1, Math.max(0, (t - c.at) / c.dur));
      const e = 1 - Math.pow(1 - p, 4);
      const v = c.from + (c.to - c.from) * e;
      c.el.textContent = v.toLocaleString('en-IN', { minimumFractionDigits: c.dec, maximumFractionDigits: c.dec });
    });
    canvases.forEach(c => {
      if (c.scene.el.style.display === 'none') return;
      const local = t - c.scene.start;
      c.ctx.clearRect(0, 0, c.w, c.h);
      const f = window.DRAW[c.fn];
      if (f) f(c.ctx, t, c.w, c.h, local, c.scene.info);
    });
    const p = document.querySelector('#prog i');
    if (p) p.style.width = (t / T.total * 100) + '%';
    const lab = document.getElementById('chap');
    if (lab) {
      let cur = scenes[0];
      scenes.forEach(s => { if (t >= s.start) cur = s; });
      const txt = cur.info.chapter;
      if (lab.dataset.txt !== txt) { lab.dataset.txt = txt; lab.textContent = txt; }
      const onCard = cur.info.cardEnd !== undefined && t - cur.start < cur.info.cardEnd + 0.4;
      document.body.dataset.tone = onCard ? 'dark' : cur.info.tone;
    }
  };

  // seeded PRNG for canvases
  window.rng = function (seed) {
    let s = seed >>> 0;
    return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  };
})();
