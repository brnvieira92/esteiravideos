import {useRef,useState} from 'react';
import type {ReactNode,PointerEvent} from 'react';
import type {Box,Point} from './geometry';
import {visibleCrop,transformCrop} from './previewGeometry';

type Target='game'|'cam';
type Source={width:number;height:number};
type Props={children:ReactNode;game:Box;cam:Box;source:Source;camera:Source;layout:string;split:number;mirrored:boolean;onChange:(key:Target,box:Box)=>void;onBegin:()=>void};
type Gesture={key:Target;box:Box;rect:{left:number;top:number;width:number;height:number};points:Point[]};
export function PreviewFraming(p:Props){
 const [enabled,setEnabled]=useState(false),[selected,setSelected]=useState<Target>(p.layout==='webcam'?'cam':'game');
 const pointers=useRef(new Map<number,Point>()),gesture=useRef<Gesture|null>(null),latest=useRef({game:p.game,cam:p.cam}),original=useRef(latest.current);
 latest.current={game:p.game,cam:p.cam};
 const combined=p.layout==='combined',top=p.layout==='webcam'?1:combined?Math.floor(1920*p.split/2)*2/1920:0;
 const point=(e:PointerEvent):Point=>({x:e.clientX,y:e.clientY});
 function clear(){pointers.current.clear();gesture.current=null}
 function rebase(key:Target,rect:Gesture['rect']){
  const source=key==='cam'?p.camera:p.source;
  const b=latest.current[key],aspect=9/16/(key==='cam'?top:1-top);
  const box=Math.abs((b.w*source.width/(b.h*source.height))/aspect-1)<1e-6?b:visibleCrop(b,source.width,source.height,aspect);
  gesture.current={key,rect,box,points:[...pointers.current.values()]};
 }
 function down(e:PointerEvent<HTMLDivElement>){
  if(e.button!==0||pointers.current.size>=2)return;
  e.preventDefault();p.onBegin();e.currentTarget.setPointerCapture(e.pointerId);pointers.current.set(e.pointerId,point(e));
  if(!gesture.current){const r=e.currentTarget.getBoundingClientRect(),key=p.layout==='webcam'||combined&&e.clientY<r.top+r.height*top?'cam':'game';setSelected(key);
   const y=key==='cam'?0:top,h=key==='cam'?top:1-top;
   rebase(key,{left:r.left,top:r.top+r.height*y,width:r.width,height:r.height*h});
  }else rebase(gesture.current.key,gesture.current.rect);
 }
 function update(e:PointerEvent<HTMLDivElement>){
  const g=gesture.current;if(!g||!pointers.current.has(e.pointerId))return;
  e.preventDefault();pointers.current.set(e.pointerId,point(e));
  const now=[...pointers.current.values()],center=(ps:Point[])=>({x:ps.reduce((s,v)=>s+v.x,0)/ps.length,y:ps.reduce((s,v)=>s+v.y,0)/ps.length});
  const a=center(g.points),b=center(now),distance=(ps:Point[])=>Math.hypot(ps[1].x-ps[0].x,ps[1].y-ps[0].y);
  if(g.points.length!==now.length)return;
  const local=(v:Point)=>({x:(v.x-g.rect.left)/g.rect.width,y:(v.y-g.rect.top)/g.rect.height});
  const ratio=now.length===2?distance(now)/Math.max(1,distance(g.points)):1;
  if(Math.hypot(a.x-b.x,a.y-b.y)<1&&Math.abs(ratio-1)<.005)return;
  const box=transformCrop(g.box,local(a),local(b),ratio,g.key==='cam'&&p.mirrored);
  latest.current={...latest.current,[g.key]:box};p.onChange(g.key,box);
 }
 function up(e:PointerEvent<HTMLDivElement>){
  if(!pointers.current.has(e.pointerId))return;
  pointers.current.delete(e.pointerId);
  if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);
  if(pointers.current.size&&gesture.current)rebase(gesture.current.key,gesture.current.rect);else clear();
 }
 function zoom(ratio:number){
  clear();p.onBegin();const key=p.layout==='webcam'?'cam':combined?selected:'game',source=key==='cam'?p.camera:p.source,h=key==='cam'?top:1-top;
  const b=visibleCrop(p[key],source.width,source.height,9/16/h);
  p.onChange(key,transformCrop(b,{x:.5,y:.5},{x:.5,y:.5},ratio,p.mirrored&&key==='cam'));
 }
 return <><div className="preview-framing-toolbar"><button aria-pressed={enabled} onClick={()=>{clear();if(!enabled){original.current={game:p.game,cam:p.cam};p.onBegin()}setEnabled(!enabled)}}>{enabled?'Concluir enquadramento':'Ajustar na prévia'}</button>{enabled&&<><button aria-label="Diminuir zoom do enquadramento" onClick={()=>zoom(1/1.15)}>−</button><button aria-label="Aumentar zoom do enquadramento" onClick={()=>zoom(1.15)}>+</button><button onClick={()=>{clear();p.onChange('game',original.current.game);p.onChange('cam',original.current.cam)}}>Desfazer ajustes</button></>}</div>
 <div className={'vertical-preview '+(enabled?'framing-active':'')}>{p.children}{enabled&&<div className="preview-framing-overlay" aria-label="Arraste e pince para enquadrar o vídeo" onPointerDown={down} onPointerMove={update} onPointerUp={up} onPointerCancel={clear} onLostPointerCapture={e=>{if(pointers.current.has(e.pointerId))clear()}}>
  {top>0&&<div className={'preview-pane '+(selected==='cam'?'selected':'')} style={{top:0,height:top*100+'%'}}><span>Webcam · arraste ou pince</span></div>}
  {top<1&&<div className={'preview-pane '+(selected==='game'?'selected':'')} style={{top:top*100+'%',height:(1-top)*100+'%'}}><span>Gameplay · arraste ou pince</span></div>}
 </div>}</div>{enabled&&<p className="preview-gesture-help">Arraste a imagem com um dedo. Afaste dois dedos para aproximar; junte para afastar. Toque na parte que deseja ajustar. Conclua para voltar a rolar sobre a prévia.</p>}</>;
}
