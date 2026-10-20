# Atvēršana un darbs Windows datorā

1. Izvelc ZIP ar **Extract All / Izvilkt visu**. Neatver HTML tieši ZIP skatā.
2. Galerija: `design\course-layout-templates\preview.html`. Atver Chrome vai Edge. Visi attēli un fonts ir iekļauti blakusmapēs.
3. Ja faila atvēršanu ierobežo pārlūks, no izvilktās mapes palaid `py -m http.server 8765 --bind 127.0.0.1` un atver `http://127.0.0.1:8765/design/course-layout-templates/preview.html`.
4. Iedod Claude komplekta mapi un `CLAUDE_PROMPT_LV.txt` saturu. Pievieno savas papildu instrukcijas zem attiecīgās rindas.

Ja `factory-mjaso` jau ir noklonēts Windows datorā, izmanto šo izmaiņu zaru vai PR. Ja strādā no ZIP, pievieno tikai komplekta `design` un `docs` failus savam repo. ZIP nesatur tava repo pilnu kopiju vai vecu `_claude/CONTEXT.md`, ko pārrakstīt pāri jaunākai versijai.

Ja izmanto atsevišķo pārnesamo ZIP, tā saknē ir `CLAUDE_PROMPT.txt` — tā ir šī paša prompta ērti pieejama kopija. Pati ieviešana kompilatorā vēl nav veikta.

Pārbaude no izvilktās mapes vai repozitorija saknes:

```powershell
py design/course-layout-templates/validate_preview.py
```

Priekšskatījuma atjaunošana pēc avotu izmaiņām:

```powershell
py design/course-layout-templates/template-preview/build_preview.py
```

Python vajadzīgs tikai ģenerēšanai, pārbaudei vai lokālā servera variantam. Pašiem HTML priekšskatījumiem nav npm, instalācijas vai ārēju CDN atkarību.
