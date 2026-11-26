// node render.js <variant a|b|c> <subject.png> <out.png> [scale=2]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [v, subj, out, scale] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: +(scale || 2) });
  await p.goto('file://' + path.join(__dirname, 'thumbnails.html'));
  await p.evaluate(([v, s]) => {
    document.body.dataset.v = v;
    document.querySelector(`#${v} .me`).src = 'file://' + s;
  }, [v, path.resolve(subj)]);
  await p.evaluate(() => Promise.all([document.fonts.ready, ...[...document.images].map(i => i.decode().catch(() => 0))]));
  await p.waitForTimeout(300);
  await p.screenshot({ path: out });
  await b.close();
})();
