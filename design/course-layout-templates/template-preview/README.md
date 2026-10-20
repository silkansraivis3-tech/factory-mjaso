# Šablonu dizaina priekšskatījums

Atver `../preview.html` ar dubultklikšķi vai pārlūkā. Serveris un internets nav vajadzīgi. Visus 13 šablonus var atvērt arī atsevišķi: `templates/<id>/template.html`.

Papildinājums 09–13: garš skaidrojums ar grozāmu 3D modeli, trīs satura bloki ar animāciju, tabula ar animāciju, daudz teksta ar figūru un garš skaidrojums vairākās pārslēdzamās daļās ar 3D modeli. Aktuālais sadalījums jaunajos variantos ir 55% tekstam un 45% vizuālim (atļautais diapazons 50–60% / 40–50%). Parauga teksts saīsināts līdz aptuveni 85–135 vārdiem vienā skatā; pārslēdzamajā variantā pašlaik ir 281 vārds trīs daļās. Garāku materiālu sadala pa daļām, saglabājot lielo vizuāli un lasāmu fontu. Vārdu skaitītājs rāda pašreizējā skata apjomu; pārslēdzamajā variantā arī visu daļu kopējo apjomu. Garāka satura režīms apzināti var atklāt pārpildījumu — teksts netiek automātiski samazināts vai apgriezts.

Lietotāja noteikumi ir saglabāti `course-layout-rules.json` un katra šablona JSON: ne vairāk kā divi slaidi pēc kārtas bez vizuāļa; blīvam saturam obligāti blakus attēls, diagramma, animācija, interaktīvs elements vai 3D modelis. Visi pieci jaunie blīvā satura šabloni to demonstrē. Galerija ir katalogs, nevis kursa slaidu secība. Reālas kursa secības validācija Factory kompilatorā vēl nav integrēta.

3D priekšskatījums ir lokāli ģenerēts cilindrisks modelis ar telpisku projekciju un grozīšanu ar pogām vai vilkšanu. Animācija tiek sākta un apturēta ar pogu. Šie ir funkcionējoši dizaina paraugi; tajos vēl nav classroom tālvadības sinhronizācijas.

Galvenā galerija ļauj izvēlēties izkārtojumu, simulēt ekrāna malu attiecību, mainīt parauga teksta apjomu, atzīmēt vērtējumu un saglabāt atsauksmes JSON failā. Atsevišķos šablonos darbojas figūras soļu pogas, secības soļi un demonstrācijas darbības poga. Galerijas piezīmes glabājas tikai lokāli pārlūkā, ja tas atļauj localStorage.

Slaida loģiskais izmērs vienmēr ir 1280×800. Ekrāna izvēle maina ārējo displeja vietu, bet slaids mērogojas proporcionāli un nepārkārtojas. Portretā apzināti redzamas lielas malas; tas demonstrē vienotu projektora skatu, nevis atsevišķu portreta mācību lapas dizainu. Mazi galerijas priekšskatījumi ir samazināti slaidi; lasāmību paredzētajā ekrānā novērtē pilnekrānā.

Šis ir jauns dizaina virziens pēc esošās Factory krāsu paletes, nevis precīza pašreizējā dizaina kopija. Ir iekļauts Raleway mainīgais fonts no Google Fonts repozitorija ar OFL licenci (`assets/FONT-LICENSE.txt`). Visi aktīvi tiek ielādēti lokāli.

Kuģa attēls ir ģenerēts ar iebūvēto `imagegen` rīku, paredzēts dizaina priekšskatījumam. Diagramma ir vienkāršota un nav tehniski validēts mācību materiāls. Parauga teksts angliski nav apstiprināts kursa saturs. Galerijas vadība latviski.

Katram šablonam ir atsevišķs HTML un piedāvāts `template.json` līgums. HTML satur reālo struktūru ar `data-slot` atzīmēm; kopīgais CSS un priekšskatījuma uzvedība ir `assets/`. JSON failu izpilde un slotu aizpildīšana no kursa avotiem vēl nav pieslēgta Factory kompilatoram. Ātrā pārlūka pārbaude ziņo par daļu ģeometrisku kļūdu; tā nav pilns teksta pārklāšanās vai satura kvalitātes audits.

HTML/JSON avotu ģenerators: `python3 build_preview.py`. Dizainu avots ir šis skripts un `assets/template.css`; pēc ģenerēto HTML manuālām izmaiņām palaists ģenerators tās pārrakstīs.

Attēla ģenerēšanas uzvedne:

> Use case: photorealistic-natural. Asset type: background photograph for a maritime training slide template preview. Create a polished editorial aerial oblique photograph of a modern small LNG carrier at sea, viewed from port quarter, white superstructure, dark navy hull, pale industrial deck with visible cylindrical cargo equipment, open Baltic sea in muted deep blue, distant soft misty horizon, cool early morning daylight, understated professional maritime training aesthetic, crisp realistic texture, wide landscape composition 16:10, vessel on the right two-thirds with calm dark water on the left for text. No text, no logos, no watermarks, no people close up. This is illustrative design content, not a technical engineering reference.
