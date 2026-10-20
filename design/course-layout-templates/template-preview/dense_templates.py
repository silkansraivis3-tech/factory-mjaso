"""Content-heavy layout specimens. Sample teaching copy, not an approved course."""

extra = '<p class="dense-addition">Additional context can explain an unfamiliar term, describe another example or connect this topic to an earlier lesson. Keep the wording visible at the same reading size when checking whether the chosen layout still has enough space.</p>'

simple_tank = '''<svg viewBox="0 0 600 300" role="img" aria-label="Simplified illustrative vessel with liquid and vapour regions"><defs><clipPath id="reading-tank"><rect x="42" y="62" width="516" height="192" rx="65"/></clipPath></defs><path d="M160 255v20m280-20v20M135 278h50m230 0h50" stroke="#6f93af" stroke-width="8" fill="none"/><rect x="38" y="58" width="524" height="200" rx="69" fill="#163c56" stroke="#98b6ca" stroke-width="3"/><g clip-path="url(#reading-tank)"><path d="M40 170Q80 155 120 170T200 170T280 170T360 170T440 170T520 170T600 170V260H40Z" fill="#2985ac"/></g><path d="M310 58V26h94" fill="none" stroke="#98b6ca" stroke-width="6"/><circle cx="404" cy="26" r="13" fill="#163c56" stroke="#98b6ca" stroke-width="2"/><circle cx="64" cy="104" r="7" fill="#e9ab39"/><circle cx="535" cy="171" r="7" fill="#e9ab39"/><circle cx="480" cy="100" r="7" fill="#e9ab39"/></svg>'''

def visual_rail(kind='model', note='Keep the visual in view while reading the explanation.'):
    if kind == 'model':
        media = '<canvas class="rotation-model" width="520" height="420" role="img" aria-label="Rotatable illustrative three-dimensional tank model. Use the rotation buttons or drag the model."></canvas><div class="rotation-controls"><button type="button" data-rotate="-1" data-control-id="model-rotate-left" aria-label="Rotate model left">↶</button><span>Drag to rotate</span><button type="button" data-rotate="1" data-control-id="model-rotate-right" aria-label="Rotate model right">↷</button></div>'
        label = 'ROTATABLE 3D VIEW'
    else:
        media = '<div class="animated-figure" data-playing="false">'+simple_tank+'<span class="flow-dot"></span></div><button type="button" class="animation-toggle" data-animation-toggle data-control-id="visual-animation-toggle" aria-pressed="false">Play animation</button>'
        label = 'ANIMATED DIAGRAM'
    return '<aside class="visual-rail" data-slot="visual" data-visual-kind="'+kind+'" data-fit-region><p class="visual-label">'+label+'</p>'+media+'<p class="visual-rail-note">'+note+'</p><span class="visual-disclaimer">ILLUSTRATIVE MODEL</span></aside>'

chunks = [
    ('Overview', 'Start with the complete picture.', [
      'Start with the overall shape, the main elements and the direction in which the drawing should be read. This overview gives the details a clear context before you focus on individual labels.',
      'Describe which elements belong together and which appear separately. Use the photograph for real-world context and the diagram to follow the relationship. Connect the two views through the elements they share.'
    ], 'Focus on the relationship', 'Connect each detail to the complete view.',
    'Which elements can you identify before reading any of the labels?'),
    ('Detail', 'Connect each label to its element.', [
      'Follow each label to the element it names. Check the endpoint of the leader line: it may identify an opening, a boundary or a region within the drawing rather than the whole object.',
      'Name the selected element and explain how it relates to its neighbours. When the photograph uses a different viewpoint, describe that connection in words instead of relying on the element’s screen position.'
    ], 'Use precise language', 'Use the element’s name and follow its label.',
    'What makes your selected element distinguishable from its neighbours?'),
    ('Explanation', 'Build an explanation that can be checked.', [
      'Connect an observation to a reason. Identify the relationship shown and explain why it matters in this example. Keep visible features separate from assumptions that would need another source to support them.',
      'Return to the illustration and check your account. Every element mentioned should be identifiable, and each label should be used consistently. If the image cannot support a conclusion, state what information is missing.'
    ], 'Connect, then review', 'Check the explanation against the same visual.',
    'Which part of your explanation can another person verify directly from the illustration?')
]

chunk_html = []
for index, (label, title, paragraphs, note_title, note, question) in enumerate(chunks, 1):
    chunk_html.append(f'''<section class="chunk-page" id="chunk-panel-{index}" role="tabpanel" aria-labelledby="chunk-tab-{index}" data-chunk-page="{index}" {'hidden' if index != 1 else ''}>
      <article class="chunk-copy" data-fit-region><p class="section-index">PART {index:02} / 03</p><h2>{title}</h2>{''.join('<p>'+p+'</p>' for p in paragraphs)}{extra}</article>
      {visual_rail('model', note)}
    </section>''')

DENSE_TEMPLATES = [
  dict(id='long-explanation', name='Garš skaidrojums', en='A complete explanation', desc='Pilnas rindkopas divās kolonnās. Piemērots izvērstam skaidrojumam vienā skatā.', kind='dense dense-editorial', dark=False, slots=['title','leftText','rightText','takeaway'], body='''
    <header class="dense-heading"><p class="eyebrow">09 / READ THE COMPLETE EXPLANATION</p><h1 data-slot="title">Give the explanation room to breathe.</h1></header>
    <div class="reading-columns">
      <article data-slot="leftText" data-fit-region><span class="section-index">01 / ESTABLISH THE CONTEXT</span><h2>Start with what is visible.</h2><p>A technical drawing brings selected features into focus. Start with the overall shape and identify the main elements before reading individual labels. Use the illustration as a reference while following the explanation: each name should connect to something you can locate in the picture.</p><p data-optional>Read the text and picture together. Connect an unfamiliar term to a visible feature before moving on.</p>'''+extra+'''</article>
      <article data-slot="rightText" data-fit-region><span class="section-index">02 / DEVELOP THE EXPLANATION</span><h2>Connect the parts to the whole.</h2><p>Explain how the elements relate, using the same names throughout. Follow a deliberate order so the reader can move between the text and the visual without guessing which part is being discussed. Finish by checking the explanation against the complete picture.</p><p data-optional>Return to the complete picture and identify any detail that still needs a separate explanation.</p>'''+extra+'''</article>
    </div><div class="reading-takeaway" data-slot="takeaway"><span>KEY IDEA</span><p>Use enough words to explain the relationship. Give those words a clear structure.</p></div>'''),
  dict(id='three-content-blocks', name='Trīs satura bloki', en='Three connected explanations', desc='Trīs izvērsti temati ar apakšvirsrakstiem un rindkopām, ne tikai īsi lozungi.', kind='dense dense-blocks', dark=True, slots=['title','blocks'], body='''
    <header class="dense-heading"><p class="eyebrow">10 / ORGANISE THE INFORMATION</p><h1 data-slot="title">Three parts of a complete explanation.</h1></header><div class="text-block-grid" data-slot="blocks">
      <article class="text-block" data-fit-region><span class="block-number">01</span><h2>Describe the context.</h2><p>Begin by telling the reader what the example shows and which question the explanation addresses. Introduce the main elements before adding detail. This prevents the reader from collecting isolated facts without knowing how those facts belong together.</p><p data-optional>A useful description identifies the view, names the important parts and establishes the order in which the information should be read. It gives the following explanation a shared frame of reference.</p>'''+extra+'''</article>
      <article class="text-block" data-fit-region><span class="block-number">02</span><h2>Explain the relationship.</h2><p>Connect each new point to something already introduced. Explain how the elements relate rather than simply repeating their names. Where several factors belong to the same idea, keep them together under a meaningful subheading and use complete sentences to make the connection clear.</p><p data-optional>Keep terminology consistent. A change of wording should add meaning, rather than make the reader wonder whether a different element has been introduced.</p>'''+extra+'''</article>
      <article class="text-block" data-fit-region><span class="block-number">03</span><h2>Make it reviewable.</h2><p>End with an explanation that another person can check against the example. Identify the observations that support the account and distinguish them from points that need further information. This makes the reasoning visible instead of presenting a conclusion without its supporting context.</p><p data-optional>A short recap can then bring the main relationship back into focus. The recap supports the full explanation; it does not replace the detail needed to understand it.</p>'''+extra+'''</article>
    </div>'''),
  dict(id='reference-table', name='Tabula + secinājums', en='A structured reference', desc='Vairāk informācijas salīdzināmā tabulā. Teksts saglabājas pilnos teikumos.', kind='dense dense-reference', dark=False, slots=['title','table','takeaway'], body='''
    <header class="dense-heading"><p class="eyebrow">11 / KEEP THE DETAILS COMPARABLE</p><h1 data-slot="title">Different sources. Different information.</h1></header>
    <table class="reference-table" data-slot="table" data-fit-region><thead><tr><th scope="col">Source</th><th scope="col">What it helps you understand</th><th scope="col">What to check when using it</th></tr></thead><tbody>
    <tr><th scope="row"><span>01</span>Technical diagram</th><td>A simplified arrangement makes selected elements and their relationships easier to see. Labels connect the explanation to a specific feature.</td><td>Read the title, follow each leader line and confirm which details are included in this particular view.</td></tr>
    <tr><th scope="row"><span>02</span>Photograph</th><td>A realistic view adds visual context and helps connect the diagram to equipment that a learner may recognise.</td><td>Identify the viewpoint and distinguish the main object from nearby equipment or features in the background.</td></tr>
    <tr><th scope="row"><span>03</span>Written explanation</th><td>Connected sentences develop the meaning of the illustration, define unfamiliar terms and explain why the selected relationship matters.</td><td>Check that the terminology stays consistent and that each statement can be connected to the example or its source.</td></tr>
    <tr><th scope="row"><span>04</span>Worked example</th><td>A complete example brings the observations and explanation together, showing the reasoning that connects the starting information to a conclusion.</td><td>Follow the reasoning in order and identify any assumptions or additional information required to support the account.</td></tr>
    </tbody></table><div class="reading-takeaway" data-slot="takeaway"><span>READ ACROSS</span><p>Compare the same questions for every source: what it shows, what it explains and what still needs checking.</p></div>'''),
  dict(id='reading-with-figure', name='Daudz teksta + figūra', en='A longer explanation with a visual anchor', desc='Īss skaidrojums un līdzvērtīgi liela figūra. Sadalījums 55% / 45%.', kind='dense dense-reading-visual', dark=False, slots=['title','bodyText','figure','figureLegend'], body='''
    <header class="dense-heading"><p class="eyebrow">12 / KEEP THE VISUAL IN VIEW</p><h1 data-slot="title">Read the explanation. Keep the connection.</h1></header><div class="reading-visual-grid">
    <article class="long-reading" data-slot="bodyText" data-fit-region><p>Keep the diagram in view while reading. It provides a visual anchor for the explanation, so the reader can locate each element without remembering an image from an earlier screen.</p><p>Introduce the main elements before describing their relationships. Use the same names in the text and legend. Refer to the element itself rather than its position on the screen, especially when the photograph shows a different view.</p><p data-optional>Bring the individual points back together. Check that the explanation still matches the complete picture.</p>'''+extra+'''</article>
    <aside class="reading-figure" data-fit-region><div data-slot="figure">'''+simple_tank+'''</div><p class="mini-caption">ILLUSTRATIVE DIAGRAM / VISUAL ANCHOR</p><ol data-slot="figureLegend"><li><b>Containment</b><span>The boundary of the simplified vessel.</span></li><li><b>Liquid region</b><span>The shaded region in the diagram.</span></li><li><b>Vapour space</b><span>The upper region of the view.</span></li></ol></aside>
    </div>'''),
  dict(id='content-in-parts', name='Viens slaids, vairākas daļas', en='One topic in several readable parts', desc='Garš skaidrojums vienā slaidā ar trim pārslēdzamām daļām. Visas rindkopas saglabātas.', kind='dense dense-paged', dark=False, slots=['title','parts','partNavigation'], body='''
    <header class="dense-heading"><p class="eyebrow">13 / ONE TOPIC, THREE READABLE PARTS</p><h1 data-slot="title">Read the system in context.</h1></header>
    <div class="chunk-tabs" role="tablist" aria-label="Explanation parts">'''+''.join(f'<button type="button" role="tab" id="chunk-tab-{i}" aria-controls="chunk-panel-{i}" aria-selected="{str(i==1).lower()}" data-chunk="{i}" data-control-id="explanation-part-{i}"><span>{i:02}</span>{row[0]}</button>' for i,row in enumerate(chunks,1))+'''</div>
    <div class="chunk-pages" data-slot="parts">'''+''.join(chunk_html)+'''</div>
    <nav class="chunk-navigation" data-slot="partNavigation" aria-label="Move through explanation"><span data-chunk-counter aria-live="polite">Part 1 of 3 / Overview</span><div><button type="button" data-chunk-back data-control-id="explanation-back" disabled>← Previous part</button><button type="button" data-chunk-next data-control-id="explanation-next">Next part →</button></div></nav>''')
]

# Dense material always keeps a meaningful visual beside the reading area.
# This preview's teaching copy may be edited; approved course text must retain
# the factory's source-approval workflow when pagination is integrated.
for item in DENSE_TEMPLATES:
    if item['id'] == 'long-explanation':
        item['body'] = '''<header class="dense-heading"><p class="eyebrow">09 / A COMPLETE EXPLANATION, WITH VISUAL CONTEXT</p><h1 data-slot="title">Give the explanation room to breathe.</h1></header>
        <div class="dense-with-rail"><article class="dense-prose" data-fit-region>
        <div data-slot="leftText"><p>A technical drawing brings selected features into focus. Start with the overall shape and identify the main elements before reading individual labels. Use the illustration as a reference while following the explanation: each name should connect to something you can locate in the picture.</p><p data-optional>Read the text and picture together. Connect an unfamiliar term to a visible feature before moving on.</p></div>
        <div data-slot="rightText"><p>Explain how the elements relate, using the same names throughout. Follow a deliberate order so the reader can move between the text and the visual without guessing which part is being discussed. Finish by checking the explanation against the complete picture.</p><p data-optional>Return to the complete picture and identify any detail that still needs a separate explanation.</p></div>'''+extra+'''</article>'''+visual_rail()+'''</div><div class="reading-takeaway" data-slot="takeaway"><span>KEY IDEA</span><p>Explain the relationship in full sentences. Keep the visual available as a point of reference.</p></div>'''
        item['desc'] = 'Divas īsas rindkopas un liels grozāms 3D modelis. Sadalījums 55% / 45%.'
        item['slots'].append('visual')
    elif item['id'] == 'three-content-blocks':
        item['body'] = '''<header class="dense-heading"><p class="eyebrow">10 / THREE CONNECTED IDEAS, ONE VISUAL</p><h1 data-slot="title">Three parts of a complete explanation.</h1></header><div class="dense-with-rail"><div class="dense-topics" data-slot="blocks">
        <article class="dense-topic" data-fit-region><div><span class="block-number">01</span><h2>Describe the context.</h2></div><p>Introduce the example and its main elements. Give the reader a clear starting point before adding detail.</p></article>
        <article class="dense-topic" data-fit-region><div><span class="block-number">02</span><h2>Explain the relationship.</h2></div><p>Explain how the elements connect. Use consistent names so the reader can follow the same part in the visual.</p></article>
        <article class="dense-topic" data-fit-region><div><span class="block-number">03</span><h2>Make it reviewable.</h2></div><p>Connect the explanation to visible observations. Finish by checking the relationship against the complete picture.</p></article>'''+extra+'''</div>'''+visual_rail('animation')+'''</div>'''
        item['desc'] = 'Trīs izvērsti skaidrojuma bloki; blakus paliek darbināma animācija.'
        item['slots'].append('visual')
    elif item['id'] == 'reference-table':
        start = item['body'].index('<table ')
        end = item['body'].index('</table>') + len('</table>')
        rail = visual_rail('animation', 'Use each source for the information it shows most clearly.').replace('<p class="visual-rail-note">', '<p class="visual-rail-note" data-slot="takeaway">')
        table = '''<table class="reference-table" data-slot="table" data-fit-region><thead><tr><th scope="col">Source</th><th scope="col">What it adds</th></tr></thead><tbody>
        <tr><th scope="row"><span>01</span>Diagram</th><td>A simplified view makes selected elements and their relationships easier to follow.</td></tr>
        <tr><th scope="row"><span>02</span>Photograph</th><td>A realistic view adds context and helps the learner recognise the equipment.</td></tr>
        <tr><th scope="row"><span>03</span>Explanation</th><td>Connected sentences explain why the elements matter and define unfamiliar terms.</td></tr>
        <tr><th scope="row"><span>04</span>Example</th><td>A worked example connects the observations to a conclusion through clear reasoning.</td></tr>
        </tbody></table>'''
        item['body'] = item['body'][:start]+'<div class="dense-with-rail table-with-rail"><div class="table-region" data-fit-region>'+table+'</div>'+rail+'</div>'
        item['desc'] = 'Īsāka tabula un liela animēta figūra. Sadalījums 55% / 45%.'
        item['slots'].append('visual')
    elif item['id'] == 'content-in-parts':
        item['desc'] = 'Īsāks teksts trīs pārslēdzamās daļās. Aptuveni 55% tekstam un 45% 3D vizuālim.'
        item['slots'].append('visual')
