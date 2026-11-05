/* Gemini browser driver - paste this whole file into ONE javascript_tool call on gemini.google.com, once per tab.
   It defines window.GB; every later call is one short line:
     GB.state()            signed in? which model? is a reply still running? Images on, which aspect?
     await GB.prompt(text, {aspect: '16:9'})   new chat, Images tool on, aspect ratio, prompt in - not sent yet
     await GB.press()      Send - in its own call, 2-3 s after GB.prompt
     await GB.wait()       up to 15 s; call again while it says {done:false}
     await GB.show()       built-in pane: the newest picture 1:1 over the whole page, and the tiles to zoom
     GB.hide()             takes that overlay away (GB.prompt does it too)
     await GB.download()   Claude in Chrome: click Gemini's own "Download full size image" on the newest picture
   Every function returns a small object - never the page, never the picture bytes.
   Selectors are by role and aria-label first, so a Gemini redesign breaks one line here, not the skill. */
window.GB = (() => {
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const label = b => (b.getAttribute('aria-label') || b.getAttribute('mattooltip') || b.innerText || '').trim();
  const btn = (rx, root = document) => $$('button, a[role=button], [role=button]', root).find(b => rx.test(label(b)));
  const editor = () => document.querySelector('rich-textarea .ql-editor, .ql-editor[contenteditable=true], div[contenteditable=true][role=textbox]');
  const replies = () => $$('model-response');
  const last = () => replies().pop() || null;
  const pictures = root => root ? $$('img', root).filter(i => i.naturalWidth >= 256 && !/\/a\/|avatar|profile/i.test(i.src)) : [];
  const busy = () => !!btn(/^stop (response|generating)/i);
  // the chip and the button have had two labels each: "Close Images" / "Deselect Images", "Aspect ratio" / "Aspect ratio, 16:9"
  const IMAGES_ON = /^(close|deselect) images$/i;
  const ASPECT = /^aspect ratio\b/i;
  const aspectOf = b => ((/^aspect ratio,\s*(\d+:\d+)/i.exec(b ? label(b) : '') || [])[1]) || null;
  const ratioIn = (e, aspect) => new RegExp('(^|[^\\d])' + aspect + '([^\\d]|$)').test((e.innerText || label(e) || '').trim());
  const FAIL = /can't (create|generate|make)|cannot (create|generate)|unable to (create|generate)|isn't available|not available in your|are you signed in|try again later|encountered an error|limit/i;
  let before = 0, beforeText = '';
  const mark = () => { before = replies().length; beforeText = (last() || {}).innerText || ''; };

  // Gemini's own "I encountered an error" -> its Redo -> Try again, in the same chat (counts as the second try)
  async function retry() {
    const r = last();
    const redo = r && btn(/^redo$/i, r);
    if (!redo) return { retried: false, why: 'no Redo button on the newest reply' };
    mark();
    redo.click();
    await sleep(800);
    const again = $$('[role=menuitem]').filter(e => e.offsetParent).find(e => /^try again$/i.test(label(e)));
    if (!again) { document.body.click(); return { retried: false, why: 'no Try again in the Redo menu' }; }
    again.click();
    return { retried: true };
  }

  function state() {
    const signIn = $$('a, button').some(b => /^sign in$/i.test(label(b)) && b.offsetParent);
    const model = btn(/mode picker|model/i);
    return { signedIn: !signIn, model: model ? label(model).replace(/^open mode picker, currently /i, '') : null,
             editor: !!editor(), busy: busy(), replies: replies().length, url: location.pathname, blocked: blocked(),
             images: !!btn(IMAGES_ON), aspect: aspectOf(btn(ASPECT)) };
  }

  // the Images tool must be on: without it a Workspace account answers "I am unable to generate images" (2026-10-16)
  async function imagesTool(aspect) {
    if (!btn(IMAGES_ON)) {
      const tools = btn(/^upload and tools$|^tools$/i);
      if (!tools) return 'no Upload and tools button';
      tools.click();
      await sleep(800);
      const item = $$('gem-list-item, [role=menuitem], button').filter(e => e.offsetParent).find(e => /^create image$/i.test(label(e)));
      if (!item) { document.body.click(); return 'no Create image in the tools menu'; }
      item.click();
      await sleep(800);
      if (!btn(IMAGES_ON)) return 'the Images tool did not switch on';
    }
    if (aspect) {
      const ar = btn(ASPECT);
      if (ar && aspectOf(ar) !== aspect) {
        ar.click();
        await sleep(600);
        const opt = $$('[role=menuitemradio]').find(e => ratioIn(e, aspect));
        if (!opt) { document.body.click(); return 'no ' + aspect + ' in the aspect ratio menu'; }
        opt.click();
        await sleep(500);
        // the setting outlives the chat: a stray 3:4 once turned a 4:3 prompt into a portrait picture - check it took.
        // The new button names the ratio; the old one needs its menu opened again
        let got = aspectOf(btn(ASPECT));
        if (!got) {
          ar.click();
          await sleep(500);
          const now = $$('[role=menuitemradio]').find(e => e.getAttribute('aria-checked') === 'true');
          got = now ? ((/\d+:\d+/.exec(now.innerText || '') || [])[0] || now.innerText.trim()) : '?';
          if (now) now.click(); else document.body.click();
          await sleep(300);
        }
        if (got !== aspect) return 'the aspect ratio is ' + got + ', not ' + aspect;
      }
    }
    return '';
  }

  // Google's unusual-traffic check (www.google.com/sorry) shows up in Gemini as "Check your internet connection"
  // and every later call fails. It is a CAPTCHA: stop, never try to pass it - the person opens Gemini themselves.
  const BLOCK = /check your internet connection|unusual traffic|google\.com\/sorry|something went wrong/i;
  const blocked = () => $$('simple-snack-bar, .mat-mdc-snack-bar-label, [role=status], [role=alert]')
    .map(e => (e.innerText || '').trim()).find(t => BLOCK.test(t)) || '';

  // the daily picture limit: "You've reached your image-generation limit until 7:42 PM" - Flash stops at the same moment.
  // at = that end as a local time with its offset when the reply gives a clock time (today or tomorrow), else null
  const LIMIT = /(?:reached|hit) (?:your|the) (?:daily )?image[- ]?(?:generation|creation) limit/i;
  function limitOf(text, now = new Date()) {
    const s = (text || '').replace(/\s+/g, ' ');
    const m = LIMIT.exec(s);
    if (!m) return null;
    const u = /^[^.]{0,80}?\b(?:until|till|resets? (?:at|on))\s+(.+?)(?:\.(?=\s|$)|$)/i.exec(s.slice(m.index + m[0].length));
    const until = u ? u[1].trim() : '';
    let at = null;
    const t = /\b(\d{1,2})[:.](\d{2})\s*(?:([ap])\.?\s?m\.?)?(?=\W|$)/i.exec(until);
    if (t && !/[a-z0-9]/i.test(until.replace(t[0], '').replace(/\b(today|tomorrow)\b/i, ''))) {
      let h = +t[1];
      if (t[3]) h = (h % 12) + (/p/i.test(t[3]) ? 12 : 0);
      const d = new Date(now);
      d.setHours(h, +t[2], 0, 0);
      if (/tomorrow/i.test(until) || d <= now) d.setDate(d.getDate() + 1);
      const p = n => String(Math.abs(n)).padStart(2, '0'), off = -d.getTimezoneOffset();
      at = d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T' + p(d.getHours()) + ':' + p(d.getMinutes())
        + ':00' + (off < 0 ? '-' : '+') + p(Math.trunc(off / 60)) + ':' + p(off % 60);
    }
    return { limit: true, until, at };
  }

  // the prompt goes in and Send is pressed in two calls, 2-3 s apart: one long call times the browser tool out
  async function prompt(text, { newChat = true, aspect = '16:9' } = {}) {
    hide();
    if (newChat) {
      const nc = btn(/^new chat$/i);
      if (nc) { nc.click(); await sleep(2500); }
    }
    const tool = await imagesTool(aspect);
    if (tool) return { put: false, why: tool };
    const ed = editor();
    if (!ed) return { put: false, why: 'no prompt box - is gemini.google.com/app open and signed in?' };
    ed.focus();                                   // Gemini enforces Trusted Types: no innerHTML, edit like a keyboard
    document.execCommand('selectAll', false);
    document.execCommand('delete', false);
    document.execCommand('insertText', false, text);
    ed.dispatchEvent(new InputEvent('input', { bubbles: true }));
    return { put: true, chars: text.length, aspect: aspectOf(btn(ASPECT)) || aspect };
  }

  async function press() {
    // a new chat can drop the Images chip a moment after it loads (2026-10-16: the prompt went out as text) -
    // check it once more right before Send
    if (!btn(IMAGES_ON)) {
      const again = await imagesTool(aspectOf(btn(ASPECT)));
      if (again || !btn(IMAGES_ON)) return { sent: false, why: again || 'the Images tool switched itself off' };
    }
    for (let i = 0; i < 20; i++) {
      const s = btn(/^send message$/i);
      if (s && !s.disabled && s.getAttribute('aria-disabled') !== 'true') { mark(); s.click(); return { sent: true }; }
      await sleep(250);
    }
    return { sent: false, why: 'the Send button never became active' };
  }

  async function wait(maxMs = 15000) {
    const t0 = Date.now();
    while (Date.now() - t0 < maxMs) {
      const stop = blocked();
      if (stop) return { done: true, pictures: 0, blocked: stop, note: 'Google is checking for unusual traffic - STOP the loop' };
      const r = last();
      // a new reply, or the same reply redone (Redo -> Try again replaces it in place)
      if (r && (replies().length > before || (r.innerText || '') !== beforeText)) {
        const pics = pictures(r);
        if (pics.length && !busy()) {
          await sleep(1500);
          return { done: true, pictures: pics.length, size: pics.map(i => i.naturalWidth + 'x' + i.naturalHeight), secs: (Date.now() - t0) / 1000 };
        }
        const text = (r.innerText || '').replace(/\s+/g, ' ').trim();
        const lim = !busy() && !pics.length && limitOf(text);
        if (lim) return { done: true, pictures: 0, ...lim, note: 'the daily picture limit - STOP the loop, resume at ' + (lim.at || lim.until || 'the time Gemini names') };
        if (!busy() && !pics.length && text.length > 20 && FAIL.test(text)) return { done: true, pictures: 0, failed: text.slice(0, 300) };
      }
      await sleep(1000);
    }
    return { done: false, busy: busy(), note: 'still working - call GB.wait() again' };
  }

  async function download(index = 0) {
    const r = last();
    const pics = pictures(r);
    if (!pics.length) return { clicked: false, why: 'no picture in the newest reply' };
    const pic = pics[Math.min(index, pics.length - 1)];
    let host = pic;
    for (let k = 0; k < 8 && host && !btn(/download/i, host); k++) host = host.parentElement;
    pic.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    await sleep(400);
    const d = (host && btn(/download/i, host)) || btn(/download/i, r);
    if (!d) return { clicked: false, why: 'no Download button next to the picture', buttons: $$('button', r).map(label).filter(Boolean).slice(0, 20) };
    d.click();
    return { clicked: true, button: label(d) };
  }

  // a zoom of up to 512 x 572 comes back 1:1: a 16:9 picture (1024 x 572) is 2 x 1 tiles, a 4:3 one (1024 x 765) 2 x 2.
  // gemini_take.py stitch cuts the same way
  const TILE = [512, 572];
  function tiles(w, h) {
    const cols = Math.ceil(w / TILE[0]), rows = Math.ceil(h / TILE[1]);
    const cut = (n, k) => [...Array(k + 1).keys()].map(i => Math.floor(n * i / k));
    const xs = cut(w, cols), ys = cut(h, rows), rects = [];
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) rects.push([xs[i], ys[j], xs[i + 1], ys[j + 1]]);
    return { cols, rows, tiles: rects };
  }

  // the built-in pane takes no Copy image (clipboard denied), no Download (it asks where to save) and no post to this
  // computer (Gemini's CSP): the newest picture is shown 1:1 over the whole page, zoomed tile by tile and stitched back
  async function show(index = 0) {
    hide();
    const pics = pictures(last());
    if (!pics.length) return { shown: false, why: 'no picture in the newest reply' };
    const pic = pics[Math.min(index, pics.length - 1)];
    const w = pic.naturalWidth, h = pic.naturalHeight;
    const box = document.createElement('div');
    box.id = 'gb-overlay';
    box.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:#000;margin:0;padding:0;overflow:hidden';
    const img = document.createElement('img');
    img.style.cssText = 'position:absolute;left:0;top:0;width:' + w + 'px;height:' + h + 'px;max-width:none;max-height:none;margin:0;padding:0;border:0';
    img.src = pic.currentSrc || pic.src;
    box.appendChild(img);
    document.body.appendChild(box);
    try { await img.decode(); } catch (e) { hide(); return { shown: false, why: 'the picture did not load in the overlay' }; }
    return { shown: true, size: w + 'x' + h, since: Math.floor(Date.now() / 1000), fits: w <= innerWidth && h <= innerHeight,
             viewport: innerWidth + 'x' + innerHeight, dpr: window.devicePixelRatio || 1, ...tiles(w, h) };
  }
  function hide() {
    const o = document.getElementById('gb-overlay');
    if (o) o.remove();
    return { hidden: true };
  }

  return { state, prompt, press, wait, show, hide, tiles, limitOf, retry, download };
})();
GB.state();
