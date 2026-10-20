# Monday hand-off (written 2026-10-16, Friday)

## Where things stand

- Branch `aleksis/script-compiler`, PR silkansraivis3-tech/factory-mjaso#1 open for Raivis.
- Pushed and in the PR description: up to `8017bd6` **2.49.1**, which fixes 31 of the 33 problems the M06 build found.
  All 36 test files pass, and M01–M06 compile with `python -I` on a scratch copy.
- Not fixed, on purpose: per-question Retry (course-task-ux §9a rules it out, so it's Raivis's call), and `two-col` on a
  photo stays `photo split`.
- Still open for Raivis: no hand-off screen after the module check; no `data-active` for `check_balance`.
- The real course still needs `"rows": 2` in `working_claude\figures\M02\s15.kit.json`.

## 3D for M04–M06: Aleksis's choices (2026-10-16)

| Module | Keep → 3D model | Strike → `"declined"` |
|---|---|---|
| M04 | **s10** "A leak - up or down? Predict, then watch" (slide 11): the enclosed space you can turn, the cloud rising or sinking | s06 LPG tank on deck |
| M05 | **s06** "Gas-safe or ESD-protected machinery space" (slide 6): both spaces with the double-walled pipe, detector and gas valve | s05 barrier model (an idea, not a thing) |
| M06 | **s14** "High and low pressure - and liquid trapped between valves" (slide 16): the pipe cut open, the liquid warming, the relief valve lifting | s06 BLEVE tank |

Nothing has been written into the course yet.

## Steps for Monday

1. Write the struck three into each script's `"declined"` (`{"3d": {"s06": "Aleksis 2026-10-16: ..."}}`). This sits
   outside the approved words, so the approval stays.
2. For the kept three: `content_script.py propose` changes `visual_kind` → `model_3d` with a `visual` describing the
   scene. Aleksis confirms, then `apply`, then re-approve the three scripts.
3. Build the three three.js scenes (one per module, like M03's `m03_station3d.js`), list them in each build sheet, and
   pass the speed test: first frame within 1 s, 30 fps with the CPU slowed 4x. **Record the time per scene.**
4. `compile_module.py` M04, M05, M06, then `run_audits.py` and the usual checks.
5. Check improvement: the 3D proposal matched M05 s05 (the barrier model, an idea) on "tanks, valves". Add
   "barrier model" / "layers of protection" to `three_d.flat_words` or similar.
