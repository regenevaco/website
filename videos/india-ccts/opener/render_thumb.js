// node render_thumb.js <bg.png> <subject.png> <out_2560.png>
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [bg, subj, out] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, 'thumbnail.html'));
  await p.evaluate(([bg, s]) => {
    document.querySelector('.bg').style.backgroundImage = `url("file://${bg}")`;
    document.querySelector('.me').src = 'file://' + s;
  }, [path.resolve(bg), path.resolve(subj)]);
  await p.evaluate(() => Promise.all([document.fonts.ready, ...[...document.images].map(i => i.decode().catch(() => 0))]));
  await p.waitForTimeout(500);
  await p.screenshot({ path: out });
  await b.close();
})();
