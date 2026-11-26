// node render.js <lower|sub> <out_dir> [scale=2]   -> RGBA PNG frames (30 fps) with transparent background
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const [o, out, scale] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: +(scale || 2) });
  await p.goto('file://' + path.join(__dirname, 'overlays.html'));
  await p.evaluate(o => { document.body.dataset.o = o; }, o);
  await p.evaluate(() => document.fonts.ready);
  const dur = await p.evaluate(o => window.DUR[o], o);
  const n = Math.round(dur * 30);
  for (let f = 0; f < n; f++) {
    await p.evaluate(t => window.setT(t), f / 30);
    await p.screenshot({ path: path.join(out, `f_${String(f).padStart(4, '0')}.png`), omitBackground: true });
  }
  await b.close();
  console.log(o, n, 'frames');
})();
