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
