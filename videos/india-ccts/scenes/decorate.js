// Generated markup: chapter cards, glossary, evolution camera pan.
(function () {
  const GLOSS = [
    { t: 'Greenhouse gases', k: 'GHG', d: 'Gases that trap heat in the atmosphere.', v: '<div class="mols"><span><i>CO<sub>2</sub></i></span><span><i>CH<sub>4</sub></i></span><span><i>N<sub>2</sub>O</i></span></div>' },
    { t: 'CO<sub>2</sub> equivalent', k: 'CO<sub>2</sub>e', d: 'One common unit for every gas, weighted by its warming effect.', v: '<div class="eqv"><span>CO<sub>2</sub></span><span>CH<sub>4</sub></span><span>N<sub>2</sub>O</span><i class="fa-solid fa-arrow-right"></i><b>tCO<sub>2</sub>e</b></div>' },
    { t: 'Emissions intensity', k: 'GEI', d: 'Emissions per unit of output. CCTS targets intensity, not an absolute cap.', v: '<div class="frac"><b>tCO<sub>2</sub>e</b><hr><span>tonne of product</span></div>' },
    { t: 'Baseline & target', k: 'BASE', d: 'Baseline: the 2023-24 starting point. Target: the lower intensity required in a compliance year.', v: '<div class="bt"><i style="height:100%"><span>2023-24<br>baseline</span></i><i class="g" style="height:88%"><span>2025-26</span></i><i class="g" style="height:80%"><span>2026-27</span></i><em>Illustrative</em></div>' },
    { t: 'Carbon Credit Certificate', k: 'CCC', d: 'One tonne of CO<sub>2</sub>e reduced, removed or avoided.', v: '<div class="ccc"><small>CARBON CREDIT CERTIFICATE</small><b>1 CCC</b><span>= 1 tCO<sub>2</sub>e</span></div>' },
    { t: 'Monitoring, Reporting & Verification', k: 'MRV', d: 'How every tonne is measured, reported and independently checked.', v: '<div class="mrv"><span><i class="fa-solid fa-gauge-high"></i>Monitor</span><span><i class="fa-solid fa-file-lines"></i>Report</span><span><i class="fa-solid fa-magnifying-glass"></i>Verify</span></div>' },
    { t: 'Not all certificates are carbon credits', k: 'UNITS', d: 'Each certificate measures something different.', v: '<div class="units"><div><b>ESCert</b><span>PAT scheme</span><em>1 toe energy saved</em></div><div><b>REC</b><span>Renewable Energy Certificate</span><em>1 MWh green power</em></div><div class="g"><b>CCC</b><span>CCTS</span><em>1 tCO<sub>2</sub>e</em></div></div>' }
  ];

  window.decorate = {
    global(sec) {
      // EU CBAM: share of embedded emissions charged, 2026-2034 (free allocation phase-out)
      const pct = [2.5, 5, 10, 22.5, 48.5, 61, 73.5, 86, 100];
      const box = sec.querySelector('#pbars');
      pct.forEach((v, i) => {
        const d = document.createElement('div');
        d.className = 'pb';
        d.innerHTML = `<em class="a fade" data-c="3" data-o="${(1 + i * 0.5).toFixed(1)}">${v}%</em><i class="a growy" data-c="3" data-o="${(0.8 + i * 0.5).toFixed(1)}" style="height:${Math.max(4, v * 4.2)}px"></i><span>${2026 + i}</span>`;
        box.appendChild(d);
      });
    },
    terms(sec) {
      const idx = sec.querySelector('#glossIndex');
      const stage = sec.querySelector('#glossStage');
      GLOSS.forEach((g, i) => {
        const c = i + 1;
        const row = document.createElement('div');
        row.className = 'gi a fade';
        row.dataset.c = '1'; row.dataset.o = (0.2 + i * 0.12).toFixed(2);
        row.innerHTML = `<span class="gn">${String(c).padStart(2, '0')}</span><span>${g.k}</span><i class="hl a fade" data-c="${c}" data-x="${c + 1}" data-xo="-0.25"></i>`;
        idx.appendChild(row);
        const card = document.createElement('div');
        card.className = 'gcard a up';
        card.dataset.c = String(c);
        if (c < GLOSS.length) { card.dataset.x = String(c + 1); card.dataset.xo = '-0.3'; }
        card.innerHTML = `<div class="gk">${g.k}</div><h3>${g.t}</h3><p>${g.d}</p><div class="gv a fade" data-c="${c}" data-o="0.6">${g.v}</div>`;
        stage.appendChild(card);
      });
    }
  };

  // chapter cards for every scene that asks for one
  window.beforeInit = function (T) {
    T.scenes.forEach((info, i) => {
      const sec = document.getElementById(info.id);
      const kind = sec.dataset.card;
      if (kind) {
        const card = document.createElement('div');
        card.className = 'chapcard a fade';
        card.dataset.cd = '0.05';
        if (kind === 'long') { card.dataset.x = '1'; card.dataset.xo = '-0.35'; }
        else { card.dataset.x = '0'; card.dataset.xo = '1.6'; }
        card.innerHTML = `<div class="cn a up" data-o="0.1">${String(i).padStart(2, '0')}</div>
          <div class="cline a growx" data-o="0.25"></div>
          <div class="ct a up" data-o="0.35">${info.chapter}</div>`;
        sec.appendChild(card);
        info.cardEnd = kind === 'long' ? (info.lines[1] ? info.lines[1].start - 0.35 : 2) : (info.lines[0].start + 1.6);
      }
      if (sec.dataset.src) {
        const s = document.createElement('div');
        s.className = 'src a fade'; s.dataset.c = '1'; s.dataset.o = '0';
        if (kind !== 'long') { s.dataset.c = '0'; s.dataset.o = '2.4'; }
        s.innerHTML = sec.dataset.src;
        sec.appendChild(s);
      }
    });
    // evolution: camera pans across the timeline as nodes appear
    const ev = T.scenes.find(s => s.id === 'evolution');
    const track = document.getElementById('tltrack');
    if (ev && track) {
      const steps = [[1, 0], [3, -460], [5, -1460], [6, -1920]];
      const kf = [];
      const total = ev.dur;
      steps.forEach(([line, x]) => {
        const at = (ev.lines[line].start + 0.2) / total;
        kf.push({ offset: Math.min(0.98, at), transform: `translateX(${x}px)` });
      });
      kf.sort((a, b) => a.offset - b.offset);
      // hold between moves: duplicate each target just before the next move
      const frames = [{ offset: 0, transform: 'translateX(0px)' }];
      kf.forEach((k, j) => {
        if (j > 0) frames.push({ offset: Math.max(frames[frames.length - 1].offset, k.offset - 0.03), transform: kf[j - 1].transform });
        frames.push(k);
      });
      frames.push({ offset: 1, transform: kf[kf.length - 1].transform });
      const a = track.animate(frames, { duration: total * 1000, delay: ev.start * 1000, fill: 'both', easing: 'linear' });
      a.pause();
    }
  };
})();
