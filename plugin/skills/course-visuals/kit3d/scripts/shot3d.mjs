/* shot3d.mjs - pictures of 3D scenes, saved as PNG files, from a hidden Chrome (the 3D kit, course-visuals/kit3d).
 *
 *   node shot3d.mjs <plan.json> [--w=1280 --h=720] [--gl=swiftshader|gpu|none]
 *
 * plan.json: a list of shots, taken in order in one browser:
 *   [{"url": "http://127.0.0.1:47660/course-visuals/kit3d/studio3d.html?spec=examples/m01_hull.kit3d.json",
 *     "wait": "window.k3ready",                 - a JS expression; the shot waits until it is true (20 s at most)
 *     "do": "k3.step(1)",                       - JS run before the shot (optional; a list runs in turn)
 *     "settle": 1200,                           - ms after "do" (tweens are 750 ms)
 *     "clip": "#box",                           - only this element (default: the whole window)
 *     "out": "C:/.../m01_kit_s1.png",
 *     "probe": "JSON.stringify(k3.info())"}]    - a JS value to report with the shot (optional)
 *   A shot without "url" stays on the page the shot before loaded (a step after a step).
 * WHY: the side-by-side pictures of a hand-made scene and its kit port, and a reviewer that looks at files - the
 * Browser pane draws nothing while it is hidden, and a screenshot there cannot be saved.
 * Prints one JSON line per shot: {out, ms, probe, errors}. Exit 0 every shot taken, 1 a shot failed, 2 bad input.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SLOTS = join(HERE, '..', '..', '..', 'course-module-ux', 'measure', 'scripts', 'browser_slots.mjs');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const args = process.argv.slice(2), opt = {}, pos = [];
for (const a of args) { const m = /^--([\w-]+)(?:=(.*))?$/.exec(a); if (m) opt[m[1]] = m[2] ?? true; else pos.push(a); }
if (pos.length !== 1 || !existsSync(pos[0])) { console.error('usage: node shot3d.mjs <plan.json> [--w=1280 --h=720] [--gl=swiftshader|gpu]'); process.exit(2); }
const plan = JSON.parse(readFileSync(pos[0], 'utf8'));
const W = Number(opt.w || 1280), H = Number(opt.h || 720), GL = String(opt.gl || 'swiftshader');

function findChrome() {
  const c = [process.env.CHROME_PATH];
  for (const b of [process.env.ProgramFiles, process.env['ProgramFiles(x86)'], process.env.LOCALAPPDATA].filter(Boolean)) {
    c.push(join(b, 'Google', 'Chrome', 'Application', 'chrome.exe'), join(b, 'Microsoft', 'Edge', 'Application', 'msedge.exe'));
  }
  c.push('/usr/bin/google-chrome', '/usr/bin/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
  return c.find(x => x && existsSync(x));
}
const chromePath = findChrome();
if (!chromePath) { console.error('shot3d: no Chrome found (set CHROME_PATH)'); process.exit(2); }
if (existsSync(SLOTS)) { try { const { takeSlot } = await import('file:///' + SLOTS.replace(/\\/g, '/')); await takeSlot(); } catch { /* no pool */ } }

const profile = mkdtempSync(join(tmpdir(), 'shot3d-'));
const glArgs = GL === 'none' ? ['--disable-3d-apis', '--disable-gpu', '--disable-software-rasterizer']   /* a tablet with no WebGL */
  : GL === 'gpu' ? ['--ignore-gpu-blocklist', '--enable-gpu-rasterization']
  : ['--use-angle=swiftshader', '--use-gl=angle', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const chrome = spawn(chromePath, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, `--window-size=${W},${H}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio', '--no-sandbox',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding', ...glArgs, 'about:blank'], { stdio: 'ignore' });
let exited = false;
chrome.on('exit', () => { exited = true; });
async function done(code) {
  try { chrome.kill(); } catch {}
  await sleep(400);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
  process.exit(code);
}
setTimeout(() => { console.error('shot3d: gave up after 5 minutes'); done(1); }, 300000).unref();

let ws, nextId = 1;
const waiting = new Map(), errors = [];
const send = (method, params = {}) => new Promise((res, rej) => { const id = nextId++; waiting.set(id, { res, rej, method }); ws.send(JSON.stringify({ id, method, params })); });
async function ev(expr, awaitPromise = false) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
async function connect() {
  for (let i = 0; i < 120; i++) {
    if (exited) throw new Error('Chrome exited at start');
    try {
      const port = Number(readFileSync(join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]);
      const pg = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t => t.type === 'page');
      if (pg) return pg.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('Chrome did not start');
}

let failed = false;
try {
  ws = new WebSocket(await connect());
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', () => rej(new Error('websocket'))); });
  ws.addEventListener('message', e => {
    const m = JSON.parse(typeof e.data === 'string' ? e.data : Buffer.from(e.data).toString());
    if (m.id && waiting.has(m.id)) { const w = waiting.get(m.id); waiting.delete(m.id); if (m.error) w.rej(new Error(w.method + ': ' + m.error.message)); else w.res(m.result); }
    else if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  });
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  for (const s of plan) {
    const t0 = Date.now(), errs0 = errors.length;
    try {
      if (s.url) {
        const loaded = new Promise(r => { const h = e => { const m = JSON.parse(typeof e.data === 'string' ? e.data : Buffer.from(e.data).toString()); if (m.method === 'Page.loadEventFired') { ws.removeEventListener('message', h); r(); } }; ws.addEventListener('message', h); });
        await send('Page.navigate', { url: s.url });
        await Promise.race([loaded, sleep(20000)]);
      }
      if (s.wait) {
        let ok = false;
        for (let i = 0; i < 200 && !ok; i++) { try { ok = !!(await ev(s.wait)); } catch {} if (!ok) await sleep(100); }
        if (!ok) throw new Error('waited 20 s for ' + s.wait);
      }
      for (const d of [].concat(s.do || [])) { await ev(d, true); await sleep(Number(s.between || 300)); }
      await sleep(Number(s.settle ?? 900));
      let clip;
      if (s.clip) {
        const r = await ev(`(function(){ var e = document.querySelector(${JSON.stringify(s.clip)}); if (!e) return null; var r = e.getBoundingClientRect(); return {x: r.left, y: r.top, width: r.width, height: r.height}; })()`);
        if (r && r.width) clip = { ...r, scale: 1 };
      }
      const shot = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip } : {}) });
      if (s.out) writeFileSync(s.out, Buffer.from(shot.data, 'base64'));
      const probe = s.probe ? await ev(s.probe) : undefined;
      console.log(JSON.stringify({ out: s.out, ms: Date.now() - t0, probe, errors: errors.slice(errs0) }));
    } catch (e) {
      failed = true;
      console.log(JSON.stringify({ out: s.out, error: String(e.message || e), errors: errors.slice(errs0) }));
    }
  }
} catch (e) { console.error('shot3d: ' + (e.message || e)); failed = true; }
await done(failed ? 1 : 0);
