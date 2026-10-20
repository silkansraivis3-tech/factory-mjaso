(function(){
  'use strict';
  var slide=document.getElementById('slide'), selectedStep=1;
  function fit(){var s=Math.min(innerWidth/1280,innerHeight/800);slide.style.transform='translate('+((innerWidth-1280*s)/2)+'px,'+((innerHeight-800*s)/2)+'px) scale('+s+')';}
  function audit(){
    var bounds=slide.getBoundingClientRect(), findings=[];
    Array.from(slide.querySelectorAll('h1,h2,h3,p,li,td,th,[data-fit-region],.dense-with-rail,.chunk-pages,.chunk-page,.reading-visual-grid,.step-controls,.bottomline,.compare-copy,.recap-card')).forEach(function(el){
      if(!el.getClientRects().length)return;var r=el.getBoundingClientRect();
      if(r.bottom>bounds.bottom+1||r.right>bounds.right+1||r.left<bounds.left-1||r.top<bounds.top-1) findings.push({type:'outside-slide',element:el.tagName,text:el.textContent.trim().slice(0,70)});
      if(el.clientHeight>0&&el.scrollHeight>el.clientHeight+3) findings.push({type:'overflow',element:el.tagName,text:el.textContent.trim().slice(0,70)});
      if(el.hasAttribute('data-fit-region')&&el.parentElement){var pr=el.parentElement.getBoundingClientRect();if(r.bottom>pr.bottom+2)findings.push({type:'region-overflow',text:el.textContent.trim().slice(0,70)});}
    });
    var content=slide.querySelector('.slide-content'),footer=slide.querySelector('.bottomline');
    if(content&&footer){var f=footer.getBoundingClientRect();Array.from(content.querySelectorAll('h1,h2,p,.step-controls')).forEach(function(el){if(el.getClientRects().length&&el.getBoundingClientRect().bottom>f.top+1)findings.push({type:'footer-overlap',text:el.textContent.trim().slice(0,70)});});}
    function words(text){return(text||'').trim().split(/\s+/).filter(Boolean).length;}
    var readingRoot=slide.querySelector('.slide-content'),totalRoot=readingRoot.cloneNode(true);
    totalRoot.querySelectorAll('.stress-copy,.dense-addition,button,.chunk-tabs,.chunk-navigation').forEach(function(el){el.remove();});
    var walker=document.createTreeWalker(totalRoot,NodeFilter.SHOW_TEXT),allText=[],node;while((node=walker.nextNode()))allText.push(node.textContent);
    var payload={type:'template-status',template:document.body.dataset.template,mode:document.body.dataset.mode||'normal',findings:findings,step:selectedStep,wordsVisible:words(readingRoot.innerText),wordsTotal:words(allText.join(' '))};
    if(parent!==window)parent.postMessage(payload,'*');window.templateStatus=payload;return payload;
  }
  function setStep(step){selectedStep=step;
    Array.from(document.querySelectorAll('[data-step-button]')).forEach(function(b){b.setAttribute('aria-pressed',Number(b.dataset.stepButton)===step?'true':'false');});
    Array.from(document.querySelectorAll('[data-highlight]')).forEach(function(e){e.style.opacity=Number(e.dataset.highlight)===step?'1':'.65';});
    var names=['Containment','Liquid level','Vapour space'];document.querySelectorAll('[data-step-name]').forEach(function(e){e.textContent=String(step).padStart(2,'0')+' / '+names[step-1];});
    setTimeout(audit,40);
  }
  var process=[['Observe','Start with the whole picture. Notice the shape, the main elements and their positions.','One clear action per step.'],['Identify','Name the main elements. Match the labels to the parts shown in the diagram.','Use the same names in both views.'],['Explain','Describe the relationship between the elements in your own words.','Connect an observation to its meaning.'],['Check','Return to the diagram and check that your explanation matches what is shown.','Review the same information from another view.']];
  document.querySelectorAll('[data-step-button]').forEach(function(b){b.addEventListener('click',function(){setStep(Number(b.dataset.stepButton));});});
  document.querySelectorAll('[data-process]').forEach(function(b){b.addEventListener('click',function(){var i=Number(b.dataset.process),p=process[i-1];selectedStep=i;document.querySelectorAll('[data-process]').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});document.getElementById('process-number').textContent=String(i).padStart(2,'0');document.getElementById('process-title').textContent=p[0];document.getElementById('process-text').textContent=p[1];document.getElementById('process-foot').textContent=p[2];audit();});});
  var taskButton=document.getElementById('task-demo-button');if(taskButton)taskButton.addEventListener('click',function(){var started=taskButton.dataset.started==='true';taskButton.dataset.started=String(!started);taskButton.querySelector('span').textContent=started?'Preview interaction':'Close preview';document.getElementById('task-demo-result').textContent=started?'':'Demo interaction opened. The final course connects this action to its task.';audit();});
  var chunkPages=Array.from(document.querySelectorAll('[data-chunk-page]')),currentPart=1;
  function showPart(value){
    currentPart=Math.max(1,Math.min(chunkPages.length,value));selectedStep=currentPart;
    chunkPages.forEach(function(page){page.hidden=Number(page.dataset.chunkPage)!==currentPart;});
    document.querySelectorAll('[data-chunk]').forEach(function(button){button.setAttribute('aria-selected',String(Number(button.dataset.chunk)===currentPart));});
    var back=document.querySelector('[data-chunk-back]'),next=document.querySelector('[data-chunk-next]'),counter=document.querySelector('[data-chunk-counter]');
    if(back)back.disabled=currentPart===1;if(next)next.disabled=currentPart===chunkPages.length;
    if(counter)counter.textContent='Part '+currentPart+' of '+chunkPages.length+' / '+['Overview','Detail','Explanation'][currentPart-1];
    requestAnimationFrame(audit);
  }
  document.querySelectorAll('[data-chunk]').forEach(function(button){button.addEventListener('click',function(){showPart(Number(button.dataset.chunk));});button.addEventListener('keydown',function(event){if(event.key!=='ArrowRight'&&event.key!=='ArrowLeft')return;event.preventDefault();var part=Math.max(1,Math.min(chunkPages.length,currentPart+(event.key==='ArrowRight'?1:-1)));showPart(part);document.querySelector('[data-chunk="'+part+'"]').focus();});});
  var chunkBack=document.querySelector('[data-chunk-back]'),chunkNext=document.querySelector('[data-chunk-next]');
  if(chunkBack)chunkBack.addEventListener('click',function(){showPart(currentPart-1);});
  if(chunkNext)chunkNext.addEventListener('click',function(){showPart(currentPart+1);});
  document.querySelectorAll('[data-animation-toggle]').forEach(function(button){button.addEventListener('click',function(){var playing=button.getAttribute('aria-pressed')!=='true';button.setAttribute('aria-pressed',String(playing));button.textContent=playing?'Pause animation':'Play animation';button.parentElement.querySelector('.animated-figure').dataset.playing=String(playing);});});
  document.querySelectorAll('.rotation-model').forEach(function(canvas){
    canvas.height=320;var ctx=canvas.getContext('2d'),angle=-.55,tilt=.23,dragX=null;
    function project(p){var x=p[0]*Math.cos(angle)+p[2]*Math.sin(angle),z=-p[0]*Math.sin(angle)+p[2]*Math.cos(angle),y=p[1]*Math.cos(tilt)-z*Math.sin(tilt);z=p[1]*Math.sin(tilt)+z*Math.cos(tilt);var scale=90*6/(6+z);return{x:260+x*scale,y:160+y*scale,z:z};}
    function draw(){ctx.clearRect(0,0,520,320);ctx.strokeStyle='#23435e';ctx.lineWidth=1;for(var i=-3;i<=3;i++){var a=project([i*.65,1.1,-1.6]),b=project([i*.65,1.1,1.6]);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}var faces=[],n=28;
      for(var j=0;j<n;j++){var t=j*2*Math.PI/n,u=(j+1)*2*Math.PI/n;faces.push({p:[[-1.65,.78*Math.cos(t),.78*Math.sin(t)],[1.65,.78*Math.cos(t),.78*Math.sin(t)],[1.65,.78*Math.cos(u),.78*Math.sin(u)],[-1.65,.78*Math.cos(u),.78*Math.sin(u)]],shade:Math.round(38+13*Math.cos(t-.5))});}
      [-1.65,1.65].forEach(function(x){var cap=[];for(var k=0;k<n;k++){var t=k*2*Math.PI/n;cap.push([x,.78*Math.cos(t),.78*Math.sin(t)]);}faces.push({p:cap,shade:47});});
      faces=faces.map(function(f){var points=f.p.map(project);return{p:points,z:points.reduce(function(s,p){return s+p.z;},0)/points.length,shade:f.shade};}).sort(function(a,b){return b.z-a.z;});
      faces.forEach(function(f){ctx.beginPath();f.p.forEach(function(p,i){if(i)ctx.lineTo(p.x,p.y);else ctx.moveTo(p.x,p.y);});ctx.closePath();ctx.fillStyle='hsl(204 40% '+f.shade+'%)';ctx.fill();ctx.strokeStyle='#8bb9d044';ctx.lineWidth=1;ctx.stroke();});
      [-1.65,1.65].forEach(function(x){var p=project([x,-.78,0]);ctx.beginPath();ctx.arc(p.x,p.y,5,0,Math.PI*2);ctx.fillStyle='#e9ab39';ctx.fill();});canvas.dataset.rotation=String(Math.round(angle*180/Math.PI));
    }
    canvas.parentElement.querySelectorAll('[data-rotate]').forEach(function(button){button.addEventListener('click',function(){angle+=Number(button.dataset.rotate)*Math.PI/8;draw();});});
    canvas.addEventListener('pointerdown',function(e){dragX=e.clientX;canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',function(e){if(dragX===null)return;angle+=(e.clientX-dragX)/Math.max(1,canvas.getBoundingClientRect().width)*4;dragX=e.clientX;draw();});function stop(){dragX=null;}canvas.addEventListener('pointerup',stop);canvas.addEventListener('pointercancel',stop);canvas.addEventListener('lostpointercapture',stop);draw();
  });
  function mode(value){document.body.dataset.mode=value;slide.classList.remove('content-short','content-long');if(value!=='normal')slide.classList.add('content-'+value);requestAnimationFrame(function(){requestAnimationFrame(audit);});}
  addEventListener('message',function(event){if(event.source!==parent||!event.data||event.data.type!=='template-config')return;mode(event.data.content||'normal');});
  addEventListener('resize',function(){fit();audit();});fit();setStep(1);
  if(document.fonts)document.fonts.ready.then(function(){fit();audit();});else setTimeout(audit,100);
  window.templateAudit=audit;
})();
