/*
 * browser_slots.mjs - the Node side of the ONE computer-wide pool of hidden browsers (2.57.0).
 *
 *     import { takeSlot } from './browser_slots.mjs';
 *     const release = await takeSlot();      // waits for a free slot; freed by release() or when the process exits
 *
 * The same lock files and rules as course-factory/scripts/browser_slots.py (read its header): %TEMP%\cf_browser_slots\
 * slot_N.lock made with exclusive create, holding the PID; touched every 20 s while held; reclaimed when its PID is not
 * running or it was not touched for 5 minutes. CF_BROWSER_SLOTS sets how many (default a quarter of the cores, 2-8),
 * CF_BROWSER_SLOT_DIR the folder.
 */
import { closeSync, mkdirSync, openSync, readFileSync, statSync, unlinkSync, utimesSync, writeSync } from 'node:fs';
import { availableParallelism, cpus, tmpdir } from 'node:os';
import { join } from 'node:path';

const HEARTBEAT = 20000, STALE = 300000;

export function slotCount() {
  const want = parseInt(process.env.CF_BROWSER_SLOTS || '0', 10) || 0;
  const cores = typeof availableParallelism === 'function' ? availableParallelism() : cpus().length;
  // 2.62.1: a quarter of the cores, at least 2, at most 8 - the same rule as browser_slots.py count() (measured there)
  return Math.max(1, want || Math.min(8, Math.max(2, Math.floor((cores || 2) / 4))));
}

export function slotFolder() {
  const d = process.env.CF_BROWSER_SLOT_DIR || join(tmpdir(), 'cf_browser_slots');
  mkdirSync(d, { recursive: true });
  return d;
}

function alive(pid) {
  if (!(pid > 0)) return false;
  if (pid === process.pid) return true;
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

function stale(path) {
  let st;
  try { st = statSync(path); } catch { return false; }
  const age = Date.now() - st.mtimeMs;
  let pid = 0;
  try { pid = parseInt(readFileSync(path, 'ascii').trim().split(/\s+/)[0], 10) || 0; } catch {}
  return age > STALE || (age > 2000 && !alive(pid));
}

function reclaim(d, path) {
  const guard = join(d, 'reclaim.lock');
  try { if (Date.now() - statSync(guard).mtimeMs > 30000) unlinkSync(guard); } catch {}
  try { closeSync(openSync(guard, 'wx')); } catch { return; }
  try { if (stale(path)) unlinkSync(path); } catch {}
  finally { try { unlinkSync(guard); } catch {} }
}

function take(d, n) {
  const start = Math.floor(Math.random() * n);
  for (let k = 0; k < n; k++) {
    const path = join(d, `slot_${(start + k) % n}.lock`);
    let fd;
    try { fd = openSync(path, 'wx'); } catch (e) {
      if (e.code === 'EEXIST' && stale(path)) reclaim(d, path);
      continue;
    }
    try { writeSync(fd, `${process.pid}\n`); } finally { closeSync(fd); }
    return path;
  }
  return null;
}

/** waits for a slot of the computer's pool; returns release() - also run when the process exits */
export async function takeSlot(waitNote) {
  const d = slotFolder(), n = slotCount(), t0 = Date.now();
  let path = take(d, n), pause = 50, said = false;
  while (!path) {
    await new Promise(r => setTimeout(r, pause + Math.random() * pause));
    pause = Math.min(500, pause * 1.5);
    if (waitNote && !said && Date.now() - t0 > 10000) { said = true; waitNote((Date.now() - t0) / 1000); }
    path = take(d, n);
  }
  const beat = setInterval(() => { try { const t = new Date(); utimesSync(path, t, t); } catch {} }, HEARTBEAT);
  beat.unref();
  let done = false;
  const release = () => {
    if (done) return; done = true;
    clearInterval(beat);
    try { unlinkSync(path); } catch {}
  };
  process.on('exit', release);
  return release;
}
