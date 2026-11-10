// node render_thumb_pro.js <subject.png> <out_2560.png>
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [subj, out] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, 'thumbnail_pro.html'));
  await p.evaluate(s => { document.querySelector('.me').src = 'file://' + s; }, path.resolve(subj));
  await p.evaluate(() => Promise.all([document.fonts.ready, ...[...document.images].map(i => i.decode().catch(() => 0))]));
  await p.waitForTimeout(400);
  await p.screenshot({ path: out });
  await b.close();
})();
