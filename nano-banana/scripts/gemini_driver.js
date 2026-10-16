/* Gemini browser driver - paste this whole file into ONE javascript_tool call on gemini.google.com, once per tab.
   It defines window.GB; every later call is one short line:
     GB.state()            signed in? which model? is a reply still running?
     await GB.send(prompt, {aspect: '16:9'})   new chat, Images tool on, aspect ratio, prompt in, Send
     await GB.wait()       up to 38 s; call again while it says {done:false}
     await GB.download()   click Gemini's own "Download full size image" on the newest picture
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
             editor: !!editor(), busy: busy(), replies: replies().length, url: location.pathname, blocked: blocked() };
  }

  // the Images tool must be on: without it a Workspace account answers "I am unable to generate images" (2026-10-16)
  async function imagesTool(aspect) {
    if (!btn(/^close images$/i)) {
      const tools = btn(/^upload and tools$|^tools$/i);
      if (!tools) return 'no Upload and tools button';
      tools.click();
      await sleep(800);
      const item = $$('gem-list-item, [role=menuitem], button').filter(e => e.offsetParent).find(e => /^create image$/i.test(label(e)));
      if (!item) { document.body.click(); return 'no Create image in the tools menu'; }
      item.click();
      await sleep(800);
      if (!btn(/^close images$/i)) return 'the Images tool did not switch on';
    }
    if (aspect) {
      const ar = btn(/^aspect ratio$/i);
      if (ar) {
        ar.click();
        await sleep(600);
        const opt = $$('[role=menuitemradio]').find(e => e.innerText.trim() === aspect);
        if (!opt) { document.body.click(); return 'no ' + aspect + ' in the aspect ratio menu'; }
        opt.click();
        await sleep(500);
        // the setting outlives the chat: a stray 3:4 once turned a 4:3 prompt into a portrait picture - check it took
        ar.click();
        await sleep(500);
        const now = $$('[role=menuitemradio]').find(e => e.getAttribute('aria-checked') === 'true');
        const got = now ? now.innerText.trim() : '?';
        if (now) now.click(); else document.body.click();
        await sleep(300);
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

  async function send(prompt, { newChat = true, aspect = '16:9' } = {}) {
    if (newChat) {
      const nc = btn(/^new chat$/i);
      if (nc) { nc.click(); await sleep(2500); }
    }
    const tool = await imagesTool(aspect);
    if (tool) return { sent: false, why: tool };
    const ed = editor();
    if (!ed) return { sent: false, why: 'no prompt box - is gemini.google.com/app open and signed in?' };
    ed.focus();                                   // Gemini enforces Trusted Types: no innerHTML, edit like a keyboard
    document.execCommand('selectAll', false);
    document.execCommand('delete', false);
    document.execCommand('insertText', false, prompt);
    ed.dispatchEvent(new InputEvent('input', { bubbles: true }));
    mark();
    // a new chat can drop the Images chip a moment after it loads (2026-10-16: the prompt went out as text) -
    // check it once more right before Send
    await sleep(600);
    if (!btn(/^close images$/i)) {
      const again = await imagesTool(aspect);
      if (again || !btn(/^close images$/i)) return { sent: false, why: again || 'the Images tool switched itself off' };
    }
    for (let i = 0; i < 20; i++) {
      const s = btn(/^send message$/i);
      if (s && !s.disabled && s.getAttribute('aria-disabled') !== 'true') { s.click(); return { sent: true, chars: prompt.length }; }
      await sleep(250);
    }
    return { sent: false, why: 'the Send button never became active' };
  }

  async function wait(maxMs = 38000) {
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

  return { state, send, wait, retry, download };
})();
GB.state();
