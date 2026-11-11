#!/usr/bin/env node
/* brief.mjs - the whole-course workflow (build_course.js) for a session that hands out the agents itself: the Auto build and
 * the factory trial (SKILL.md "Auto build"), where the Workflow tool does not run it.
 *
 *   node brief.mjs <args.json>                   the agents to start now - label, model, effort, brief file, answer file -
 *                                                and the ones started before that have not answered yet
 *   node brief.mjs <args.json> --again <label>   that agent ended without its answer: list it to start once more
 *   node brief.mjs <args.json> --none <label>    that agent brought back nothing (run twice, no answer): the workflow goes on
 *
 * args.json holds the workflow's own args: course, factory (the skills folder), modules [{id, title, minutes, theory,
 * practical}] - the approved table - and notes, wave, final as the workflow takes them.
 *
 * Each call runs build_course.js from its start. An agent whose answer is in <course>/working_claude/_build/agents/ gets it
 * back; the first one of a branch without an answer is listed and that branch waits - so the run takes exactly the
 * workflow's path: its order, its models, its one fix round, its re-judging of only what was BROKEN, the walk's two rounds.
 * The brief of each agent is the workflow's own, word for word, in a file beside its answer: the session starts the agent
 * with that file's path and never pastes, writes or rereads a brief (a trial's session read build_course.js twice,
 * ~100 KB, and wrote 43 briefs of its own - its words, not the workflow's, carried in each of its turns). The gate is three
 * commands and is run here, not by an agent. When nothing is left it prints the workflow's answer (result.json).
 */
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
export const WORKFLOW = path.join(HERE, 'build_course.js')

/* a label as a file name: fixfig:1:s03 -> fixfig_1_s03 */
export const fileOf = (label) => String(label).replace(/[^\w.-]+/g, '_')

export const agentsDir = (args) => path.join(args.course, 'working_claude', '_build', 'agents')

const SAID = `
---
YOUR ANSWER GOES IN A FILE. This run hands out its agents from a session, not the Workflow tool, and reads each agent's
answer from a file - not from your last message. When you are done, write`

/* the brief as the agent gets it: the workflow's prompt, then where its answer goes and its shape */
export function briefText(prompt, o, answer) {
  const shape = o.schema
    ? `ONE JSON object matching this schema - nothing else in the file:\n${JSON.stringify(o.schema, null, 1)}`
    : 'the report your brief asks for, its first lines as the brief says.'
  return `${prompt}\n${SAID}\n  ${answer}\nwith the Write tool: ${shape}\nThen end with one line: ANSWERED ${o.label}`
}

/* the gate, run here: the same three commands the workflow's gate agent runs, read the same way */
export function runGate(args) {
  const cf = path.join(args.factory, 'course-factory')
  const py = (...a) => spawnSync('python', a, { encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } })
  const gate = py(path.join(cf, 'scripts', 'course_gate.py'), args.course)
  const approved = args.modules.filter((m) => {
    const s = py(path.join(cf, 'scripts', 'content_script.py'), 'status', args.course, '--module', String(m.id))
    return /approved by/.test(s.stdout || '')
  }).map((m) => String(m.id))
  const ord = py(path.join(cf, 'scripts', 'build_order.py'), args.course, '--modules', args.modules.map((m) => m.id).join(','), '--json')
  let order = []
  try { order = JSON.parse((ord.stdout || '').slice((ord.stdout || '').indexOf('['))) } catch (e) { order = [] }
  return { open: gate.status === 0, output: ((gate.stdout || '') + (gate.stderr || '')).trim(), approved, order, skill_dir: cf }
}

/* -> { pending: [{label, model, effort, brief, answer}], logs, result } - result is set only when the workflow finished */
export async function step(args) {
  const dir = agentsDir(args)
  fs.mkdirSync(dir, { recursive: true })
  const src = fs.readFileSync(WORKFLOW, 'utf8').replace(/^export const meta/m, 'const meta')
  const pending = [], logs = []
  const answerOf = (o) => {
    const base = path.join(dir, fileOf(o.label))
    if (fs.existsSync(base + '.none')) return { found: true, value: null }
    for (const ext of ['.json', '.txt']) {
      if (!fs.existsSync(base + ext)) continue
      const text = fs.readFileSync(base + ext, 'utf8')
      if (!o.schema) return { found: true, value: text }
      try { return { found: true, value: JSON.parse(text.slice(text.indexOf('{'))) } } catch (e) { return { found: false, bad: true } }
    }
    return { found: false }
  }
  const agent = (prompt, o) => {
    const a = answerOf(o)
    if (a.found) return Promise.resolve(a.value)
    if (/^gate:/.test(o.label)) return Promise.resolve(runGate(args))      // run each time: an approval since counts
    const name = fileOf(o.label)
    const answer = path.join(dir, name + (o.schema ? '.json' : '.txt'))
    const brief = path.join(dir, name + '.brief.md')
    const started = path.join(dir, name + '.started')
    const running = fs.existsSync(started) && !a.bad
    if (!running) {
      fs.writeFileSync(brief, briefText(prompt, o, answer))
      fs.writeFileSync(started, new Date().toISOString() + '\n')
    }
    pending.push({ label: o.label, model: o.model || 'the session\'s', effort: o.effort || '-', brief, answer, bad: !!a.bad, running })
    return new Promise(() => {})
  }
  const pipeline = (items, ...stages) => Promise.all(items.map(async (x) => { let r = x; for (const s of stages) r = await s(r); return r }))
  const parallel = (fs_) => Promise.all(fs_.map((f) => f()))
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
  let result, error
  new AsyncFunction('args', 'agent', 'pipeline', 'parallel', 'phase', 'log', src)(args, agent, pipeline, parallel, () => {}, (x) => logs.push(String(x)))
    .then((r) => { result = r }, (e) => { error = e })
  for (let i = 0; i < 200; i++) await new Promise((go) => setImmediate(go))   // every branch runs until it waits on an agent
  if (error) throw error
  return { pending, logs, result }
}

function main(argv) {
  const file = argv[0]
  if (!file || !fs.existsSync(file)) {
    console.log('usage: node brief.mjs <args.json> [--none <label>]')
    return Promise.resolve(2)
  }
  const args = JSON.parse(fs.readFileSync(file, 'utf8'))
  if (!args.course || !args.factory || !(args.modules || []).length) {
    console.log('Stopped - args.json needs course, factory (the skills folder) and modules (the approved table)')
    return Promise.resolve(2)
  }
  fs.mkdirSync(agentsDir(args), { recursive: true })
  const none = argv.indexOf('--none')
  if (none >= 0) fs.writeFileSync(path.join(agentsDir(args), fileOf(argv[none + 1]) + '.none'), 'brought back nothing\n')
  const again = argv.indexOf('--again')
  if (again >= 0) fs.rmSync(path.join(agentsDir(args), fileOf(argv[again + 1]) + '.started'), { force: true })
  return step(args).then(({ pending, logs, result }) => {
    for (const x of logs) console.log('workflow: ' + x)
    if (result !== undefined) {
      const out = path.join(agentsDir(args), 'result.json')
      fs.writeFileSync(out, JSON.stringify(result, null, 1))
      const r = result || {}
      console.log(`DONE - the workflow's answer: ${out}`)
      if (r.stopped_at) console.log(`stopped at the ${r.stopped_at}: ${r.why || ''}${r.gate ? '\n' + r.gate : ''}`)
      if (r.blocking) console.log(`blocking: ${r.blocking.length ? r.blocking.join(', ') : 'none'}; walk not passed: ${
        ((r.walk || {}).not_passed || []).map((w) => w.module).join(', ') || 'none'}`)
      return 0
    }
    const start = pending.filter((p) => !p.running), wait = pending.filter((p) => p.running)
    console.log(`START ${start.length} agent(s) now, side by side - each with "Read <its brief>: it is your whole brief." as its prompt:`)
    for (const p of start) {
      console.log(`  ${p.label}  model ${p.model}, effort ${p.effort}${p.bad ? '  (its answer file is not JSON - run it again)' : ''}`)
      console.log(`      brief  ${p.brief}\n      answer ${p.answer}`)
    }
    if (wait.length) console.log(`RUNNING, no answer yet: ${wait.map((p) => p.label).join(', ')}`)
    console.log('Run this again when an agent ends. One that ended without its answer file: --again <label>, and start it '
      + 'once more; a second time without: --none <label>.')
    return 0
  })
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then((code) => process.exit(code), (e) => { console.log(`Stopped - ${e && e.stack || e}`); process.exit(1) })
}
