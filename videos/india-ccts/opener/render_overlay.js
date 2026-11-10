// Render overlay.html to transparent 4K PNGs, one per output frame that shows something.
//   node render_overlay.js <out_dir> <frames> [still_t ...]
// Frames whose animation state is unchanged reuse the previous PNG (hard link), so static holds are free.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [outDir, frames, ...stills] = process.argv.slice(2);
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, 'overlay.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  if (stills.length) {
    for (const t of stills.map(Number)) {
      await page.evaluate(x => window.setTime(x), t);
      await page.screenshot({ path: path.join(outDir, `still_${t.toFixed(2)}.png`), omitBackground: true });
    }
    await browser.close();
    return;
  }
  let prevKey = null, prevFile = null, shots = 0, links = 0;
  for (let k = 0; k < +frames; k++) {
    const { key, visible } = await page.evaluate(x => window.setTime(x), k / 30);
    if (!visible) { prevKey = null; continue; }
    const file = path.join(outDir, `${String(k).padStart(5, '0')}.png`);
    if (key === prevKey && prevFile) { fs.linkSync(prevFile, file); links++; }
    else { await page.screenshot({ path: file, omitBackground: true }); shots++; prevKey = key; prevFile = file; }
    if (k % 300 === 0) console.log(k, shots, links);
  }
  console.log('done', shots, 'renders', links, 'reused');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
