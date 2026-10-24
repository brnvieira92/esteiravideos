import test from 'node:test';
import assert from 'node:assert/strict';
import {blank,newCutFrom} from '../src/cuts.ts';

test('new cuts inherit framing and style without inheriting identity, interval or subtitle text',()=>{
 const current={...blank(),id:'saved-cut',name:'Primeiro',start:1,end:8,layout:'combined',split:.48,
 game:{x:.06,y:.13,w:.62,h:.87},cam:{x:.69,y:.51,w:.31,h:.27},fontSize:72,margin:130,outline:4,
 subtitles:[{start:0,end:1,text:'Só deste corte'}]};
 const next=newCutFrom(current,12,120);
 assert.equal(next.id,undefined);assert.equal(next.name,'Novo corte');
 assert.equal(next.start,12);assert.equal(next.end,42);assert.deepEqual(next.subtitles,[]);
 for(const key of ['layout','game','cam','split','fontSize','margin','outline']) assert.deepEqual(next[key],current[key]);
 next.cam.x=0;next.game.y=0;
 assert.equal(current.cam.x,.69);assert.equal(current.game.y,.13);
});
test('new interval stays within source and remains valid at end of recording',()=>{
 for(const time of [0,95,100]){
  const next=newCutFrom(blank(),time,100);
  assert.ok(next.start>=0&&next.start<next.end&&next.end<=100);
 }
});
