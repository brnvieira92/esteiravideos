import {cropPixels,normalizeBox} from './geometry.ts';
import type {Box,Point} from './geometry.ts';

// The preview fills each pane with a centered crop, just like FFmpeg's scale/crop.
export function visibleCrop(box:Box,width:number,height:number,aspect:number):Box {
 const p=cropPixels(box,width,height),w=Math.min(p.w,p.h*aspect),h=w/aspect;
 return {x:(p.x+(p.w-w)/2)/width,y:(p.y+(p.h-h)/2)/height,w:w/width,h:h/height};
}

// Follow the fingers in screen space. The anchor remains under their midpoint.
export function transformCrop(box:Box,start:Point,current:Point,ratio:number,mirrored=false):Box {
 const b=normalizeBox(box),scale=Math.max(Math.max(.01/b.w,.01/b.h),Math.min(Math.min(1/b.w,1/b.h),1/Math.max(.01,ratio)));
 const w=b.w*scale,h=b.h*scale;
 const sx=mirrored?1-start.x:start.x,cx=mirrored?1-current.x:current.x;
 return normalizeBox({x:Math.max(0,Math.min(1-w,b.x+sx*b.w-cx*w)),y:Math.max(0,Math.min(1-h,b.y+start.y*b.h-current.y*h)),w,h});
}
