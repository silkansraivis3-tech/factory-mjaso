(function(){
 'use strict';
 var catalog=window.TEMPLATE_CATALOG,active=0,frame=document.getElementById('preview-frame'),screen=document.getElementById('screen-frame'),well=document.querySelector('.preview-well'),content=document.getElementById('content-size'),size=document.getElementById('screen-size'),notes=document.getElementById('review-notes'),ratings={},storageOK=true;
 try{ratings=JSON.parse(localStorage.getItem('novikontas-template-feedback-v1')||'{}');}catch(e){storageOK=false;}
 var fragment=location.hash.slice(1);catalog.forEach(function(t,i){if(t.id===fragment)active=i;});
 var nav=document.getElementById('template-nav');catalog.forEach(function(t,i){var button=document.createElement('button');button.type='button';button.className='nav-item';button.dataset.index=i;button.innerHTML='<span class="nav-index">'+String(i+1).padStart(2,'0')+'</span><span class="nav-mini '+t.id+'" aria-hidden="true"><i></i><i></i></span><span>'+t.name+'</span>';button.addEventListener('click',function(){select(i);});nav.appendChild(button);});
 document.getElementById('template-total').textContent=String(catalog.length).padStart(2,'0');
 function save(){try{localStorage.setItem('novikontas-template-feedback-v1',JSON.stringify(ratings));document.getElementById('review-saved').textContent='Saglabāts šajā pārlūkā.';}catch(e){storageOK=false;document.getElementById('review-saved').textContent='Piezīmes pieejamas līdz loga aizvēršanai. Saglabā atsauksmes failā.';}}
 function entry(){return ratings[catalog[active].id]||(ratings[catalog[active].id]={rating:null,notes:''});}
 function syncReview(){var state=entry();notes.value=state.notes;document.querySelectorAll('[data-rating]').forEach(function(b){b.setAttribute('aria-pressed',String(state.rating===b.dataset.rating));});document.getElementById('review-saved').textContent=storageOK?'Piezīmes paliek šajā pārlūkā.':'Piezīmes pieejamas līdz loga aizvēršanai.';}
 function config(){frame.contentWindow.postMessage({type:'template-config',content:content.value},'*');}
 function resize(){
   var wh=size.value.split('x').map(Number),ratio=wh[0]/wh[1],full=!!document.fullscreenElement,padding=full?0:(innerWidth<721?16:(innerWidth>1599?56:44));
   var available=well.clientWidth-padding,maxHeight=full?well.clientHeight:Math.max(260,Math.min(innerHeight*.66,860));
   var w=Math.min(available,maxHeight*ratio),h=w/ratio;screen.style.width=w+'px';screen.style.height=h+'px';
   var scale=Math.min(w/1280,h/800);frame.style.transform='translate('+((w-1280*scale)/2)+'px,'+((h-800*scale)/2)+'px) scale('+scale+')';
 }
 function select(i){active=Math.max(0,Math.min(catalog.length-1,i));var t=catalog[active];
   document.querySelectorAll('.nav-item').forEach(function(b){b.setAttribute('aria-current',String(Number(b.dataset.index)===active));});
   document.getElementById('template-count').textContent='ŠABLONS '+String(active+1).padStart(2,'0')+' / '+String(catalog.length).padStart(2,'0');document.getElementById('template-name').textContent=t.name;document.getElementById('template-description').textContent=t.description;
   document.getElementById('standalone-link').href='template-preview/'+t.path;document.getElementById('contract-link').href='template-preview/'+t.contract;
   document.getElementById('previous-template').disabled=active===0;document.getElementById('next-template').disabled=active===catalog.length-1;
   frame.src='template-preview/'+t.path;frame.title=t.name+' — kursa šablons';
   document.getElementById('audit-state').textContent='Ielādē priekšskatījumu…';document.getElementById('audit-state').classList.remove('warning');
   history.replaceState(null,'','#'+t.id);syncReview();resize();
 }
 frame.addEventListener('load',config);content.addEventListener('change',config);size.addEventListener('change',resize);
 addEventListener('message',function(e){if(e.source!==frame.contentWindow||!e.data||e.data.type!=='template-status'||e.data.template!==catalog[active].id)return;var el=document.getElementById('audit-state'),n=e.data.findings.length;el.textContent=n?'Ātrā pārbaude: pārskati ietilpību':'Ātrā pārbaude: saturs slaida robežās';el.classList.toggle('warning',n>0);el.title='Priekšskatījuma ģeometrijas pārbaude; neaizstāj pilnu kursa auditu.';document.getElementById('content-count').textContent=catalog[active].id==='content-in-parts'?e.data.wordsVisible+' vārdi skatā · '+e.data.wordsTotal+' kopā':e.data.wordsVisible+' vārdi skatā';});
 notes.addEventListener('input',function(){entry().notes=notes.value;save();});document.querySelectorAll('[data-rating]').forEach(function(b){b.addEventListener('click',function(){entry().rating=entry().rating===b.dataset.rating?null:b.dataset.rating;save();var v=entry().rating;document.querySelectorAll('[data-rating]').forEach(function(x){x.setAttribute('aria-pressed',String(x.dataset.rating===v));});});});
 document.getElementById('previous-template').addEventListener('click',function(){select(active-1);});document.getElementById('next-template').addEventListener('click',function(){select(active+1);});
 document.getElementById('fullscreen').addEventListener('click',function(){if(document.fullscreenElement){document.exitFullscreen();}else if(well.requestFullscreen){well.requestFullscreen().catch(function(){document.getElementById('audit-state').textContent='Pilnekrāns šajā pārlūkā nav pieejams.';});}});
 document.getElementById('export-feedback').addEventListener('click',function(){var result={type:'novikontas-template-feedback',createdAt:new Date().toISOString(),templates:catalog.map(function(t){return {template:t.id,name:t.name,rating:(ratings[t.id]||{}).rating||null,notes:(ratings[t.id]||{}).notes||''};})};var u=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='template-atsauksmes.json';a.click();setTimeout(function(){URL.revokeObjectURL(u);},1000);});
 addEventListener('resize',resize);document.addEventListener('fullscreenchange',resize);new ResizeObserver(resize).observe(well);select(active);
})();
