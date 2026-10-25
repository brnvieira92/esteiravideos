import type {Box} from './geometry';
export type Subtitle={start:number;end:number;text:string};
export type Cut={autoName?:boolean;camFlip?:boolean;reactionId?:string;reactionOffset?:number;baseVolume?:number;reactionVolume?:number;id?:string;name:string;start:number;end:number;layout:string;game:Box;cam:Box;split:number;fontSize:number;margin:number;outline:number;subtitles:Subtitle[]};
export const blank=():Cut=>({autoName:true,camFlip:false,name:'Novo corte',start:0,end:10,layout:'gameplay',game:{x:0,y:0,w:1,h:1},cam:{x:0,y:0,w:.3,h:.3},split:.35,fontSize:64,margin:120,outline:3,subtitles:[]});

// Framing belongs to the recording; text blocks and time ranges belong to each cut.
export function newCutFrom(current:Cut,time:number,duration:number,name='Novo corte'):Cut {
 const start=time>=duration?Math.max(0,duration-30):Math.max(0,time);
 return {...blank(),name,start,end:Math.min(start+30,duration),
  camFlip:current.camFlip??false,reactionId:current.reactionId,reactionOffset:current.reactionOffset,baseVolume:current.baseVolume,reactionVolume:current.reactionVolume,layout:current.layout,game:{...current.game},cam:{...current.cam},split:current.split,
  fontSize:current.fontSize,margin:current.margin,outline:current.outline};
}
