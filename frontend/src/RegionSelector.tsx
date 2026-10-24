import {useId,useRef} from 'react';
import type {PointerEvent,KeyboardEvent} from 'react';
import {boxFromPoints,moveBox,normalizeBox,resizeBox,roundBox} from './geometry';
import type {Box,Point} from './geometry';

type Drag = {id:number;start:Point;box:Box;mode:string;bounds:DOMRect;moved:boolean};
function valid(box:Box){try{return normalizeBox(box)}catch{return null}}

export function RegionSelector({box,label,drawMode,onChange,onDrawEnd,width,height}:{
 box:Box;label:string;drawMode:boolean;onChange:(b:Box)=>void;onDrawEnd:()=>void;width:number;height:number;
}){
 const drag=useRef<Drag|null>(null);const hint=useId();const b=valid(box);
 if(!b)return null;
 function point(e:PointerEvent,bounds:DOMRect):Point{return {x:(e.clientX-bounds.left)/bounds.width,y:(e.clientY-bounds.top)/bounds.height}}
 function down(e:PointerEvent<HTMLDivElement>){
  if(e.button!==0||!e.isPrimary||!b)return;
  const handle=(e.target as HTMLElement).closest<HTMLElement>('[data-handle]');
  const mode=drawMode?'draw':handle?.dataset.handle||'draw';
  e.preventDefault();const bounds=e.currentTarget.getBoundingClientRect();
  e.currentTarget.setPointerCapture(e.pointerId);
  drag.current={id:e.pointerId,start:point(e,bounds),box:b,mode,bounds,moved:false};
 }
 function update(e:PointerEvent<HTMLDivElement>){
  const d=drag.current;if(!d||d.id!==e.pointerId)return;
  const p=point(e,d.bounds);const dx=p.x-d.start.x,dy=p.y-d.start.y;
  if(!d.moved&&Math.hypot(dx*d.bounds.width,dy*d.bounds.height)<3)return;
  d.moved=true;
  onChange(roundBox(d.mode==='draw'?boxFromPoints(d.start,p):d.mode==='move'?moveBox(d.box,dx,dy):resizeBox(d.box,d.mode,p)));
 }
 function up(e:PointerEvent<HTMLDivElement>){
  if(drag.current?.id!==e.pointerId)return;
  update(e);const drawn=drag.current.moved&&drag.current.mode==='draw';drag.current=null;
  if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);
  if(drawn)onDrawEnd();
 }
 function keyboard(e:KeyboardEvent){
  if(!b||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;
  e.preventDefault();const step=e.shiftKey?10:1;
  onChange(moveBox(b,e.key==='ArrowLeft'?-step/width:e.key==='ArrowRight'?step/width:0,
   e.key==='ArrowUp'?-step/height:e.key==='ArrowDown'?step/height:0));
 }
 return <div className={'region-overlay '+(drawMode?'drawing':'')} onPointerDown={down} onPointerMove={update}
  onPointerUp={up} onPointerCancel={()=>{drag.current=null}} onLostPointerCapture={()=>{drag.current=null}}
  aria-label={'Área de seleção da '+label}>
  <div className="region-selection" role="group" tabIndex={0} data-handle="move" aria-label={'Região da '+label}
   aria-describedby={hint} onKeyDown={keyboard}
   style={{left:b.x*100+'%',top:b.y*100+'%',width:b.w*100+'%',height:b.h*100+'%'}}>
   <span className="region-name">{label}</span>
   {!drawMode&&['nw','ne','sw','se'].map(c=><span key={c} data-handle={c} className={'region-handle '+c} aria-hidden="true"/>)}
  </div>
  <span id={hint} className="region-instruction">{drawMode?'Clique e arraste para desenhar a região.':'Arraste para mover; use os cantos para redimensionar. Setas ajustam a posição; Shift acelera.'}</span>
 </div>
}

export function RegionControls({box,label,onChange,onEdit,active}:{box:Box;label:string;onChange:(b:Box)=>void;onEdit:()=>void;active:boolean}){
 const b=valid(box);
 const fields=[{key:'x',name:'Posição X',slider:'Posição horizontal',max:b?1-b.w:1,min:0},
  {key:'y',name:'Posição Y',slider:'Posição vertical',max:b?1-b.h:1,min:0},
  {key:'w',name:'Largura',slider:'Largura',max:1,min:.01},
  {key:'h',name:'Altura',slider:'Altura',max:1,min:.01}] as const;
 return <details open className={'region-settings '+(active?'editing':'')}><summary>Região da {label}<span aria-hidden="true">⌄</span></summary>
  <button className="outline select-region" disabled={!b} aria-pressed={active} onClick={onEdit}>Selecionar {label} no vídeo</button>
  {fields.map(f=><div className="region-field" key={f.key}>
   <label className="region-range">{f.slider}<output>{b?Math.round(b[f.key]*100)+'%':'—'}</output>
    <input type="range" aria-label={f.slider+' da '+label} min={f.min} max={f.max} step=".001"
     disabled={!b||f.max===f.min} value={b?.[f.key]??f.min} onChange={e=>onChange({...box,[f.key]:+e.target.value})}/>
   </label>
   <label className="region-number">{f.name}<input type="number" aria-label={f.name+' da '+label} min={f.min} max="1" step=".001"
     value={Number(box[f.key].toFixed(4))} onChange={e=>onChange({...box,[f.key]:+e.target.value})}/></label>
  </div>)}
  {b&&b.w===1&&<p className="help">Reduza a largura para mover a região na horizontal.</p>}
 </details>
}
