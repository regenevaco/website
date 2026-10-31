// Render scenes/index.html to frames with headless Chromium.
//   node render.js stills <timing.json> <out_dir> t1 t2 ...          PNG stills (1080p)
//   node render.js video  <timing.json> <out.mp4> [workers] [scale]  H.264, scale 2 => 3840x2160
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30;
const PAGE = 'file://' + path.join(__dirname, 'index.html');

async function openPage(browser, timing, scale) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: scale });
  page.on('pageerror', e => console.error('pageerror', e.message));
  await page.goto(PAGE);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(t => window.init(t), timing);
  await page.waitForTimeout(400);
  return page;
}

async function stills(timing, outDir, times, scale) {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await openPage(browser, timing, scale);
  for (const t of times) {
    await page.evaluate(x => window.setTime(x), t);
    await page.screenshot({ path: path.join(outDir, `s_${String(t.toFixed(2)).padStart(7, '0')}.png`) });
  }
  await browser.close();
}

async function segment(timing, from, to, out, scale) {
  const SCALE = scale;
  const browser = await chromium.launch({ args: ['--disable-gpu'] });
  const page = await openPage(browser, timing, scale);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
    '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', scale > 1 ? '17' : '17',
    '-pix_fmt', 'yuv420p', '-r', String(FPS), '-g', '60', ...(out.endsWith('.ts') ? ['-f', 'mpegts'] : []), out],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const cdp = await page.context().newCDPSession(page);
  const t0 = Date.now();
  for (let f = from; f < to; f++) {
    await page.evaluate(x => window.setTime(x), f / FPS);
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 94, optimizeForSpeed: true, clip: { x: 0, y: 0, width: 1920, height: 1080, scale: SCALE } });
    const buf = Buffer.from(data, 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - from) % 600 === 0) console.log(`${path.basename(out)} ${f - from}/${to - from} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  await browser.close();
}

async function video(timing, out, workers, scale) {
  const total = Math.ceil(timing.total * FPS);
  const per = Math.ceil(total / workers);
  const parts = [], jobs = [];
  for (let w = 0; w < workers; w++) {
    const from = w * per, to = Math.min(total, from + per);
    if (from >= to) break;
    const part = out.replace(/\.mp4$/, `.part${w}.mp4`);
    parts.push(part);
    jobs.push(segment(timing, from, to, part, scale));
  }
  await Promise.all(jobs);
  const list = out.replace(/\.mp4$/, '.parts.txt');
  fs.writeFileSync(list, parts.map(p => `file '${p}'`).join('\n'));
  await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
    '-i', list, '-c', 'copy', out], { stdio: 'inherit' }).on('close', c => (c === 0 ? res() : rej(c))));
  parts.forEach(p => fs.unlinkSync(p)); fs.unlinkSync(list);
}

(async () => {
  const [mode, timingPath, out, ...rest] = process.argv.slice(2);
  const timing = JSON.parse(fs.readFileSync(timingPath, 'utf8'));
  if (mode === 'stills') await stills(timing, out, rest.map(Number), 1);
  else if (mode === 'range') {
    // node render.js range <timing> <out.ts> <fromFrame> <toFrame|end> <scale>
    // MPEG-TS output stays playable if the job is interrupted; resume with a new range.
    const total = Math.ceil(timing.total * FPS);
    const from = +rest[0], to = rest[1] === 'end' ? total : Math.min(total, +rest[1]);
    await segment(timing, from, to, out, +(rest[2] || 1));
  }
  else await video(timing, out, +(rest[0] || 4), +(rest[1] || 1));
})().catch(e => { console.error(e); process.exit(1); });
