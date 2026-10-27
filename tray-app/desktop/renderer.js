'use strict';
const compact=new URLSearchParams(location.search).get('view')==='flyout';
document.body.classList.toggle('flyout',compact);
const $=id=>document.getElementById(id);
const meta={
  device:{icon:'<rect x="7" y="3" width="10" height="18" rx="3"/><path d="M10 7h4M10 17h4"/>'},
  gamepad:{icon:'<path d="M7 7h10c3 0 5 9 3 11-2 2-4-3-5-3H9c-1 0-3 5-5 3-2-2 0-11 3-11ZM7 9v5M5 11h4M16 10h1M18 13h1"/>'},
  mouse:{icon:'<rect x="6" y="2" width="12" height="20" rx="6"/><path d="M12 2v7M6 10h12"/>'},
  keyboard:{icon:'<rect x="2" y="5" width="20" height="14" rx="3"/><path d="M6 9h1m4 0h1m4 0h1M6 12h1m4 0h1m4 0h1M7 15h10"/>'},
  headset:{icon:'<path d="M4 14v-3a8 8 0 0 1 16 0v3M4 12H3v7h4v-7H4Zm16 0h1v7h-4v-7h3ZM20 19c0 3-3 3-6 3"/>'}
};
const icons={bolt:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m13 2-8 12h6l-1 8 9-13h-6l1-7Z"/></svg>'};
let model=null,shapeRAF=0,shapeStarted=0;
const motionQuery=matchMedia('(prefers-reduced-motion: reduce)');
const reduced=()=>motionQuery.matches||!!model?.settings.reducedMotion;
function reconcile(rows){
  const keys=new Set(rows.map(r=>r.key));
  for(const card of $('devices').querySelectorAll('.device-card')){
    if(!keys.has(card.dataset.key))card.remove();
  }
  for(const r of rows){
    let card=$('card-'+r.key);
    if(!card){
      const kind=Object.hasOwn(meta,r.kind)?r.kind:'device',m=meta[kind];
      card=document.createElement('article');card.className='device-card '+kind;
      card.id='card-'+r.key;card.dataset.key=r.key;
      card.innerHTML=`<div class="device-top"><span class="device-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${m.icon}</svg></span></div><div class="device-title"><h2 class="device-name"></h2><p class="device-subtitle"></p></div><div class="battery-number"><span class="number">—</span><span class="unit">%</span></div><div class="battery-line"><span class="state-label"></span></div><div class="battery-track"><span class="battery-fill"></span></div>`;
    }
    card.querySelector('.device-name').textContent=r.name;
    card.querySelector('.device-subtitle').textContent=r.source||'已检测到接收器';
    $('devices').append(card);
  }
}
function stateText(r){if(r.supported===false)return '暂不支持电量读取';return r.level===null?'未读到电量':r.charging?'正在充电':r.charging===null?'充电状态未知':r.level<=20?'电量偏低':'电池供电';}
function timestamp(t){return t?new Date(t).toLocaleTimeString('zh-CN',{hour12:false,hour:'2-digit',minute:'2-digit'}):'等待首次读取';}
function render(next){
  model=next;
  reconcile(next.rows);
  $('empty-state').hidden=next.rows.length>0;
  $('empty-state').textContent=next.busy?'正在检测设备…':next.error||'未检测到支持读取电量的设备';
  document.body.classList.toggle('sleeping',document.hidden);
  document.body.classList.toggle('dark',next.settings.theme==='dark'||(next.settings.theme==='system'&&next.dark));
  document.body.classList.toggle('reduced',reduced());
  let count=0,charging=0;
  for(const r of next.rows){
    const card=$(`card-${r.key}`);if(!card)continue;
    const online=r.level!==null;
    count+=online;charging+=!!r.charging;
    card.classList.toggle('offline',!online);card.classList.toggle('charging',!!r.charging);card.classList.toggle('low',online&&r.level<=20);
    card.querySelector('.number').textContent=online?(r.approximate?'≈':'')+r.level:'—';
    card.querySelector('.unit').hidden=!online;
    const status=card.querySelector('.state-label');status.replaceChildren();
    if(r.charging){const bolt=document.createElement('span');bolt.innerHTML=icons.bolt;status.append(bolt);}
    status.append(document.createTextNode(stateText(r)));
    card.querySelector('.battery-fill').style.width=online?r.level+'%':'0%';
    card.setAttribute('aria-label',`${r.name}，${online?r.level+'%':'未读到电量'}，${stateText(r)}`);
    card.title=online?'':r.detail;
  }
  $('flyout-time').textContent=next.busy?'正在更新…':`更新于 ${timestamp(next.updatedAt)} · ${count}/${next.rows.length} 台设备`;
  $('flyout-summary').textContent=`每 ${next.settings.interval} 秒更新`;
  document.querySelectorAll('.refresh').forEach(b=>{b.disabled=next.busy;b.setAttribute('aria-busy',next.busy);b.querySelector('.refresh-label').textContent=next.busy?'正在读取':'刷新电量';});
  updateLoader(next.busy);
}
// A damped physical spring for the sheet/flyout. Retargeting keeps current velocity.
const springs=new WeakMap();
function spring(element,from,transform){
  let s=springs.get(element);
  if(s?.raf)cancelAnimationFrame(s.raf);
  if(reduced()){element.style.transform=transform(0);element.style.opacity='1';return;}
  s=s||{x:from,v:0};s.x=from;s.last=performance.now();
  function step(now){
    const dt=Math.min((now-s.last)/1000,.032);s.last=now;
    const count=4,h=dt/count,k=380,c=2*.8*Math.sqrt(k);
    for(let i=0;i<count;i++){s.v+=(-k*s.x-c*s.v)*h;s.x+=s.v*h;}
    element.style.transform=transform(s.x);element.style.opacity=String(Math.min(1,1-Math.abs(s.x)*.012));
    if(Math.abs(s.x)>.03||Math.abs(s.v)>.03)s.raf=requestAnimationFrame(step);
    else{element.style.transform=transform(0);element.style.opacity='1';s.raf=0;}
  }
  springs.set(element,s);s.raf=requestAnimationFrame(step);
}
function reveal(){
  if(compact)spring($('surface'),18,x=>`translateY(${x}px) scale(${1-x*.0015})`);
}
// Seven cached shapes with equal vertex counts, 650ms per morph / 4550ms per cycle.
const shapes=Array.from({length:7},(_,type)=>Array.from({length:48},(_,i)=>{
  const a=i/48*Math.PI*2;let r=7;
  if(type===1)r=6.4+.8*Math.cos(4*a);
  if(type===2)r=6.3+1.1*Math.cos(5*a);
  if(type===3)r=6.5+.7*Math.cos(3*a);
  if(type===4)r=6.4+.8*Math.cos(8*a);
  if(type===5)r=6.2+1.2*Math.cos(6*a);
  if(type===6)r=6.3+.9*Math.sin(4*a);
  return [10+r*Math.cos(a),10+r*Math.sin(a)];
}));
function updateLoader(busy){
  if(shapeRAF){cancelAnimationFrame(shapeRAF);shapeRAF=0;}
  const elements=[...document.querySelectorAll('.refresh-symbol')];
  if(!busy){elements.forEach(e=>{e.textContent='↻';});return;}
  elements.forEach(e=>e.innerHTML='<svg viewBox="0 0 20 20" aria-hidden="true"><polygon/></svg>');
  const polys=elements.map(e=>e.querySelector('polygon'));shapeStarted=performance.now();
  function frame(now){
    const t=(now-shapeStarted)/650,idx=Math.floor(t)%7,f=t-Math.floor(t),ease=f*f*(3-2*f);
    const points=shapes[idx].map((p,i)=>p.map((v,j)=>v+(shapes[(idx+1)%7][i][j]-v)*ease).map(v=>v.toFixed(2)).join(',')).join(' ');
    polys.forEach(p=>{p.setAttribute('points',points);p.setAttribute('transform',`rotate(${(now-shapeStarted)/18} 10 10)`);});
    if(!reduced()&&!document.hidden)shapeRAF=requestAnimationFrame(frame);
  }
  frame(shapeStarted);
}
document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>window.battery.action(b.dataset.action)));
document.querySelectorAll('.refresh').forEach(b=>b.addEventListener('click',()=>window.battery.refresh()));
document.addEventListener('keydown',e=>{if(e.key==='Escape')window.battery.action('hide');});
document.addEventListener('visibilitychange',()=>{document.body.classList.toggle('sleeping',document.hidden);if(model)updateLoader(model.busy);});
motionQuery.addEventListener('change',()=>{if(model)render(model);});
window.battery.onState(render);window.battery.onReveal(reveal);window.battery.getState().then(render);
