import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeBox, cropPixels} from '../src/geometry.ts';

test('screenshot: overflowing gameplay shifts up without changing size', () => {
  const raw = {x:.06,y:.35,w:.62,h:.87};
  const adjusted = normalizeBox(raw);
  assert.ok(Math.abs(adjusted.y-.13)<1e-12);
  assert.equal(adjusted.h,.87);
  assert.equal(adjusted.x,.06);
  assert.deepEqual(cropPixels(raw,1920,1080),cropPixels(adjusted,1920,1080));
  assert.deepEqual(cropPixels(raw,1920,1080),{x:114,y:140,w:1190,h:938});
  assert.deepEqual(normalizeBox(adjusted),adjusted);
});

test('right/bottom overflow, full frame and already valid webcam', () => {
  assert.deepEqual(normalizeBox({x:.9,y:.9,w:.5,h:.5}),{x:.5,y:.5,w:.5,h:.5});
  assert.deepEqual(normalizeBox({x:1,y:1,w:1,h:1}),{x:0,y:0,w:1,h:1});
  const cam={x:.69,y:.51,w:.31,h:.27};
  assert.deepEqual(normalizeBox(cam),cam);
});

test('invalid size and non-finite values are still rejected', () => {
  for(const box of [{x:0,y:0,w:0,h:1},{x:0,y:0,w:1,h:1.1},
    {x:-.1,y:0,w:1,h:1},{x:0,y:NaN,w:1,h:1}]) {
    assert.throws(()=>normalizeBox(box));
  }
});

const {boxFromPoints,moveBox,resizeBox}=await import('../src/geometry.ts');
test('draw in either direction and clamp a selection to the original frame',()=>{
 const a={x:.7,y:.5},b={x:.98,y:.8};
 assert.deepEqual(boxFromPoints(a,b),boxFromPoints(b,a));
 const box=boxFromPoints({x:-.2,y:-.1},{x:1.5,y:1.2});
 assert.deepEqual(box,{x:0,y:0,w:1,h:1});
 assert.deepEqual(boxFromPoints({x:1,y:1},{x:1,y:1}),{x:.99,y:.99,w:.01,h:.01});
});
test('moving a facecam keeps its size and stays inside the recording',()=>{
 const box={x:.69,y:.51,w:.31,h:.27};
 const moved=moveBox(box,.5,.9);
 assert.equal(moved.w,box.w);assert.equal(moved.h,box.h);
 assert.equal(moved.x,.69);assert.equal(moved.y,.73);
 assert.deepEqual(moveBox(box,-2,-2),{...box,x:0,y:0});
});
test('all four resize corners preserve the opposite corner and a valid minimum size',()=>{
 const box={x:.2,y:.2,w:.4,h:.4};
 for(const corner of ['nw','ne','sw','se']){
  const resized=resizeBox(box,corner,{x:-2,y:2});
  assert.ok(resized.w>=.01-1e-12&&resized.h>=.01-1e-12);
  assert.ok(resized.x>=0&&resized.y>=0&&resized.x+resized.w<=1+1e-12&&resized.y+resized.h<=1+1e-12);
 }
 const resized=resizeBox(box,'se',{x:.8,y:.9});
 assert.equal(resized.x,.2);assert.equal(resized.y,.2);
 assert.ok(Math.abs(resized.w-.6)<1e-12&&Math.abs(resized.h-.7)<1e-12);
});
