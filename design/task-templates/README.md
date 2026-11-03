# Task templates - the references

The upgraded trainee task screens, kept as the reference the factory's task pages are built and tested against. Each
task blueprint in `plugin/skills/course-module-ui/knowledge/blueprints.json` points at one of them.

| Folder | What it is |
|---|---|
| `live/` | twelve quick-check screens of one self-check, start to end, at the tablet's 1280 x 800: open `live/index.html`, `#s1` ... `#s12`. Sample words, never approved course text |
| `engines/` | the nineteen richer tasks (the simulator's panels, photographs, a crew, a radio, 3D), as they were built: `engines/demo/tasks/*.html`. They read the factory's colour tokens from `plugin/skills/course-module-ui/templates` |
| `themes.py` | writes the nineteen in the brandbook's colours, a Navy and a white theme, as a layer over the originals: `python themes.py <out dir>` |
| `shots/` | each of the nineteen in both themes, with its task on screen: `pd_*.jpg` Navy, `pl_*.jpg` white |

Both themes ship; the factory picks one for each task screen so neighbouring screens do not look the same.

`plugin/skills/course-module-ui/scripts/test_blueprints.py` checks that every reference is here and that both themes
still come out right.
