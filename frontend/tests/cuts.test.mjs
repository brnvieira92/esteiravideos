import test from 'node:test';
import assert from 'node:assert/strict';
import {blank,newCutFrom,reactionInterval} from '../src/cuts.ts';

test('new cuts inherit framing and style without inheriting identity, interval or subtitle text',()=>{
 const current={...blank(),id:'saved-cut',name:'Primeiro',start:1,end:8,layout:'combined',split:.48,camFlip:true,
 game:{x:.06,y:.13,w:.62,h:.87},cam:{x:.69,y:.51,w:.31,h:.27},fontSize:72,margin:130,outline:4,
 reactionId:'reaction-id',reactionOffset:-.1,baseVolume:.35,reactionVolume:.8,subtitles:[{start:0,end:1,text:'Só deste corte'}]};
 const next=newCutFrom(current,12,120);
 assert.equal(next.id,undefined);assert.equal(next.name,'Novo corte');
 assert.equal(next.start,12);assert.equal(next.end,42);assert.deepEqual(next.subtitles,[]);
 for(const key of ['camFlip','layout','game','cam','split','fontSize','margin','outline','reactionId','reactionOffset','baseVolume','reactionVolume']) assert.deepEqual(next[key],current[key]);
 next.cam.x=0;next.game.y=0;
 assert.equal(current.cam.x,.69);assert.equal(current.game.y,.13);
});
test('new interval stays within source and remains valid at end of recording',()=>{
 for(const time of [0,95,100]){
  const next=newCutFrom(blank(),time,100);
  assert.ok(next.start>=0&&next.start<next.end&&next.end<=100);
 }
});

test('a new draft accepts the project suggestion and requests authoritative automatic naming',()=>{
 const cut=newCutFrom({...blank(),name:'Nome antigo',autoName:false},1,20,'Projeto — parte 8');
 assert.equal(cut.name,'Projeto — parte 8');assert.equal(cut.autoName,true);assert.equal(cut.id,undefined);
});

test('reaction interval follows its start and actual duration, including recordings',()=>{
 assert.deepEqual(reactionInterval(7,15,60),{start:7,end:22,trimmed:false});
 assert.deepEqual(reactionInterval(10,15,60),{start:10,end:25,trimmed:false});
 assert.deepEqual(reactionInterval(7.125,15.375,60),{start:7.125,end:22.5,trimmed:false});
 assert.deepEqual(reactionInterval(7,15,20),{start:7,end:20,trimmed:true});
 assert.deepEqual(reactionInterval(-2,15,60),{start:0,end:13,trimmed:true});
 for(const values of [[60,15,60],[-20,15,60],[NaN,15,60],[7,0,60],[7,15,Infinity]])assert.equal(reactionInterval(...values),null);
});
