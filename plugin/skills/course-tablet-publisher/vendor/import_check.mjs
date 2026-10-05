// The classroom admin panel's own import check, run on a course folder on this computer.
//
//     node import_check.mjs <course folder>
//
// package-core.mjs beside this file is a byte-identical copy of the classroom system's
// admin/package-core.mjs (tablet-system-win, commit c7274a0, copied 2026-10-05). It is the exact
// code the admin panel's "+" runs when a course folder is added, so a folder this passes is a
// folder the panel takes. It never runs any of the course's own scripts. Read only.
// Prints one JSON object: { ok, errors, warnings, skipped, layout, manifest, trainee, instructor }.
import fs from 'node:fs/promises';
import path from 'node:path';
import * as core from './package-core.mjs';

const root = path.resolve(process.argv[2] || '.');

async function walk(dir, rel = '') {
  const out = [];
  for (const e of await fs.readdir(dir, { withFileTypes: true })) {
    const r = rel ? `${rel}/${e.name}` : e.name;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(full, r));
    else if (e.isFile()) {
      const st = await fs.stat(full);
      out.push({
        path: r, size: st.size,
        text: async () => fs.readFile(full, 'utf8'),
        arrayBuffer: async () => { const b = await fs.readFile(full); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); },
      });
    }
  }
  return out;
}

try {
  const files = await walk(root);
  const p = await core.prepareCourse(files);
  const m = p.manifest || {};
  console.log(JSON.stringify({
    ok: p.errors.length === 0, errors: p.errors, warnings: p.warnings, skipped: p.skipped, layout: p.layout,
    manifest: { id: m.id, title: m.title, version: m.version, modules: m.modules, description: m.description,
                moduleEntries: (m.moduleEntries || []).map(x => ({ code: x.code, title: x.title, slides: x.slides })) },
    trainee: p.files.filter(f => f.path.startsWith('trainee/')).map(f => f.path),
    instructor: p.files.filter(f => f.path.startsWith('instructor/')).length,
  }));
} catch (err) {
  console.log(JSON.stringify({ ok: false, errors: [String(err && err.message || err)], warnings: [], skipped: [], fatal: true }));
}
