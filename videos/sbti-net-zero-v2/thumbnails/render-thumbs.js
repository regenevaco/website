// node render-thumbs.js <out_dir>  -> thumb-*.png at 2560x1440 (2x) + YouTube-ready 1280x720 JPEGs
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const out = process.argv[2] || __dirname;
  const b = await chromium.launch();
  for (const f of ['thumb-a', 'thumb-b', 'thumb-c']) {
    for (const [scale, suffix, type] of [[2, '-2560x1440.png', 'png'], [1, '-1280x720.jpg', 'jpeg']]) {
      const p = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: scale });
      await p.goto('file://' + path.join(__dirname, f + '.html'));
      await p.evaluate(() => document.fonts.ready);
      await p.waitForTimeout(300);
      await p.screenshot({ path: path.join(out, f + suffix), type, ...(type === 'jpeg' ? { quality: 95 } : {}) });
      await p.close();
    }
  }
  await b.close();
})();
