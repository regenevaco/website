// Render scenes.html to video frames with headless Chromium.
//
//   node render.js stills <timing.json> <out_dir> t1 t2 ...   -> PNG stills
//   node render.js video  <timing.json> <out.mp4> [workers]    -> silent H.264 1080p30
//
// Every frame is produced by window.setTime(t), so output is deterministic.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30;
const W = 1920, H = 1080;
const PAGE = 'file://' + path.join(__dirname, 'scenes.html');

async function openPage(browser, timing) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto(PAGE);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(t => window.init(t), timing);
  await page.waitForTimeout(300);
  return page;
}

async function stills(timing, outDir, times) {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await openPage(browser, timing);
  for (const t of times) {
    await page.evaluate(x => window.setTime(x), t);
    await page.screenshot({ path: path.join(outDir, `still_${String(t).padStart(6, '0')}.png`) });
  }
  await browser.close();
}

async function segment(timing, from, to, out) {
  const browser = await chromium.launch();
  const page = await openPage(browser, timing);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
    '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-tune', 'animation',
    '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = from; f < to; f++) {
    await page.evaluate(x => window.setTime(x), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - from) % 300 === 0) console.log(`${path.basename(out)}: ${f - from}/${to - from}`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  await browser.close();
}

async function video(timing, out, workers) {
  const total = Math.ceil(timing.total * FPS);
  const per = Math.ceil(total / workers);
  const dir = path.dirname(out);
  const parts = [];
  const jobs = [];
  for (let w = 0; w < workers; w++) {
    const from = w * per, to = Math.min(total, from + per);
    if (from >= to) break;
    const part = path.join(dir, `part${w}.mp4`);
    parts.push(part);
    jobs.push(segment(timing, from, to, part));
  }
  await Promise.all(jobs);
  const list = path.join(dir, 'parts.txt');
  fs.writeFileSync(list, parts.map(p => `file '${p}'`).join('\n'));
  await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
    '-i', list, '-c', 'copy', out], { stdio: 'inherit' }).on('close', c => (c === 0 ? res() : rej(c))));
}

(async () => {
  const [mode, timingPath, out, ...rest] = process.argv.slice(2);
  const timing = JSON.parse(fs.readFileSync(timingPath, 'utf8'));
  if (mode === 'stills') await stills(timing, out, rest.map(Number));
  else await video(timing, out, +(rest[0] || 4));
})().catch(e => { console.error(e); process.exit(1); });
