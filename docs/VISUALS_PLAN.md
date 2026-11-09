# Visuals plan

Agreed with the owner on 2026-11-06. Short on purpose: what a slide picture may be, and the build order.

## What a slide picture may be

1. **Interactive 3D - 60-80 % of the teaching slides (L67).** Equipment from the 3D kit (`kit3d`). Ideas from new
   **3D concept scenes**: blocks, stacks, rings, scales, a pyramid, a triangle, a timeline track, people figures -
   turned and tapped like any scene, changed on Next.
2. **The other 20-40 %:** a static 3D render, a photograph, an AI picture, or a 2D-kit figure. Which picture a slide
   gets is the picture rule (`course-visuals` SKILL.md, L67).
3. **2D-kit figure** - for pipe and valve systems, flows, processes, charts and ideas, and universal: trade-off triangle, cycle, matrix, pyramid,
   timeline, compare, flow, cause and effect, hierarchy, bars. One hero shape that fills the box, depth from
   gradient, light and one shadow, thick strokes, words beside the shape never on it, and the shape itself changes
   on Next.
4. **The figure kit's flat line drawing is a hard stop on a slide.** A figure made of panels, readout tiles and
   dashed signal wires to show an idea is never shipped. Open point: a real control screen (HMI), where reading the
   screen is what is taught.

## Category colours

A small set of 4-5 calm colours beside the course blues, for the categories of a concept figure (scope, time, cost
and the like). Shown to the owner as swatches before any figure uses them.

## Build order

- **A. A new 2D kit** (`course-visuals/kit2d/`, 2.113.0), not a layer on the old figure kit (owner: "i dont like how 2d
  kit was before"). Built from the owner's reference: graphs, objects in motion, concepts; smooth motion; an overlap
  check the fit gate runs on every step; wired into the compiler. Next: more parts (bars, pyramid, balance, events,
  people, more objects), a light-page review, gallery cards and its own test file.
- **B. 3D concept scenes** in `kit3d`: the same concepts as 3D objects.
- **C. A universal kit:** the gas and IGF defaults, colours and meaning rules move into a gas pack; the core knows no
  course.
- **D. The gate:** a flat kit drawing on a slide stops the build, and the message names what to use instead. Turned
  on once A exists.
- **E. With the overflow work:** each picture kind says the box it needs, so the layout chooser can grow the box or
  swap the kind.
