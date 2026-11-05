// Import a course the factory built into the staging training app as a DRAFT release - the same upload the admin
// panel's Import page does, with the factory key instead of a Google session. Staging only.
//
//   node course_import.mjs <course folder with COURSE.html> <course id>
//
// The rules a package must pass are the training app's own: its package-core.mjs is fetched from the staging site
// and run here, so the factory never keeps a second copy of them. The course id the package gets from COURSE.html's
// title must be the course in preparation's id (course_portal.py create), or nothing is sent.
// Prints one line of JSON at the end: {"ok":true,"release":{...}} or {"ok":false,"error":"..."}.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';

const STAGING = 'https://mgkhdbkxfaldfxyvfqrl.supabase.co';
const SITE = 'https://novikontas-staging.vercel.app';
const ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1na2hkYmt4ZmFsZGZ4eXZmcXJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE3ODAyNDgsImV4cCI6MjEwNzM1NjI0OH0.IqohHiLweNG19tDhHxSslhcp__oCgEiTmLJ0BXJEiow';
const done = (x) => { console.log(JSON.stringify(x)); process.exit(x.ok ? 0 : 2); };

async function factoryKey() {
  if (process.env.NOVIKONTAS_FACTORY_KEY) return process.env.NOVIKONTAS_FACTORY_KEY.trim();
  const base = process.env.APPDATA || path.join(os.homedir(), '.config');
  try { return (await fs.readFile(path.join(base, 'novikontas', 'factory.key'), 'utf8')).trim(); } catch { return ''; }
}
async function walk(root, dir = '') {
  const out = [];
  for (const e of await fs.readdir(path.join(root, dir), { withFileTypes: true })) {
    const rel = dir ? dir + '/' + e.name : e.name;
    if (e.isDirectory()) out.push(...await walk(root, rel));
    else if (e.isFile()) {
      const full = path.join(root, rel), size = (await fs.stat(full)).size;
      out.push({ path: rel, size, text: () => fs.readFile(full, 'utf8'), arrayBuffer: async () => { const b = await fs.readFile(full); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); } });
    }
  }
  return out;
}

const [folder, courseId] = process.argv.slice(2);
if (!folder || !courseId) done({ ok: false, error: 'usage: node course_import.mjs <course folder> <course id>' });
const key = await factoryKey();
if (!key) done({ ok: false, error: 'There is no factory key on this PC (%APPDATA%\\novikontas\\factory.key).' });

// the training app's own package rules
const res = await fetch(SITE + '/package-core.mjs');
if (!res.ok) done({ ok: false, error: 'The staging site did not give its package rules (HTTP ' + res.status + ').' });
const tmp = path.join(os.tmpdir(), 'novikontas-package-core-' + process.pid + '.mjs');
await fs.writeFile(tmp, await res.text());
const core = await import(pathToFileURL(tmp).href);
await fs.rm(tmp, { force: true });

const call = async (body) => {
  for (let n = 0; ; n++) {
    let r;
    try {
      r = await fetch(STAGING + '/functions/v1/course-import', { method: 'POST', body: JSON.stringify(body),
        headers: { 'Content-Type': 'application/json', apikey: ANON, Authorization: 'Bearer ' + ANON, 'x-factory-key': key } });
    } catch (e) { if (n < 4) { await new Promise(t => setTimeout(t, 1500 * (n + 1))); continue; } throw e; }
    const data = await r.json().catch(() => null);
    if (r.ok) return data;
    const why = (data?.error || (data?.errors || []).join('; ') || 'HTTP ' + r.status);
    if ((r.status >= 500 || r.status === 429) && n < 4) { await new Promise(t => setTimeout(t, 1500 * (n + 1))); continue; }
    throw new Error(why);
  }
};
const b64 = (buf) => Buffer.from(buf).toString('base64');

try {
  const prepared = await core.prepareCourse(await walk(path.resolve(folder)));
  const m = prepared.manifest;
  if (m.id !== courseId) done({ ok: false, error: `COURSE.html's title makes the course "${m.id}", but the course in preparation is "${courseId}". Give COURSE.html the course's name.` });
  const bytes = new TextEncoder().encode(JSON.stringify(m, null, 2));
  const mf = prepared.files.find(f => f.path === 'trainee/course.json');
  if (mf) Object.assign(mf, { size: bytes.length, sha256: await core.digest(bytes), source: new Blob([bytes]) });
  const errors = [...new Set([...prepared.errors, ...core.validateDescriptor(m, prepared.files)])];
  if (errors.length) done({ ok: false, error: 'The course did not pass the import checks: ' + errors.slice(0, 10).join(' | ') });
  const files = prepared.files.map(({ path: p, size, sha256 }) => ({ path: p, size, sha256 }));
  // the factory's own notes first: a draft that still has picture spaces to fill says so (course_portal.py upload)
  const notes = JSON.parse(process.env.NOVIKONTAS_IMPORT_NOTES || '[]');
  const job = await call({ action: 'begin', manifest: m, files, warnings: [...notes, ...prepared.warnings].slice(0, 300) });
  const chunks = core.batches(prepared.files);
  for (let index = 0; index < chunks.length; index++) {
    if (chunks[index].length === 1 && chunks[index][0].size > core.LIMITS.part) {
      const f = chunks[index][0], buf = await f.source.arrayBuffer(), parts = Math.ceil(f.size / core.LIMITS.part);
      for (let part = 0; part < parts; part++)
        await call({ action: 'part', id: job.id, index, path: f.path, part, parts, base64: b64(buf.slice(part * core.LIMITS.part, (part + 1) * core.LIMITS.part)) });
    } else {
      const sent = await Promise.all(chunks[index].map(async f => ({ path: f.path, base64: b64(await f.source.arrayBuffer()) })));
      await call({ action: 'batch', id: job.id, index, files: sent });
    }
    process.stderr.write(`uploaded ${index + 1}/${chunks.length}\n`);
  }
  const result = await call({ action: 'finish', id: job.id });
  done({ ok: true, release: result.release, modules: m.modules, warnings: prepared.warnings.length });
} catch (e) {
  done({ ok: false, error: String(e?.message || e) });
}
