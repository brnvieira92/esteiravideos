import test from 'node:test';
import assert from 'node:assert/strict';
import {visibleCrop,transformCrop} from '../src/previewGeometry.ts';
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
test('gesture begins from the visible center crop, including hidden fill margins',()=>{
 const b=visibleCrop({x:0,y:0,w:1,h:1},1920,1080,9/16);
 close(b.w,1080*9/16/1920);close(b.h,1);close(b.x,(1-b.w)/2);
 const p=transformCrop(b,{x:.5,y:.5},{x:.6,y:.5},1);
 close(p.x,b.x-b.w*.1);close(p.w,b.w);
});
test('pinch preserves the source point under the midpoint and aspect ratio',()=>{
 const b={x:.2,y:.1,w:.5,h:.6},a={x:.3,y:.4},c={x:.4,y:.3};
 const p=transformCrop(b,a,c,2);
 close(p.w,.25);close(p.h,.3);
 close(p.x+c.x*p.w,b.x+a.x*b.w);close(p.y+c.y*p.h,b.y+a.y*b.h);
 close(p.w/p.h,b.w/b.h);
});
test('mirrored camera follows fingers in the displayed direction',()=>{
 const b={x:.2,y:.2,w:.5,h:.5};
 const plain=transformCrop(b,{x:.5,y:.5},{x:.6,y:.5},1);
 const mirrored=transformCrop(b,{x:.5,y:.5},{x:.6,y:.5},1,true);
 close(plain.x,.15);close(mirrored.x,.25);
});
test('extreme gestures stay in bounds, keep their aspect and remain exportable',()=>{
 const b={x:.2,y:.1,w:.4,h:.6};
 for(const ratio of [.0001,.1,1,10,100000]){
  const p=transformCrop(b,{x:.5,y:.5},{x:10,y:-10},ratio);
  assert.ok(p.x>=0&&p.y>=0&&p.x+p.w<=1+1e-9&&p.y+p.h<=1+1e-9);
  assert.ok(p.w>=.01-1e-9&&p.h>=.01-1e-9);
  close(p.w/p.h,b.w/b.h);
 }
});
