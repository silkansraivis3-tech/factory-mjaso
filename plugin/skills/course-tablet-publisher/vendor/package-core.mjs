// Shared by the browser, upload gate and filesystem regression tests. Never executes course JS.
export const LIMITS = { files: 6000, bytes: 300 * 1024 * 1024, file: 6 * 1024 * 1024, batch: 3 * 1024 * 1024, batchFiles: 24 };
export const HASH = /^[a-f0-9]{64}$/;
export function safePath(path) {
  return typeof path === 'string' && path.length < 500 && !/[\\\x00-\x1f\x7f%?#:]/.test(path)
    && path.split('/').every(p => p && p !== '.' && p !== '..' && !p.startsWith('.'));
}
// Working material that travels with an author's folder but is not the course: saved earlier
// versions (_versions/, _old_m21/), experiments (_probes/), packed copies, a test module. A
// folder whose name starts with "_" is the author's own by convention - except _course_shell,
// which holds the course's own map and shell. Left in, these broke the import on links that
// pointed at assets only the real module has, and doubled the size of the package.
export function internal(path) {
  return /(^|\/)(?:oldversion|_full_decks[^/]*|00_SME_REVIEW|01_MANAGEMENT_OVERVIEW|apps_script_ready|_claude_working_area|knowledge_base|source_files|__pycache__|node_modules|tablet_package)(\/|$)/i.test(path)
    || /(^|\/)(?!_course_shell\/)_[^/]*\//.test(path)
    || /^test_[^/]*\//i.test(path)
    || /\.(?:bak.*|orig|zip|tgz|tar|gz|7z|rar|py|gs|md|txt|frozen-backup|unverified-new)$/i.test(path);
}
export function instructorOnly(path) {
  return /(^|\/)(?:instructor[^/]*|presentation|plan|plans|prepare|record|answers|instructor_screens)(\/|$)/i.test(path)
    || /(?:answer[_-]?key|model[_-]?answer|_criteria|instructor[_-]analysis|observation_checklist|practical_skills_record|atbildes|pasniedzejam|pasniedzējam|gb_answers|gb_review|gb_roster|gb_observe|_paper\.html|START_HERE\.html|START_COURSE\.html|COURSE\.html|module\.html|assessment\/record\.html|MODULE_\d+_PLAN|ROTATION_PLAN|SAFETY_BRIEF)/i.test(path);
}
// How many screens a module actually has. Counted off the deck when the course is imported,
// so the number is written down once instead of being worked out again every time somebody
// opens the catalogue - and so it is right for the deck that was published, not for whatever
// is on somebody's disk today.
export function countSlides(text) {
  if (typeof text !== 'string') return null;
  return (text.match(/class\s*=\s*"(?:[^"]*\s)?slide(?:\s[^"]*)?"/gi) || []).length;
}

// What this course is, in a sentence, without anybody having to write one. A course that says
// so itself is quoted; otherwise the only honest description is what it is made of, which is
// still more use than an empty box.
// The name of a module, out of a deck title written for a browser tab. "GAS BASIC ·
// Module 1 — Gas Carriers and Their Cargoes · Instructor presentation" is the course, the
// module, and what kind of file this is; only the middle is the name.
export function moduleName(title) {
  const parts = String(title || '').replace(/\s+/g, ' ').trim().split(/\s+[·|]\s+/).filter(Boolean);
  if (!parts.length) return '';
  const marked = parts.findIndex(p => /\b(?:module|m)\s*\d+\b/i.test(p));
  let t = marked >= 0 ? parts[marked] : (parts.length > 1 ? parts[1] : parts[0]);
  t = t.replace(/^(?:module|m)\s*\d+\s*(?:[—–\-:]\s*)?/i, '').trim();
  if (!t && marked >= 0 && parts[marked + 1]) t = parts[marked + 1];
  const inBrackets = /^(?:instructor )?(?:screens?|presentation|deck)\s*\((.+)\)$/i.exec(t);
  if (inBrackets) t = inBrackets[1];
  t = t.replace(/\s*\((?:instructor )?(?:screens?|presentation|deck)\)$/i, '')
       .replace(/\s*[—–-]\s*(?:instructor )?(?:screens?|presentation|deck)$/i, '');
  return t.trim();
}

export function describeCourse(manifest, rootText) {
  const meta = typeof rootText === 'string' && rootText.match(/<meta[^>]+name\s*=\s*["']description["'][^>]*content\s*=\s*["']([^"']{20,400})["']/i);
  if (meta) return meta[1].trim();
  const entries = (manifest && manifest.moduleEntries) || [];
  if (!entries.length) return '';
  const slides = entries.reduce((n, m) => n + (m.slides || 0), 0);
  const titles = entries.map(m => moduleName(m.title) || String(m.code || '').trim()).filter(Boolean);
  const size = `${entries.length} ${entries.length === 1 ? 'module' : 'modules'}${slides ? `, ${slides} slides` : ''}`;
  return titles.length ? `${size}: ${titles.join('; ')}.` : `${size}.`;
}

export function slug(value) { return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100); }
export async function digest(bytes) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(n => n.toString(16).padStart(2, '0')).join(''); }
export function textIssues(path, text) {
  const errors = [], warnings = [];
  if (/(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\bghp_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}|["'\s]sk-[A-Za-z0-9_-]{24,}|["']client_secret["']\s*:|["']type["']\s*:\s*["']service_account["'])/.test(text)) errors.push(`Possible access key in file: ${path}`);
  for (const jwt of text.match(/eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g) || []) {
    try { if (JSON.parse(atob(jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).role !== 'anon') errors.push(`Non-public access key: ${path}`); } catch { errors.push(`Unrecognised access key: ${path}`); }
  }
  if (/<script\b[^>]*\bsrc\s*=\s*["'](?:https?:)?\/\//i.test(text)) errors.push(`Offline, an external script is required: ${path}`);
  if (/fonts\.(?:googleapis|gstatic)\.com/.test(text)) warnings.push(`Offline, a fallback font will be used: ${path}`);
  return { errors, warnings };
}
function references(path, text) {
  const out = [];
  if (!/\.(html?|css|svg)$/i.test(path)) return out;
  text = text.replace(/<!--[\s\S]*?-->/g, '').replace(/(<script\b[^>]*>)[\s\S]*?<\/script>/gi, '$1</script>');
  for (const match of text.matchAll(/\b(src|href|poster)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^)'"\s]+)["']?\s*\)/gi)) {
    const value = match[2] || match[3];
    if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(value)) continue;
    try {
      const url = new URL(value, 'https://package.invalid/' + path);
      out.push({ path: decodeURIComponent(url.pathname.slice(1)), required: match[1]?.toLowerCase() !== 'href' || /\.css(?:[?#]|$)/i.test(value) });
    } catch { /* Invalid authored navigation is reported by its course audit. */ }
  }
  return out;
}
export function validateDescriptor(manifest, files) {
  const errors = [];
  if (!manifest || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(manifest.id || '') || manifest.id.length > 100) errors.push('The course ID must be a unique name without spaces.');
  if (typeof manifest?.title !== 'string' || !manifest.title.trim() || manifest.title.length > 300) errors.push('Give the course title.');
  if (!/^\d+\.\d+\.\d+$/.test(manifest?.version || '')) errors.push('Version: for example, 1.0.0.');
  if (!Number.isInteger(manifest?.modules) || manifest.modules < 1 || manifest.modules > 99) errors.push('The number of modules must be 1–99.');
  if (!Array.isArray(files) || !files.length || files.length > LIMITS.files) return [...errors, 'Invalid file count.'];
  // The store keeps one object per checksum, so a file that is both in the trainee and the
  // instructor copy - every picture of every module - takes its space once. Counted per path,
  // a 170 MB course came out as 350 MB and was refused.
  const seen = new Set(), stored = new Set(); let size = 0;
  for (const f of files) {
    if (!safePath(f.path) || !/^(trainee|instructor)\//.test(f.path)) errors.push(`Invalid path: ${f.path}`);
    if (seen.has(f.path)) errors.push(`Duplicate path: ${f.path}`); seen.add(f.path);
    if (f.path.startsWith('trainee/') && instructorOnly(f.path.slice(8))) errors.push(`Instructor-only file in trainee package: ${f.path}`);
    if (!HASH.test(f.sha256 || '') || !Number.isSafeInteger(f.size) || f.size < 0 || f.size > LIMITS.file) errors.push(`Invalid file size or checksum: ${f.path}`);
    if (!stored.has(f.sha256)) { stored.add(f.sha256); size += f.size; }
  }
  if (size > LIMITS.bytes) errors.push('The prepared package is over 300 MB.');
  if (!seen.has('trainee/course.json')) errors.push('The generated course descriptor is missing.');
  if (manifest?.moduleEntries) {
    if (!Array.isArray(manifest.moduleEntries) || manifest.moduleEntries.length !== manifest.modules) errors.push('The module list and the module count do not match.');
    else for (const m of manifest.moduleEntries) if (!seen.has(m.entry)) errors.push(`Missing module start page: ${m.entry}`);
  } else if (![...seen].some(p => /^trainee\/(?:module_\d+|modules\/m\d+)\//i.test(p))) errors.push('The module list is missing.');
  return errors;
}
export function batches(files) {
  const result = []; let current = [], size = 0;
  for (const f of files) {
    if (current.length && (size + f.size > LIMITS.batch || current.length >= LIMITS.batchFiles)) { result.push(current); current = []; size = 0; }
    current.push(f); size += f.size;
  }
  if (current.length) result.push(current);
  return result;
}
export async function fingerprint(files) { return digest(new TextEncoder().encode(JSON.stringify(files.map(({path,sha256,size}) => ({path,sha256,size}))))); }

// File-like objects: {path,size,text(),arrayBuffer()}. Source files are never modified.
export async function prepareCourse(source, progress = () => {}) {
  const original = new Map(source.map(f => [f.path, f]));
  if (original.size !== source.length || source.some(f => !safePath(f.path))) throw new Error('The folder has duplicate or disallowed file paths.');
  const ready = source.some(f => f.path.startsWith('trainee/'));
  const texts = new Map(), errors = [], warnings = [], skipped = [], entries = [];
  const allowed = source.filter(f => { if (internal(f.path)) { skipped.push(f.path); return false; } return true; });
  for (const f of allowed) if (/\.(html?|js|mjs|css|json|svg)$/i.test(f.path)) {
    const text = await f.text(); texts.set(f.path, text);
    const issues = textIssues(f.path, text); errors.push(...issues.errors); warnings.push(...issues.warnings);
  }
  let manifest = original.has('trainee/course.json') ? JSON.parse(await original.get('trainee/course.json').text()) : null;
  const rootPage = ['COURSE.html', 'START_COURSE.html', 'index.html', 'trainee/index.html'].find(p => texts.has(p));
  const title = texts.get(rootPage)?.match(/<title[^>]*>([^<]+)<\/title>/i)?.[1]?.trim() || '';
  if (!ready) {
    const mapText = texts.get('_course_shell/course_map.js');
    if (mapText) {
      const match = mapText.match(/window\.COURSE_MAP\s*=\s*(\[[\s\S]*\])\s*;?\s*$/);
      if (!match) throw new Error('The course module list cannot be read safely; it is not run as a program.');
      const map = JSON.parse(match[1]);
      for (const m of map) entries.push({ code: m.code, title: m.title, entry: `instructor/${m.code}/${m.entry}`, slides: countSlides(texts.get(`${m.code}/${m.entry}`)) });
    } else {
      for (const f of allowed.filter(f => /^[^/]+\/(?:module\.html|(?:presentation|instructor_screens)\/index\.html)$/i.test(f.path)).sort((a,b) => a.path.localeCompare(b.path, 'en', {numeric:true}))) {
        const code = f.path.split('/')[0];
        if (!entries.some(m => m.code === code)) entries.push({code, title: moduleName(texts.get(f.path)?.match(/<title[^>]*>([^<]+)/i)?.[1]) || code, entry: `instructor/${f.path}`, slides: countSlides(texts.get(f.path))});
      }
    }
    if (!entries.length) throw new Error('No course modules found: choose a folder with COURSE.html or Module_XX presentations.');
  }
  if (!manifest) {
    const count = ready ? new Set(allowed.map(f => f.path.match(/^trainee\/(module_\d+|modules\/m\d+)\//i)?.[1]).filter(Boolean)).size : entries.length;
    manifest = { id: slug(title), title, version: '1.0.0', modules: count, status: 'draft' };
    if (!ready) Object.assign(manifest, { layout: 'author-folder-v1', entry: rootPage ? `instructor/${rootPage}` : entries[0].entry, moduleEntries: entries });
    // Nobody should have to write a description of a course they just imported. If the
    // course says what it is, that is quoted; otherwise it is described by what it is
    // made of. Either way the box is filled in, and the office edits it if it wants to.
    if (!ready && !manifest.description) manifest.description = describeCourse(manifest, texts.get(rootPage));
  }
  const files = [];
  let count = 0;
  for (const f of allowed) {
    if (f.path === 'trainee/course.json') continue;
    const bytes = await f.arrayBuffer(), sha256 = await digest(bytes);
    const record = { path: ready ? f.path : `instructor/${f.path}`, size: bytes.byteLength, sha256, source: f };
    files.push(record);
    // Authoring folders are mixed-audience. Only clearly trainee-facing materials
    // and their common assets are copied; plans, record sheets and exams stay private.
    // `assessment/` carries the module check the class sits at the end of a module. Its answer
    // key and the instructor's record sheet stay private: instructorOnly() names them.
    if (!ready && !instructorOnly(f.path) && (/(^|\/)(tasks|handout|documents|assets|assessment)\//i.test(f.path) || f.path === '_course_shell/course_bridge.js' || f.path === '_course_shell/gb_tokens.css')) files.push({...record, path: `trainee/${f.path}`});
    progress(++count, allowed.length);
  }
  // A module check is copied for the trainees only when everything it needs is in the trainee
  // tree. In some courses that page is really an instructor screen (it pulls in the roster or
  // the case materials); those stay private instead of arriving broken.
  {
    const traineePaths = new Set(files.filter(f => f.path.startsWith('trainee/')).map(f => f.path));
    for (let pass = 0; pass < 4; pass++) {
      let pruned = false;
      for (let i = files.length - 1; i >= 0; i--) {
        const f = files[i];
        if (!f.path.startsWith('trainee/') || !/\/assessment\//i.test(f.path)) continue;
        const text = texts.get(f.source?.path); if (!text) continue;
        const missing = references(f.path, text).filter(r => r.required && !r.path.endsWith('/') && !traineePaths.has(r.path));
        if (!missing.length) continue;
        warnings.push(`The module check stays instructor-only, because it needs ${missing[0].path.split('/').pop()}: ${f.path.slice(8)}`);
        traineePaths.delete(f.path); files.splice(i, 1); pruned = true;
      }
      if (!pruned) break;
    }
  }
  const paths = new Set(files.map(f => f.path));
  for (const f of files) {
    const text = texts.get(f.source.path); if (!text) continue;
    for (const ref of references(f.path, text)) {
      if (paths.has(ref.path) || ref.path.endsWith('/')) continue;
      const msg = `Link outside the package: ${f.path} → ${ref.path}`;
      if (ref.required) errors.push(msg); else warnings.push(msg);
    }
  }
  if (!ready) warnings.unshift('Module checks, marking sheets and Word documents are instructor-only for now. Self-check tasks may contain answer explanations.');
  const bytes = new TextEncoder().encode(JSON.stringify(manifest, null, 2));
  files.push({path: 'trainee/course.json', size: bytes.length, sha256: await digest(bytes), source: new Blob([bytes], {type:'application/json'})});
  errors.push(...validateDescriptor(manifest, files));
  return {manifest, files, errors: [...new Set(errors)], warnings: [...new Set(warnings)], skipped, layout: ready ? 'Prepared tablet package' : 'Author course folder'};
}
