#!/usr/bin/env node
/* review_sheets.mjs - the visual review's pictures, made by a script (compile GUIDE 2f, 2.50.0). Node 18+, no npm packages.
 *
 *   node review_sheets.mjs <module folder> <out folder> [--all] [--base=<last review folder>] [--w=1280 --h=800] [--chrome=PATH]
 *
 * WHY (IGF M01 benchmark, 2026-10-19): the required look at every screen was done by browser-driving subagents - 100 model
 * calls and $2.42 for one module, a third of the build's cost. The looking is still required; driving a browser to see is
 * not. This opens the module once in headless Chrome and photographs, at 1280 x 800:
 *   the deck    every slide, and every step of a figure that steps, as the deck's own Next shows them (each step at its end)
 *   each task   every question three times: as asked - every tap area and drop zone outlined and named by the script (a
 *               review overlay, never in the page) - then answered WRONG and checked, then answered RIGHT and checked
 *               (a fresh load), so the screen's own words say which. A question is answered by its own keys (the same
 *               FNV-1a key as gb_answer.js), so the script needs no answer list: if the engine does not say "right" for
 *               the right answer and "not right" for a wrong one, that is a FAILURE printed here - item 4 of the review
 *               list is checked by the script, not by eye.
 * The photographs go two to a sheet (stacked, full width, each with its label) - sheet_01.png ... - and a manifest of each
 * screen's picture hash. A screen whose picture did not change since the last review (manifest.json in the out folder)
 * is left off the new sheets, unless --all: a re-review looks only at what changed.
 * Exit 0 sheets made and every answer graded as expected; 1 an answer graded wrongly; 2 could not run.
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join, resolve, basename } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = {}, pos = [];
for (const a of args) { const m = a.match(/^--([\w-]+)(?:=(.*))?$/); if (m) opt[m[1]] = m[2] ?? true; else pos.push(a); }
if (pos.length !== 2) { console.error('usage: node review_sheets.mjs <module folder> <out folder> [--all]'); process.exit(2); }
const MDIR = resolve(pos[0]), OUT = resolve(pos[1]);
const W = Number(opt.w || 1280), H = Number(opt.h || 800);
const sleep = ms => new Promise(r => setTimeout(r, ms));

function findChrome(explicit) {
  const c = [explicit, process.env.CF_BROWSER, process.env.CHROME_PATH].filter(Boolean);
  if (process.platform === 'win32') {
    for (const b of [process.env.ProgramFiles, process.env['ProgramFiles(x86)'], process.env.LOCALAPPDATA].filter(Boolean)) {
      c.push(join(b, 'Google', 'Chrome', 'Application', 'chrome.exe'), join(b, 'Microsoft', 'Edge', 'Application', 'msedge.exe'));
    }
  } else if (process.platform === 'darwin') {
    c.push('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', join(homedir(), 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'));
  } else {
    for (const n of ['google-chrome', 'chromium', 'chromium-browser', 'microsoft-edge']) for (const d of ['/usr/bin', '/usr/local/bin', '/snap/bin']) c.push(join(d, n));
  }
  return c.find(p => p && existsSync(p)) || null;
}

/* ------------------------------------------------------------------ the browser */
const chromePath = findChrome(opt.chrome);
if (!chromePath) { console.error('review_sheets: no Chrome or Edge (set CF_BROWSER)'); process.exit(2); }
const profile = mkdtempSync(join(tmpdir(), 'cf-review-'));
const chrome = spawn(chromePath, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, `--window-size=${W},${H}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio', '--allow-file-access-from-files',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding', 'about:blank'], { stdio: 'ignore' });
let ws, nextId = 1;
const waiting = new Map(), handlers = [];
const send = (method, params = {}) => new Promise((res, rej) => { const id = nextId++; waiting.set(id, { res, rej, method }); ws.send(JSON.stringify({ id, method, params })); });
async function evaluate(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error('page: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
}
async function connect() {
  for (let i = 0; i < 120; i++) {
    try {
      const port = Number(readFileSync(join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]);
      const pg = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t => t.type === 'page');
      if (pg) return pg.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('Chrome did not start');
}
async function load(url) {
  const loaded = new Promise(res => handlers.push(m => { if (m.method === 'Page.loadEventFired') res(); }));
  await send('Page.navigate', { url });
  await Promise.race([loaded, sleep(20000)]);
  await evaluate('document.fonts ? document.fonts.ready.then(() => 1) : 1');
  await sleep(250);
}
async function shot(height) {
  const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: W, height: height || H, scale: 1 }, captureBeyondViewport: false });
  return Buffer.from(r.data, 'base64');
}
/* every animation at its end, every kit figure at the end of its step and held still - a flow that never ends is set to
   its start, so the same screen gives the same picture (the re-review compares pictures) */
const SETTLE = `(function(){
  document.querySelectorAll('svg[data-kit]').forEach(function(s){ var f=s.__kit; if(f&&f.go&&!s.closest('.slide:not(.active)')){ try{ f.go(f.n, true); if(f.layout) f.layout(); if(f.stop) f.stop(); }catch(e){} } });
  if (document.getAnimations) document.getAnimations().forEach(function(a){ try{ var t=a.effect&&a.effect.getTiming?a.effect.getTiming():{}; if(t.iterations===Infinity){ a.pause(); a.currentTime=0; } else a.finish(); }catch(e){} });
  return 1; })()`;

/* ------------------------------------------------------------------ the deck */
async function deck(tiles) {
  const page = join(MDIR, 'presentation', 'index.html');
  if (!existsSync(page)) return;
  await load(pathToFileURL(page).href);
  await evaluate(`(function(){ var b=document.getElementById('startBtn'); if(b) b.click(); return 1; })()`);
  await sleep(500);
  /* one picture per slide, a stepping figure at its LAST step - its fullest state, as the round-1 review looked at it;
     the drawing check (L54) already judges every step by measurement */
  const seen = new Set();
  for (let n = 0; n < 400; n++) {
    await sleep(160);
    const st = await evaluate(`(function(){ var s=document.querySelector('.slide.active'); if(!s) return null;
      var k=s.querySelector('svg[data-kit]'), f=k&&k.__kit; var all=[].slice.call(document.querySelectorAll('.slide'));
      if (f && f.steps && f.steps()) { try { f.go(f.steps(), true); } catch(e){} }
      return { id: s.id, i: all.indexOf(s)+1, of: all.length, title: s.getAttribute('data-title')||'', steps: f&&f.steps?f.steps():0,
               last: !!(document.getElementById('btnNext')||{}).disabled }; })()`);
    if (!st) break;
    if (seen.has(st.id)) {                      // still on it (a step was taken): its picture is retaken at this later state
      await evaluate(SETTLE); await sleep(140); await evaluate(SETTLE);
      const t = tiles.find(x => x.id === 'deck/' + st.id);
      if (t) t.png = await shot();
      if (st.last) break;
      await evaluate(`(function(){ var b=document.getElementById('btnNext'); if(b && !b.disabled) b.click(); return 1; })()`);
      continue;
    }
    if (!seen.size) await sleep(900);           // the first slide fades in after Start
    seen.add(st.id);
    await evaluate(`Promise.all([].slice.call(document.images).map(function(i){ return i.complete ? 1 : new Promise(function(r){ i.onload = i.onerror = r; setTimeout(r, 3000); }); })).then(function(){ return 1; })`);
    await evaluate(SETTLE); await sleep(140); await evaluate(SETTLE);
    tiles.push({ id: 'deck/' + st.id, label: `Deck slide ${st.i}/${st.of} (${st.id}) ${st.title}` + (st.steps ? ` - figure at its last step (${st.steps})` : ''), png: await shot() });
    if (st.last) break;
    await evaluate(`(function(){ var b=document.getElementById('btnNext'); if(b && !b.disabled) b.click(); return 1; })()`);
  }
}

/* ------------------------------------------------------------------ a task page, answered by its own keys */
const DRIVER = `
window.__rv = (function(){
  function norm(s){ return String(s).replace(/\\s+/g,' ').replace(/^ | $/g,''); }
  function txt(el){ return norm(el.textContent); }
  function imul(a,b){ var ah=(a>>>16)&0xffff, al=a&0xffff, bh=(b>>>16)&0xffff, bl=b&0xffff; return ((al*bl)+(((ah*bl+al*bh)<<16)>>>0)|0); }
  function key(id,text,value){ var s=unescape(encodeURIComponent(id+'|'+norm(text)+'|'+value)), h=0x811c9dc5, i; for(i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=imul(h,0x01000193)>>>0; } return ('0000000'+h.toString(16)).slice(-8); }
  function k(el){ return (el.getAttribute('data-key')||'').toLowerCase(); }
  function keyEl(it){ return it.hasAttribute('data-key') ? it : (it.parentNode.querySelector('[data-key]') || it); }
  function $$(s,r){ return [].slice.call((r||document).querySelectorAll(s)); }
  function go(){ var g=document.getElementById('go'); if(g && !g.disabled){ g.click(); return true; } return false; }
  function press(el){ var r=el.getBoundingClientRect(), o={bubbles:true,button:0,clientX:r.left+5,clientY:r.top+5};
    el.dispatchEvent(new MouseEvent('mousedown',o)); document.dispatchEvent(new MouseEvent('mouseup',o)); }
  function zv(z){ return norm(z.getAttribute('data-val')||''); }
  function place(c){ return (c.getAttribute('data-place')||c.getAttribute('data-key')||'').toLowerCase(); }
  function rightItems(id, box, val){
    return $$('.opt, .hot', box).filter(function(it){ var e=keyEl(it); return k(e)===key(id, txt(e), val); });
  }
  /* one part answered right (good=true) or wrong; returns false when it cannot be */
  function part(sec, el, prev, good){
    var id = sec.getAttribute('data-script');
    if (el.getAttribute('data-kind') === 'stop') {
      var chips = $$('.chip', prev || sec), r = chips.filter(function(c){ return k(c)===key(id, txt(c), '1'); });
      var pick = good ? r[0] : chips.filter(function(c){ return r.indexOf(c) < 0; })[0];
      if (!pick) return false; pick.click(); return true;
    }
    var did = false, cgs = $$('.cg', el), boxes = cgs.length ? cgs : ($$('.opt, .hot', el).length ? [el] : []);
    boxes.forEach(function(b, bi){
      var val = b.getAttribute('data-val') || '1', multi = b.getAttribute('data-multi')==='1' || sec.getAttribute('data-multi')==='1';
      var items = $$('.opt, .hot', b), r = rightItems(id, b, val);
      if (!items.length) return;
      if (good || bi > 0) { (multi ? r : r.slice(0,1)).forEach(function(it){ it.click(); }); }
      else { var w = items.filter(function(it){ return r.indexOf(it) < 0; })[0]; if (w) w.click(); else if (r.length > 1) r.slice(1).forEach(function(it){ it.click(); }); else r.forEach(function(it){ it.click(); }); }
      did = true;
    });
    var chips = $$('.chip', el), zones = $$('.zone', el);
    if (chips.length && zones.length) {
      var to = chips.map(function(c){ return zones.filter(function(z){ return key(id, txt(c), zv(z)) === place(c); })[0] || null; });
      if (!good) {                       /* wrong: the first two cards that belong in different places swap places */
        var a = -1, b = -1;
        to.forEach(function(z, i){ if (z && a < 0) a = i; else if (z && b < 0 && z !== to[a]) b = i; });
        if (a >= 0 && b >= 0) { var t = to[a]; to[a] = to[b]; to[b] = t; }
        else if (a >= 0) { to[a] = zones.filter(function(z){ return z !== to[a]; })[0] || to[a]; }
      }
      chips.forEach(function(c, ci){ if (to[ci]) { press(c); to[ci].click(); } });
      did = true;
    }
    $$('.dial', el).forEach(function(d){
      var lo=parseFloat(d.getAttribute('data-lo')), hi=parseFloat(d.getAttribute('data-hi')), st=parseFloat(d.getAttribute('data-step')), dec=parseInt(d.getAttribute('data-dec')||'0',10);
      var S=Math.pow(10,dec), n=Math.round((hi-lo)/st), unit=d.getAttribute('data-unit')||'', keys=k(d).split(/\\s+/), target=-1, wrong=-1, i;
      for (i=0;i<=n;i++){ var at=((Math.round(lo*S)+i*Math.round(st*S))/S).toFixed(dec); if(keys.indexOf(key(id,unit,at))>=0){ if(target<0) target=i; } else if(wrong<0) wrong=i; }
      var want = good ? target : wrong, plus = d.querySelector('.dial-plus');
      for (i=0; i<=want && plus; i++) plus.click();
      did = true;
    });
    return did;
  }
  return {
    start: function(){ if (!document.querySelector('.scr.on[data-script]')) go(); return 1; },     /* the try / intro screen's own button */
    current: function(){ var s = document.querySelector('.scr.on[data-script]') || $$('.scr[data-script]').filter(function(x){ return x.offsetParent; })[0]; return s ? s.getAttribute('data-script') : null; },
    ids: function(){ return $$('.scr[data-script]').map(function(s){ return s.getAttribute('data-script'); }); },
    overlay: function(on){
      var old = document.getElementById('__rvov'); if (old) old.remove();
      if (!on) return 1;
      var sec = document.querySelector('.scr.on[data-script]'); if (!sec) return 0;
      var ov = document.createElement('div'); ov.id='__rvov'; ov.style.cssText='position:absolute;left:0;top:0;width:0;height:0;z-index:99999;pointer-events:none';
      /* what the trainee taps or drops on - never a leader line, which carries data-part too */
      $$('.hot, .zone', sec).filter(function(h){ return h.tagName.toLowerCase() !== 'line'; }).forEach(function(h, i){
        var r = h.getBoundingClientRect(); if (!r.width || !r.height) return;
        var b = document.createElement('div');
        b.style.cssText = 'position:absolute;box-sizing:border-box;border:2px dashed #ff2bd6;left:'+(r.left+scrollX)+'px;top:'+(r.top+scrollY)+'px;width:'+r.width+'px;height:'+r.height+'px';
        var t = document.createElement('span'); t.textContent = (h.classList.contains('zone') ? 'zone ' : 'tap ') + (i+1);
        t.style.cssText = 'position:absolute;left:0;top:-15px;font:700 11px sans-serif;color:#fff;background:#ff2bd6;padding:0 3px';
        b.appendChild(t); ov.appendChild(b);
      });
      document.body.appendChild(ov); return 1;
    },
    answer: function(good){
      var sec = document.querySelector('.scr.on[data-script]'); if (!sec) return {error:'no question on screen'};
      var parts = $$('.part', sec); if (!parts.length) parts = [sec];
      var prev = null, i;
      for (i = 0; i < parts.length; i++) {
        if (!part(sec, parts[i], prev, good)) return {error:'could not answer part '+(i+1)};
        if (!go()) return {error:'Check stayed off after answering part '+(i+1)};
        if (i < parts.length - 1) { go(); }                                       /* "Go on": the next part opens */
        prev = parts[i];
      }
      var w = sec.querySelector('.why');
      return { ok: !!(w && w.classList.contains('good')), bad: !!(w && w.classList.contains('bad')), vd: txt(sec.querySelector('.vd')||document.body).slice(0,90) };
    },
    next: function(){ return go(); },
    /* 2.50.1 (M01 benchmark: three re-reviews were spent on these) - every leader line of the question on screen, as the
       engine placed it: it must end ON something drawn of the part it names, and cross no words but its own box's */
    leaders: function(){
      var sec = document.querySelector('.scr.on[data-script]'); if (!sec) return [];
      var svg = sec.querySelector('svg.taskfig'), f = svg && svg.__kit, out = [];
      function pt(line, which){ var p = line.ownerSVGElement.createSVGPoint(); p.x = +line.getAttribute(which==1?'x1':'x2'); p.y = +line.getAttribute(which==1?'y1':'y2');
        return p.matrixTransform(line.getScreenCTM()); }
      function shown(el){ for (var e = el; e && e.nodeType === 1; e = e.parentNode) { var cs = getComputedStyle(e);
        if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false; } return true; }
      function crosses(a, b, r){            /* segment a-b through rectangle r (1 px inside its edges) */
        var x0 = r.left + 1, x1 = r.right - 1, y0 = r.top + 1, y1 = r.bottom - 1, t0 = 0, t1 = 1, dx = b.x - a.x, dy = b.y - a.y;
        var ps = [-dx, dx, -dy, dy], qs = [a.x - x0, x1 - a.x, a.y - y0, y1 - a.y];
        if (x1 <= x0 || y1 <= y0) return false;
        for (var i = 0; i < 4; i++) { if (ps[i] === 0) { if (qs[i] < 0) return false; } else { var t = qs[i] / ps[i];
          if (ps[i] < 0) { if (t > t1) return false; if (t > t0) t0 = t; } else { if (t < t0) return false; if (t < t1) t1 = t; } } }
        return t1 - t0 > 0.02;
      }
      function name(id){ var b = sec.querySelector('.lbox[data-val="' + id + '"]'); return b ? (b.getAttribute('data-name') || id) : id; }
      $$('line[data-part]', sec).forEach(function(ln){
        if (!shown(ln)) return;
        var id = ln.getAttribute('data-part'), a = pt(ln, 1), b = pt(ln, 2), own = f && f.parts && f.parts[id] && f.parts[id].g;
        $$('svg.taskfig text, .lbox', sec).forEach(function(t){
          if (!shown(t) || (t.classList.contains('lbox') && t.getAttribute('data-val') === id)) return;
          if (own && own.contains(t)) return;              /* its own part's words: the leader is meant to reach them */
          if (t.closest && t.closest('.lbox[data-val="' + id + '"]')) return;
          var words = (t.textContent || '').replace(/\\s+/g, ' ').trim();
          if (!words && !t.classList.contains('lbox')) return;
          if (crosses(a, b, t.getBoundingClientRect())) out.push('the leader to "' + name(id) + '" crosses ' + (t.classList.contains('lbox') ? 'the label box of "' + (t.getAttribute('data-name') || t.getAttribute('data-val')) + '"' : 'the words "' + words.slice(0, 30) + '"'));
        });
        var part = f && f.parts && f.parts[id];
        if (part && part.g) {                /* its end on something painted of its part, within 8 px */
          var best = 1e9;
          $$('*', part.g).forEach(function(e){
            if (!e.getBBox || e.tagName === 'g' || !shown(e)) return;
            var cs = getComputedStyle(e); if (e.classList.contains('hit') || (cs.fill === 'none' && cs.stroke === 'none')) return;
            var r = e.getBoundingClientRect(); if (!r.width && !r.height) return;
            var ddx = Math.max(r.left - b.x, 0, b.x - r.right), ddy = Math.max(r.top - b.y, 0, b.y - r.bottom);
            best = Math.min(best, Math.sqrt(ddx * ddx + ddy * ddy));
          });
          if (best > 8 && best < 1e9) out.push('the leader to "' + name(id) + '" ends ' + Math.round(best) + ' px from anything drawn of its part');
        }
      });
      return out;
    }
  };
})();`;

async function tasks(tiles, failures) {
  const pages = [];
  for (const d of ['tasks', 'assessment']) {
    const dir = join(MDIR, d);
    if (!existsSync(dir)) continue;
    for (const f of readdirSync(dir).sort()) if (f.endsWith('.html') && !/answer_key/i.test(f)) pages.push(join(dir, f));
  }
  for (const page of pages) {
    const url = pathToFileURL(page).href, name = basename(page);
    await load(url);
    await evaluate(DRIVER);
    const ids = await evaluate('__rv.ids()');
    // pass 1: asked (with the overlay), then wrong; pass 2 (a fresh load): right
    for (const good of [false, true]) {
      if (good) { await load(url); await evaluate(DRIVER); }
      await evaluate('__rv.start()');
      await sleep(200);
      for (let n = 0; n < ids.length; n++) {
        const q = await evaluate('__rv.current()');
        if (!q) break;
        await evaluate(SETTLE); await sleep(150); await evaluate(SETTLE);
        if (!good) for (const x of await evaluate('__rv.leaders()')) failures.push(`${name} ${q}: ${x}`);
        if (opt.asked && good) tiles.push({ id: `${name}/${q}/asked`, label: `${name} ${q} - as asked`, png: await shot() });
        const r = await evaluate(`__rv.answer(${good})`);
        await sleep(220); await evaluate(SETTLE); await sleep(80);
        if (!good) await evaluate('__rv.overlay(true)');      // the tap areas and drop zones, outlined on the wrong-answer screen
        if (r.error) {
          failures.push(`${name} ${q}: answered ${good ? 'right' : 'wrong'} by the script - ${r.error}`);
          tiles.push({ id: `${name}/${q}/${good ? 'right' : 'wrong'}`, label: `${name} ${q} - could not be answered ${good ? 'right' : 'wrong'}: ${r.error}`, png: await shot() });
          break;
        } else if (good && !r.ok) failures.push(`${name} ${q}: the RIGHT answer (by its own keys) was graded not right - "${r.vd}"`);
        else if (!good && !r.bad) failures.push(`${name} ${q}: a WRONG answer was graded right - "${r.vd}"`);
        if (!opt.asked) tiles.push({ id: `${name}/${q}/${good ? 'right' : 'wrong'}`, label: `${name} ${q} - answered ${good ? 'RIGHT' : 'WRONG'} and checked: "${r.vd || ''}"`
                     + (good ? '' : ' (pink: every tap area / drop zone, review overlay only)'), png: await shot() });
        if (!good) await evaluate('__rv.overlay(false)');
        await evaluate('__rv.next()');
        await sleep(180);
      }
    }
  }
}

/* ------------------------------------------------------------------ the sheets */
async function sheets(tiles) {
  mkdirSync(OUT, { recursive: true });
  const manPath = join(OUT, 'manifest.json');
  const basePath = join(opt.base ? resolve(opt.base) : OUT, 'manifest.json');     // --base: compare with the last review's folder
  const before = existsSync(basePath) ? JSON.parse(readFileSync(basePath, 'utf8')) : {};
  /* "changed" is judged on a fingerprint - the screen's mean grey in 16 x 16 px cells - not on the bytes: a pipe's flow or a
     gas cloud's drift is never caught at the same phase twice, and the fingerprint does not see it; a word, a moved part,
     a label or a colour changes the cells it is in */
  await load('about:blank');
  const fps = await evaluate(`(async function(){ var out=[], data=${JSON.stringify(tiles.map(t => t.png.toString('base64')))};
    var c=document.createElement('canvas'); c.width=${Math.ceil(W / 16)}; c.height=${Math.ceil(H / 16)}; var x=c.getContext('2d');
    for (var i=0;i<data.length;i++){ var im=new Image(); im.src='data:image/png;base64,'+data[i]; await im.decode();
      x.drawImage(im,0,0,c.width,c.height); var d=x.getImageData(0,0,c.width,c.height).data, g=[];
      for (var j=0;j<d.length;j+=4) g.push(Math.round((d[j]+d[j+1]+d[j+2])/3));
      out.push(g); }
    return out; })()`);
  const now = {};
  tiles.forEach((t, i) => { t.fp = fps[i]; now[t.id] = Buffer.from(t.fp).toString('base64'); });
  const differs = t => {
    if (!before[t.id]) return true;
    const a = Buffer.from(before[t.id], 'base64');
    if (a.length !== t.fp.length) return true;
    let worst = 0;
    for (let i = 0; i < a.length; i++) worst = Math.max(worst, Math.abs(a[i] - t.fp[i]));
    return worst > 8;
  };
  const show = opt.all ? tiles : tiles.filter(differs);
  for (const f of readdirSync(OUT)) if (/^sheet_\d+\.png$/.test(f)) rmSync(join(OUT, f));
  const LBL = 30, out = [];
  /* the sheet is a page of files, never a data: URL - one with a photo slide passed Chrome's 2 MB limit and came out black */
  const tmpDir = join(profile, 'sheet');
  mkdirSync(tmpDir, { recursive: true });
  for (let i = 0; i < show.length; i += 2) {
    const pair = show.slice(i, i + 2);
    pair.forEach((t, k) => writeFileSync(join(tmpDir, `t${i + k}.png`), t.png));
    const html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#111">' + pair.map((t, k) =>
      `<div style="height:${LBL}px;font:700 16px/30px sans-serif;color:#fff;background:#333;padding:0 10px;white-space:nowrap;overflow:hidden">${t.label.replace(/</g, '&lt;')}</div>` +
      `<img style="display:block;width:${W}px;height:${H}px" src="t${i + k}.png">`).join('') + '</body></html>';
    const hh = pair.length * (H + LBL);
    writeFileSync(join(tmpDir, `s${i}.html`), html);
    await send('Emulation.setDeviceMetricsOverride', { width: W, height: hh, deviceScaleFactor: 1, mobile: false });
    await load(pathToFileURL(join(tmpDir, `s${i}.html`)).href);
    const png = await shot(hh);
    const f = join(OUT, `sheet_${String(out.length + 1).padStart(2, '0')}.png`);
    writeFileSync(f, png);
    out.push({ file: basename(f), screens: pair.map(t => t.label) });
  }
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  writeFileSync(manPath, JSON.stringify(now, null, 1));
  return { out, total: tiles.length, shown: show.length };
}

/* ------------------------------------------------------------------ run */
let code = 2;
try {
  ws = new WebSocket(await connect());
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', () => rej(new Error('websocket'))); });
  ws.addEventListener('message', ev => {
    const m = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString());
    if (m.id && waiting.has(m.id)) { const w = waiting.get(m.id); waiting.delete(m.id); m.error ? w.rej(new Error(w.method + ': ' + m.error.message)) : w.res(m.result); }
    else if (m.method) handlers.forEach(h => h(m));
  });
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  const tiles = [], failures = [];
  await deck(tiles);
  await tasks(tiles, failures);
  const r = await sheets(tiles);
  const list = r.out.map(s => `  ${s.file}\n${s.screens.map(x => '      ' + x).join('\n')}`).join('\n');
  writeFileSync(join(OUT, 'sheets.json'), JSON.stringify({ sheets: r.out, failures, total: r.total, shown: r.shown }, null, 1));
  console.log(`Review sheets: ${r.shown} of ${r.total} screens ${opt.all ? '' : '(changed since the last review) '}on ${r.out.length} sheet(s) in ${OUT}`);
  if (opt.list) console.log(list);
  failures.forEach(f => console.log('  FAIL ' + f));
  console.log(failures.length ? `${failures.length} task-page problem(s)` : 'Every question graded as expected: wrong answers not right, right answers right; every leader line ends on its part and crosses no words.');
  code = failures.length ? 1 : 0;
} catch (e) {
  console.error('review_sheets: ' + (e && e.message || e));
  code = 2;
} finally {
  try { chrome.kill(); } catch {}
  await sleep(300);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
  process.exit(code);
}
