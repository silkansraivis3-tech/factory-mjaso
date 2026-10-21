#!/usr/bin/env node
/* perf3d.mjs - speed test of the 3D slides of a one-page deck (Node 18+, no npm packages, any course).
 *
 *   node perf3d.mjs <deck.html | http(s)://url> [options]
 *
 * Starts headless Chrome on a temp profile, speaks the DevTools protocol over Node's global WebSocket, slows the CPU
 * (default 4x - a stand-in for the classroom tablet) and, for every 3D slide asked for, loads the deck afresh, starts
 * the show and presses Next until the slide is up. Two runs per slide:
 *   warm  - it stops on the slide BEFORE the 3D one and dwells there (--dwell ms), as a person does. A scene that builds
 *           itself ahead ("build-ahead") gets its idle time. This is the number the budget is judged on.
 *   cold  - jumps straight to the slide with window.__noPrepare = true set before the deck loads. What a skip costs.
 *
 * The deck contract (what the 3D slide must offer, set when the slide's enter hook runs):
 *   window.__scene3d = { enterT, firstFrameT, frames, [spin(ms, cb)], [marks], [prepared] }
 *     enterT       performance.now() when the slide became active
 *     firstFrameT  performance.now() when the first frame of the scene was drawn (0 until then)
 *     frames       count of frames the scene has drawn so far (used for fps)
 *     spin(ms, cb) optional: turn the model for ms, then cb({frames, ms}); without it fps is the passive frame count
 *   The deck is driven through the factory shell: .slide sections that get class "active", a Next button (#btnNext),
 *   an optional Start button (#startBtn; otherwise Enter is pressed). All three can be changed with --active-class,
 *   --next, --start.
 *
 * Options (value options take --name=value or --name value):
 *   --slides=a,b|all   slide ids; "all" (default) = every slide that has a <canvas>, [data-3d] or [data-scene]
 *   --budget-ms=1000   first-frame budget in ms at the CPU throttle
 *   --throttle=4       CPU slowdown rate (1 = none)
 *   --gate=warm        which run is judged against the budget: warm (default), cold or both
 *   --no-cold          skip the cold run
 *   --no-fps           skip the fps run (first frame only: much faster)
 *   --min-fps=0        fail a slide below this fps (default 0: fps is reported, not judged)
 *   --ms=2000          length of the fps run          --dwell=2000   idle time on the slide before (warm)
 *   --wait-ms=10000    how long to wait for a first frame before calling it "never"
 *   --w=1280 --h=800 --dsf=1   window size and device scale factor
 *   --gl=swiftshader   swiftshader (software, works anywhere) | gpu | none (WebGL off)
 *   --chrome=PATH      Chrome/Chromium/Edge executable (else env CHROME_PATH, else the usual install places)
 *   --json             print one JSON document instead of the table
 *   --help
 * Exit code: 0 = every measured slide within the budget, 1 = at least one over (or never drew), 2 = bad input,
 *            no Chrome, no 3D slide found, or the deck does not offer window.__scene3d.
 * NOTE: the CPU throttle slows scripts, not the GL back end. With --gl=swiftshader the GPU work runs in software on
 *       this machine's CPU, so a slow fps there can be the stand-in GPU rather than the scene.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { homedir } from 'node:os';
import { takeSlot } from './browser_slots.mjs';

const VALUE_OPTS = ['slides', 'budget-ms', 'throttle', 'gate', 'min-fps', 'ms', 'dwell', 'wait-ms', 'w', 'h', 'dsf', 'gl', 'chrome', 'next', 'start', 'active-class'];
const FLAGS = ['no-cold', 'no-fps', 'json', 'help'];

function parseArgs(argv) {
  const pos = [], opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { pos.push(a); continue; }
    const eq = a.indexOf('=');
    const name = eq < 0 ? a.slice(2) : a.slice(2, eq);
    if (FLAGS.includes(name)) { opt[name] = true; continue; }
    if (!VALUE_OPTS.includes(name)) throw new Error('unknown option --' + name);
    if (eq >= 0) opt[name] = a.slice(eq + 1);
    else if (i + 1 < argv.length) opt[name] = argv[++i];
    else throw new Error('--' + name + ' needs a value');
  }
  return { pos, opt };
}

const USAGE = `usage: node perf3d.mjs <deck.html | url> [--slides=a,b|all] [--budget-ms=1000] [--throttle=4] [--gate=warm|cold|both]
                           [--no-cold] [--no-fps] [--min-fps=0] [--ms=2000] [--dwell=2000] [--wait-ms=10000]
                           [--w=1280 --h=800 --dsf=1] [--gl=swiftshader|gpu|none] [--chrome=PATH] [--json] [--help]
Measures the first frame (and fps) of a deck's 3D slides in headless Chrome at a CPU throttle.
Exit 0 = all within budget, 1 = over budget, 2 = bad input / no Chrome / no 3D slide / no window.__scene3d.`;

function bad(msg) { console.error('perf3d: ' + msg); process.exit(2); }

function findChrome(explicit) {
  const cands = [];
  if (explicit) cands.push(explicit);
  if (process.env.CHROME_PATH) cands.push(process.env.CHROME_PATH);
  if (process.platform === 'win32') {
    for (const base of [process.env.ProgramFiles, process.env['ProgramFiles(x86)'], process.env.LOCALAPPDATA].filter(Boolean)) {
      cands.push(join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'),
                 join(base, 'Chromium', 'Application', 'chrome.exe'),
                 join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe'));
    }
  } else if (process.platform === 'darwin') {
    for (const root of ['/Applications', join(homedir(), 'Applications')]) {
      cands.push(join(root, 'Google Chrome.app/Contents/MacOS/Google Chrome'), join(root, 'Chromium.app/Contents/MacOS/Chromium'),
                 join(root, 'Microsoft Edge.app/Contents/MacOS/Microsoft Edge'));
    }
  } else {
    const dirs = (process.env.PATH || '').split(':').concat(['/usr/bin', '/usr/local/bin', '/snap/bin', '/opt/google/chrome']);
    for (const n of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'microsoft-edge']) {
      for (const d of dirs) if (d) cands.push(join(d, n));
    }
  }
  for (const c of cands) if (c && existsSync(c)) return c;
  return null;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
const round1 = n => Math.round(n * 10) / 10;

async function main() {
  let parsed;
  try { parsed = parseArgs(process.argv.slice(2)); } catch (e) { console.error('perf3d: ' + e.message + '\n' + USAGE); process.exit(2); }
  const { pos, opt } = parsed;
  if (opt.help) { console.log(USAGE); process.exit(0); }
  if (pos.length !== 1) { console.error(USAGE); process.exit(2); }

  const num = (name, def) => { const v = Number(opt[name] ?? def); if (!Number.isFinite(v)) bad(`--${name} must be a number`); return v; };
  const BUDGET = num('budget-ms', 1000), THROTTLE = num('throttle', 4), MIN_FPS = num('min-fps', 0);
  const FPS_MS = num('ms', 2000), DWELL = num('dwell', 2000), WAIT = num('wait-ms', 10000);
  const W = num('w', 1280), H = num('h', 800), DSF = num('dsf', 1);
  const GATE = String(opt.gate ?? 'warm'), GL = String(opt.gl ?? 'swiftshader');
  const NEXT = String(opt.next ?? '#btnNext'), START = String(opt.start ?? '#startBtn'), ACTIVE = String(opt['active-class'] ?? 'active');
  if (!['warm', 'cold', 'both'].includes(GATE)) bad('--gate must be warm, cold or both');
  if (!['swiftshader', 'gpu', 'none'].includes(GL)) bad('--gl must be swiftshader, gpu or none');
  if (THROTTLE < 1) bad('--throttle must be >= 1');
  const doCold = !opt['no-cold'], doFps = !opt['no-fps'];
  if (GATE !== 'warm' && !doCold) bad(`--gate=${GATE} needs the cold run (drop --no-cold)`);

  let deckUrl;
  if (/^(https?|file):\/\//i.test(pos[0])) deckUrl = pos[0];
  else {
    const p = resolve(pos[0]);
    if (!existsSync(p)) bad('no such deck: ' + p);
    deckUrl = pathToFileURL(p).href;
  }
  const chromePath = findChrome(opt.chrome);
  if (!chromePath) bad('no Chrome found (set CHROME_PATH or pass --chrome=PATH)');

  await takeSlot();           // 2.57.0: one slot of the computer's pool of hidden browsers, held until the process exits
  const profile = mkdtempSync(join(tmpdir(), 'perf3d-'));
  const glArgs = GL === 'none' ? ['--disable-3d-apis', '--disable-gpu', '--disable-software-rasterizer']
    : GL === 'gpu' ? ['--ignore-gpu-blocklist', '--enable-gpu-rasterization']
    : ['--use-angle=swiftshader', '--use-gl=angle', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
  let chromeExited = false;
  const chrome = spawn(chromePath, [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, `--window-size=${W},${H}`,
    '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio', '--no-sandbox',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
    '--disable-features=CalculateNativeWinOcclusion', ...glArgs, 'about:blank'
  ], { stdio: 'ignore' });
  chrome.on('exit', () => { chromeExited = true; });
  chrome.on('error', () => { chromeExited = true; });

  let closing = false;
  async function done(code) {
    if (closing) return; closing = true;
    try { chrome.kill(); } catch {}
    await sleep(400);
    try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
    process.exit(code);
  }
  process.on('SIGINT', () => done(2));
  const hardStop = setTimeout(() => { console.error('perf3d: gave up after 10 minutes'); done(2); }, 600000);
  hardStop.unref();

  let ws, nextId = 1;
  const waiting = new Map(), handlers = [];
  const send = (method, params = {}) => new Promise((res, rej) => {
    const id = nextId++; waiting.set(id, { res, rej, method });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const onEvent = fn => handlers.push(fn);
  async function evaluate(expr, awaitPromise = false) {
    const r = await send('Runtime.evaluate', { expression: expr, awaitPromise, returnByValue: true });
    if (r.exceptionDetails) throw new Error('page error: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  }

  async function connect() {
    for (let i = 0; i < 120; i++) {
      if (chromeExited) throw new Error('Chrome exited at start (' + chromePath + ')');
      try {
        const port = Number(readFileSync(join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]);
        const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
        const pg = list.find(t => t.type === 'page');
        if (pg) return pg.webSocketDebuggerUrl;
      } catch {}
      await sleep(250);
    }
    throw new Error('Chrome did not start');
  }

  try {
    ws = new WebSocket(await connect());
    await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', () => rej(new Error('websocket'))); });
    ws.addEventListener('message', ev => {
      const m = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString());
      if (m.id && waiting.has(m.id)) {
        const w = waiting.get(m.id); waiting.delete(m.id);
        if (m.error) w.rej(new Error(w.method + ': ' + m.error.message)); else w.res(m.result);
      } else if (m.method) handlers.forEach(h => h(m));
    });
    const consoleErrors = [];
    onEvent(m => {
      if (m.method === 'Runtime.exceptionThrown') consoleErrors.push('exception: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    });
    await send('Page.enable'); await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: DSF, mobile: false });
    await send('Emulation.setCPUThrottlingRate', { rate: THROTTLE });

    let preloadId = null;
    async function load(noPrepare) {
      if (preloadId) { try { await send('Page.removeScriptToEvaluateOnNewDocument', { identifier: preloadId }); } catch {} preloadId = null; }
      if (noPrepare) preloadId = (await send('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__noPrepare = true;' })).identifier;
      const loaded = new Promise(res => onEvent(m => { if (m.method === 'Page.loadEventFired') res(); }));
      await send('Page.navigate', { url: deckUrl });
      await Promise.race([loaded, sleep(20000)]);
      await sleep(400);
    }
    const q = s => JSON.stringify(s);
    const press = () => evaluate(`(function(){ var b = document.querySelector(${q(NEXT)}); if (!b || b.disabled) return false; b.click(); return true; })()`);
    const isActive = id => evaluate(`(function(){ var e = document.getElementById(${q(id)}); return !!e && e.classList.contains(${q(ACTIVE)}); })()`);

    // start the show and press Next until `id` is the active slide; with dwell, stop on the slide before it first
    async function goTo(id, dwell) {
      await evaluate(`(function(){ var s = document.querySelector(${q(START)}); if (s) s.click(); else document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true })); })()`);
      await sleep(250);
      const before = await evaluate(`(function(){ var all = [].slice.call(document.querySelectorAll('.slide')), i = all.indexOf(document.getElementById(${q(id)})); return i > 0 ? all[i - 1].id : null; })()`);
      if (dwell && before) {
        for (let n = 0; n < 400 && !(await isActive(before)) && !(await isActive(id)); n++) { if (!(await press())) break; await sleep(60); }
        await sleep(dwell);
      }
      for (let n = 0; n < 400 && !(await isActive(id)); n++) { if (!(await press())) break; await sleep(60); }
      return isActive(id);
    }

    async function waitFirstFrame() {
      let probe = null;
      const t0 = Date.now();
      while (Date.now() - t0 < WAIT) {
        probe = await evaluate(`window.__scene3d ? { enterT: window.__scene3d.enterT, firstFrameT: window.__scene3d.firstFrameT } : null`);
        if (probe && probe.firstFrameT > 0) break;
        await sleep(50);
      }
      return probe;
    }

    async function measure(id, mode) {
      const r = { mode };
      await load(mode === 'cold');
      if (!(await goTo(id, mode === 'warm' ? DWELL : 0))) { r.error = 'slide not reached with Next'; return r; }
      const probe = await waitFirstFrame();
      if (!probe) { r.error = 'window.__scene3d missing (the slide must set it on enter; see --help)'; r.noContract = true; return r; }
      if (probe.firstFrameT > 0) {
        r.firstFrameMs = round1(probe.firstFrameT - probe.enterT);
        r.preparedAhead = await evaluate(`!!window.__scene3d.prepared`);
        r.marks = await evaluate(`window.__scene3d.marks || null`);
      } else { r.firstFrameMs = null; r.error = `no first frame within ${WAIT} ms`; }
      if (mode === 'warm' && doFps && r.firstFrameMs !== null) {
        const hasSpin = await evaluate(`typeof window.__scene3d.spin === 'function'`);
        const run = hasSpin
          ? async () => { await evaluate(`new Promise(function(d){ window.__scene3d.spin(400, d); })`, true);
                          return evaluate(`new Promise(function(d){ window.__scene3d.spin(${FPS_MS}, d); })`, true); }
          : () => evaluate(`new Promise(function(d){ var s = window.__scene3d, f0 = s.frames, t0 = performance.now(); setTimeout(function(){ d({ frames: s.frames - f0, ms: performance.now() - t0 }); }, ${FPS_MS}); })`, true);
        const x = await run();
        r.fps = x && x.ms > 0 ? round1(x.frames * 1000 / x.ms) : null;
      }
      return r;
    }

    // which slides
    await load(false);
    let ids;
    if (!opt.slides || opt.slides === 'all') {
      ids = await evaluate(`[].slice.call(document.querySelectorAll('.slide')).filter(function(s){ return s.querySelector('canvas,[data-3d],[data-scene]') || s.hasAttribute('data-3d') || s.hasAttribute('data-scene'); }).map(function(s){ return s.id; }).filter(Boolean)`);
      if (!ids.length) { console.error('perf3d: no slide with a <canvas>, [data-3d] or [data-scene] found in ' + deckUrl + ' (name them with --slides=id1,id2)'); await done(2); return; }
    } else {
      ids = String(opt.slides).split(',').map(s => s.trim()).filter(Boolean);
      const missing = [];
      for (const id of ids) if (!(await evaluate(`!!document.getElementById(${q(id)})`))) missing.push(id);
      if (missing.length) { console.error('perf3d: no such slide id: ' + missing.join(', ')); await done(2); return; }
    }

    const slides = [];
    let contractMissing = false;
    for (const id of ids) {
      const s = { id };
      s.warm = await measure(id, 'warm');
      if (doCold && !s.warm.noContract) s.cold = await measure(id, 'cold');
      if (s.warm.noContract) contractMissing = true;
      const judge = m => !!m && m.firstFrameMs !== null && m.firstFrameMs !== undefined && m.firstFrameMs <= BUDGET;
      const budgetOk = GATE === 'warm' ? judge(s.warm) : GATE === 'cold' ? judge(s.cold) : judge(s.warm) && judge(s.cold);
      const fpsOk = !MIN_FPS || (s.warm.fps !== undefined && s.warm.fps !== null && s.warm.fps >= MIN_FPS);
      s.ok = budgetOk && fpsOk;
      slides.push(s);
    }
    const report = {
      deck: deckUrl, budgetMs: BUDGET, throttle: THROTTLE, gate: GATE, size: `${W}x${H}@${DSF}`, gl: GL,
      ok: slides.every(s => s.ok), slides, consoleErrors: consoleErrors.slice(0, 6)
    };
    if (opt.json) console.log(JSON.stringify(report));
    else {
      const f = m => !m ? '-' : m.firstFrameMs === null || m.firstFrameMs === undefined ? (m.error ? 'none' : '-') : String(m.firstFrameMs);
      console.log(`perf3d: CPU ${THROTTLE}x, ${W}x${H}, budget ${BUDGET} ms, judged on ${GATE}`);
      console.log('slide'.padEnd(24) + 'warm ms'.padStart(10) + 'cold ms'.padStart(10) + 'fps'.padStart(8) + '  verdict');
      for (const s of slides) {
        console.log(s.id.slice(0, 23).padEnd(24) + f(s.warm).padStart(10) + f(s.cold).padStart(10) + String(s.warm.fps ?? '-').padStart(8) + '  ' + (s.ok ? 'OK' : 'OVER'));
        const err = s.warm.error || (s.cold && s.cold.error);
        if (err) console.log('  ' + err);
        if (s.warm.firstFrameMs !== null && s.warm.firstFrameMs !== undefined && s.warm.preparedAhead === false && !s.ok) console.log('  not built ahead on the slide before: see GUIDE.md "build-ahead"');
      }
      if (report.consoleErrors.length) console.log('page errors: ' + report.consoleErrors.join(' | '));
      console.log(report.ok ? 'PASS: all within budget' : 'FAIL: over budget');
    }
    await done(contractMissing ? 2 : report.ok ? 0 : 1);
  } catch (e) {
    console.error('perf3d: ' + e.message);
    await done(2);
  }
}
main();
