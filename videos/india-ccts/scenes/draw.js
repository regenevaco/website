// Procedural canvas layers. Each function is deterministic in t (no Math.random).
(function () {
  const G = '#20C997';
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const ease = x => 1 - Math.pow(1 - clamp(x), 3);
  const cue = (info, i) => (info.lines[i] ? info.lines[i].start : 0);

  // ---------- cinematic night factory skyline with smoke (hook) ----------
  function building(ctx, x, base, scale, glow, t) {
    ctx.save();
    ctx.translate(x, base);
    ctx.scale(scale, scale);
    ctx.fillStyle = '#0b1210';
    // main hall
    ctx.fillRect(-260, -150, 520, 150);
    // saw-tooth roof
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      ctx.moveTo(-260 + i * 87, -150);
      ctx.lineTo(-260 + i * 87 + 60, -195);
      ctx.lineTo(-260 + i * 87 + 87, -150);
    }
    ctx.fill();
    // preheater tower + silo + kiln
    ctx.fillRect(-200, -380, 90, 230);
    ctx.fillRect(-215, -400, 120, 22);
    ctx.fillRect(40, -260, 80, 110);
    ctx.beginPath(); ctx.ellipse(80, -260, 40, 12, 0, 0, Math.PI * 2); ctx.fill();
    ctx.save(); ctx.translate(-110, -60); ctx.rotate(-0.08); ctx.fillRect(0, -18, 330, 36); ctx.restore();
    // chimneys
    ctx.fillRect(150, -470, 34, 320);
    ctx.fillRect(205, -420, 26, 270);
    // windows
    for (let r = 0; r < 3; r++) for (let c = 0; c < 9; c++) {
      const flick = 0.55 + 0.45 * Math.sin(t * 0.7 + r * 3.1 + c * 1.7);
      ctx.fillStyle = `rgba(${glow}, ${0.18 + 0.25 * flick})`;
      ctx.fillRect(-240 + c * 52, -130 + r * 38, 26, 14);
    }
    for (let r = 0; r < 6; r++) {
      ctx.fillStyle = `rgba(${glow}, 0.35)`;
      ctx.fillRect(-185, -360 + r * 36, 60, 8);
    }
    // aviation lights
    const blink = (Math.sin(t * 3) > 0.6) ? 1 : 0.25;
    ctx.fillStyle = `rgba(255,70,60,${blink})`;
    ctx.beginPath(); ctx.arc(167, -474, 5, 0, 7); ctx.fill();
    ctx.restore();
  }

  function smoke(ctx, x, y, t, density, tint, seed) {
    const R = window.rng(seed);
    const n = Math.round(70 * density);
    for (let i = 0; i < n; i++) {
      const phase = R(), drift = R(), size = R();
      const life = 9;
      const age = ((t / life + phase) % 1);
      const px = x + age * 260 * (0.6 + drift) + Math.sin(t * 0.5 + i) * 12 * age;
      const py = y - age * 330 - drift * 30;
      const r = 14 + age * 120 * (0.5 + size);
      const a = (1 - age) * 0.16 * density;
      const g = ctx.createRadialGradient(px, py, 0, px, py, r);
      g.addColorStop(0, `rgba(${tint},${a})`);
      g.addColorStop(1, `rgba(${tint},0)`);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(px, py, r, 0, 7); ctx.fill();
    }
  }

  window.DRAW.factory = function (ctx, t, w, h, local, info) {
    const push = 1 + local * 0.006;
    ctx.save();
    ctx.translate(w / 2, h / 2); ctx.scale(push, push); ctx.translate(-w / 2, -h / 2);
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#000');
    sky.addColorStop(0.65, '#04110c');
    sky.addColorStop(1, '#0a1f17');
    ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
    // stars
    const R = window.rng(7);
    for (let i = 0; i < 160; i++) {
      const sx = R() * w, sy = R() * h * 0.55, tw = 0.3 + 0.7 * Math.abs(Math.sin(t * 0.8 + i));
      ctx.fillStyle = `rgba(255,255,255,${0.25 * tw})`; ctx.fillRect(sx, sy, 1.6, 1.6);
    }
    // horizon glow
    const hg = ctx.createRadialGradient(w / 2, h * 0.86, 10, w / 2, h * 0.86, w * 0.6);
    hg.addColorStop(0, 'rgba(32,201,151,0.18)'); hg.addColorStop(1, 'rgba(32,201,151,0)');
    ctx.fillStyle = hg; ctx.fillRect(0, 0, w, h);
    // distant skyline
    ctx.fillStyle = '#06100c';
    const R2 = window.rng(3);
    for (let x = 0; x < w; x += 46) { const bh = 40 + R2() * 110; ctx.fillRect(x, h * 0.86 - bh, 40, bh); }
    const upgraded = clamp((local - cue(info, 1) - 1.5) / 3);
    // plant B smoke (heavier, grey) then plant A (fades greener)
    smoke(ctx, w * 0.73 + 22, h * 0.86 - 465 * 0.95, t, 1.0, '150,150,150', 11);
    smoke(ctx, w * 0.73 + 72, h * 0.86 - 415 * 0.95, t + 3, 0.8, '150,150,150', 12);
    smoke(ctx, w * 0.27 + 22, h * 0.86 - 465 * 0.95, t, 1.0 - 0.65 * upgraded, '150,170,160', 13);
    smoke(ctx, w * 0.27 + 72, h * 0.86 - 415 * 0.95, t + 3, 0.8 - 0.6 * upgraded, '150,170,160', 14);
    building(ctx, w * 0.27, h * 0.86, 0.95, upgraded > 0.5 ? '32,201,151' : '255,190,110', t);
    building(ctx, w * 0.73, h * 0.86, 0.95, '255,190,110', t + 2);
    ctx.fillStyle = '#020604'; ctx.fillRect(0, h * 0.86, w, h);
    // ground reflections
    ctx.fillStyle = 'rgba(32,201,151,0.06)'; ctx.fillRect(0, h * 0.86, w, 2);
    ctx.restore();
  };

  // ---------- perspective data grid with particles (dark chapters) ----------
  window.DRAW.grid = function (ctx, t, w, h, local) {
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, w, h);
    const hz = h * 0.58, vx = w / 2;
    const glow = ctx.createRadialGradient(vx, hz, 0, vx, hz, w * 0.55);
    glow.addColorStop(0, 'rgba(32,201,151,0.16)'); glow.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = glow; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(32,201,151,0.22)'; ctx.lineWidth = 1.2;
    for (let i = -24; i <= 24; i++) {
      ctx.beginPath(); ctx.moveTo(vx + i * 8, hz); ctx.lineTo(vx + i * 160, h + 40); ctx.stroke();
    }
    const speed = 0.12;
    for (let k = 0; k < 18; k++) {
      const z = ((k / 18) + (t * speed) % (1 / 18)) ;
      const p = Math.pow(z, 2.4);
      const y = hz + (h - hz + 40) * p;
      ctx.strokeStyle = `rgba(32,201,151,${0.05 + 0.25 * p})`;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
    // horizon fade
    const fade = ctx.createLinearGradient(0, hz - 10, 0, hz + 120);
    fade.addColorStop(0, 'rgba(0,0,0,1)'); fade.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = fade; ctx.fillRect(0, hz - 10, w, 130);
    // floating particles
    const R = window.rng(42);
    for (let i = 0; i < 140; i++) {
      const x0 = R() * w, y0 = R() * h, sp = 6 + R() * 18, sz = 0.8 + R() * 2.2;
      const y = (y0 - t * sp) % h; const yy = y < 0 ? y + h : y;
      const x = x0 + Math.sin(t * 0.3 + i) * 20;
      ctx.fillStyle = `rgba(32,201,151,${0.15 + 0.35 * R()})`;
      ctx.beginPath(); ctx.arc(x, yy, sz, 0, 7); ctx.fill();
    }
  };

  // ---------- light chapters: soft contour lines ----------
  window.DRAW.contour = function (ctx, t, w, h) {
    ctx.lineWidth = 1.4;
    for (let k = 0; k < 14; k++) {
      ctx.strokeStyle = `rgba(32,201,151,${0.05 + 0.015 * (k % 3)})`;
      ctx.beginPath();
      for (let x = 0; x <= w; x += 24) {
        const y = h * 0.15 + k * 64 + Math.sin(x / 260 + t * 0.15 + k * 0.6) * 26 + Math.sin(x / 90 + k) * 6;
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  };

  // ---------- intensity vs absolute (challenges, illustrative) ----------
  window.DRAW.intensity = function (ctx, t, w, h, local, info) {
    const start = cue(info, 1) + 0.6;
    const p = ease((local - start) / 5);
    const pad = 70, W = w - pad * 2, H = h - pad * 2;
    ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(pad, pad); ctx.lineTo(pad, pad + H); ctx.lineTo(pad + W, pad + H); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.55)'; ctx.font = '500 20px Roboto';
    ctx.fillText('Year 1', pad, pad + H + 34); ctx.fillText('Year 5', pad + W - 60, pad + H + 34);
    const series = [
      { c: 'rgba(255,255,255,0.75)', f: x => 0.18 + 0.7 * x, lab: 'Production', dy: -14 },
      { c: '#20C997', f: x => 0.62 - 0.22 * x, lab: 'Intensity (per tonne)', dy: 34 },
      { c: '#FF7A66', f: x => 0.3 + 0.36 * x, lab: 'Total emissions', dy: -14 }
    ];
    series.forEach((s, si) => {
      ctx.strokeStyle = s.c; ctx.lineWidth = 6; ctx.lineCap = 'round';
      ctx.beginPath();
      const n = 60;
      for (let i = 0; i <= n * p; i++) {
        const x = i / n; const X = pad + x * W, Y = pad + H - s.f(x) * H;
        i === 0 ? ctx.moveTo(X, Y) : ctx.lineTo(X, Y);
      }
      ctx.stroke();
      if (p > 0.95) {
        ctx.fillStyle = s.c; ctx.font = '700 24px "ESC"';
        ctx.textAlign = 'right'; ctx.fillText(s.lab, pad + W, pad + H - s.f(1) * H + s.dy); ctx.textAlign = 'left';
      }
    });
  };
})();
