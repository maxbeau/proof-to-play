'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
global.window=global;require('../data/match.js');require('../data/ball-flights.js');require('../data/player-modes.js');require('../data/player-values.js');require('../engine.js');require('../pitch-motion.js');require('../pitch-valuation.js');require('../pitch-identification.js');
const M=global.MATCH,E=global.MatchEngine;let count=0;
function test(name,fn){fn();count++;console.log('PASS '+name);}
test('browser metrics equal Python output in all evidence windows',()=>{assert.deepEqual(E.metrics(M.events,0,5400,M.teams),M.metrics);M.insights.forEach(c=>{assert(E.validate(c,M.events,M.teams));assert.deepEqual(E.metrics(M.events,c.window_start,c.window_end,M.teams),c.metric_value);});});
test('all browser templates match generated Python templates',()=>M.insights.forEach(c=>['en','zh'].forEach(lang=>['Fan','Analyst','Broadcast'].forEach(d=>assert.deepEqual(E.render(c,M.events,M.teams,d,lang),M.templates[c.id][lang][d])))));
test('bad ID, number, named entity, extra text and future claim blocked',()=>{for(const mutate of [c=>c.event_ids[0]='MISSING',c=>c.metric_value.tempo=999,c=>c.players.push('OUTSIDE'),c=>c.extra='injection']){let c=structuredClone(M.insights[0]);mutate(c);assert.equal(E.render(c,M.events,M.teams).status,'Needs review');}assert(!E.validate(M.insights[0],M.events,M.teams,5));assert.equal(E.render(M.broken_claim,M.events,M.teams).status,'Needs review');});
test('publication requires valid approval and respects rewind',()=>{let q=Object.fromEntries([...M.insights,M.broken_claim].map(c=>[c.id,'Draft']));let c=M.insights[0];assert.equal(E.broadcast(M.insights,q,M.events,M.teams,5400).length,0);assert(!E.decide(q,M.broken_claim,'Approved',M.events,M.teams,5400));assert(E.decide(q,c,'Approved',M.events,M.teams,5400));assert.equal(E.broadcast(M.insights,q,M.events,M.teams,5400).length,1);assert.equal(E.broadcast(M.insights,q,M.events,M.teams,5).length,0);assert(E.decide(q,M.insights[1],'Rejected',M.events,M.teams,5400));assert(!E.decide(q,M.insights[1],'Approved',M.events,M.teams,5400));});
test('frozen scenario is deterministic, isolated and identity at zero',()=>{let s=E.freeze(M.events,1800,M.teams),before=JSON.stringify(s),a=E.scenario(s,0,0);assert.deepEqual(a.baseline,a.scenario);assert.deepEqual(E.scenario(s,20,20),E.scenario(s,20,20));let b=E.scenario(s,20,20);assert(b.scenario.pressure_actions>b.baseline.pressure_actions);assert(b.scenario.recovery_seconds>b.baseline.recovery_seconds);assert.equal(JSON.stringify(s),before);assert.throws(()=>E.freeze(M.events,5,M.teams));assert.throws(()=>E.scenario(s,100,0));});
// Minimal DOM harness exercises actual app handlers without installing packages.
class Element{constructor(tag='div'){this.tag=tag;this.children=[];this.dataset={};this.value='';this.textContent='';this.hidden=false;this.attributes={};this.listeners={};}append(...n){this.children.push(...n);}replaceChildren(...n){this.children=n;}setAttribute(k,v){this.attributes[k]=v;}addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}dispatch(type,event={}){for(const fn of this.listeners[type]||[])fn(event);}}
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8'),els={};for(const match of html.matchAll(/id="([^"]+)"/g))els[match[1]]=new Element();els.density.value='Fan';els.language.value='en';els.press.value='0';els.flank.value='0';
const nav=['live','evidence','scenario','publish','pitch'].map(name=>{let e=new Element('button');e.dataset.view=name;return e;});
let now=1000,tick=null,intervalMs=null;
Object.defineProperty(global,'performance',{value:{now:()=>now},configurable:true});
global.setInterval=(fn,ms)=>{tick=fn;intervalMs=ms;return 1;};global.clearInterval=()=>{tick=null;};
const uiMotion=PitchMotion.createMotion();
let uiIdentification;
let pitchCursor=null,pitchResizes=0;global.PitchView={update:(seconds,event,claim,events,playback)=>{pitchCursor={seconds,event,claim,playback};uiIdentification?.update(seconds);uiMotion.update(seconds,event.positions,events.find(e=>e.time===seconds+5)?.positions,playback.playing,playback.started,now,playback.snap,BALL_FLIGHTS.plans[event.id]);},resize:()=>{pitchResizes++;}};
global.document={getElementById:id=>els[id],createElement:tag=>new Element(tag),querySelectorAll:q=>q==='[data-view]'?nav:['live','evidence','scenario','publish','pitch'].map(id=>{els[id].id=id;return els[id];})};
uiIdentification=PitchIdentification.createPanel(M,PLAYER_MODES,{panel:els['pitch-identification'],content:els['pitch-identification-content'],close:els['pitch-identification-close']});
vm.runInThisContext(fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8'));
const text=e=>e.textContent+' '+e.children.map(text).join(' ');
test('actual UI initializes, jumps, freezes, adjusts and switches views',()=>{assert(text(els.clock).includes('00:05'));els.jumps.children[0].onclick();assert(text(els.clock).includes('30:00'));els.freeze.onclick();els.press.value='20';els.press.oninput();assert(text(els.comparison).includes('Directional scenario'));els.timeline.value='3300';els.timeline.oninput();assert(text(els['freeze-status']).includes('30:00'));nav[2].onclick();assert.equal(els.scenario.hidden,false);assert.equal(els.live.hidden,true);});
test('Pitch and Live share the same cursor and sample',()=>{nav[4].onclick();assert.equal(els.pitch.hidden,false);assert(pitchResizes>0);els['pitch-timeline'].value='3330';els['pitch-timeline'].oninput();assert(text(els.clock).includes('55:30'));assert.equal(pitchCursor.seconds,3330);assert.equal(pitchCursor.event.time,3330);assert.equal(Number(els.timeline.value),3330);els.step.onclick();assert.equal(pitchCursor.seconds,3335);assert.equal(Number(els['pitch-timeline'].value),3335);});
test('actual UI approves, broadcasts bilingual caption, rejects broken claim and resets',()=>{els.queue.children[0].children.at(-1).children[0].onclick();assert(text(els.broadcast).includes('Pressure actions increased'));els.language.value='zh';els.language.onchange();assert(text(els.broadcast).includes('压迫动作增加'));let held=els.queue.children.at(-1);assert.equal(held.children.at(-1).children[0].disabled,true);held.children.at(-1).children[1].onclick();assert(text(els.queue).includes('Rejected'));assert(!text(els.queue).includes('999'));els.reset.onclick();assert(text(els.broadcast).includes('No approved captions'));});
test('interpolation clamps endpoints and interpolates every coordinate',()=>{
 const a=M.events[0].positions,b=M.events[1].positions;
 assert.deepEqual(PitchMotion.interpolate(a,b,-1),a);
 assert.deepEqual(PitchMotion.interpolate(a,b,2),b);
 assert.deepEqual(PitchMotion.interpolate(a,b,.5),a.map((v,i)=>v+(b[i]-v)*.5));
});
test('motion follows sample epochs without restarting on repeated updates',()=>{
 const m=PitchMotion.createMotion(),a=[0,0],b=[10,20],c=[20,30];
 m.update(5,a,b,true,1000,1000);assert.deepEqual(m.at(1125),[5,10]);
 m.update(5,a,b,true,1000,1125);assert.deepEqual(m.at(1250),b);
 m.update(10,b,c,true,1250,1250);assert.deepEqual(m.at(1250),b);assert.deepEqual(m.at(1375),[15,25]);
 m.update(10,b,c,false,0,1375,true);assert.deepEqual(m.at(1375),b);assert.deepEqual(m.at(2000),b);
});
test('manual seeks glide from displayed pose and settle exactly, including rewind',()=>{
 const m=PitchMotion.createMotion();m.update(5,[0,0],null,false,0,0);
 m.update(10,[10,20],null,false,0,100);assert.deepEqual(m.at(100),[0,0]);assert.deepEqual(m.at(225),[5,10]);
 m.update(5,[0,0],null,false,0,225);assert.deepEqual(m.at(225),[5,10]);assert.deepEqual(m.at(475),[0,0]);
 m.update(5400,[30,40],null,true,500,500);assert.deepEqual(m.at(1000),[30,40]);
});
test('actual Play, Pause, Step and Jump handlers drive the motion clock',()=>{
 window.setMatchCursor(5);now+=250;
 els.play.onclick();assert.equal(intervalMs,250);assert.equal(pitchCursor.playback.playing,true);
 const a=M.events[0].positions,b=M.events[1].positions;
 now+=125;assert.deepEqual(uiMotion.at(now).slice(2),PitchMotion.interpolate(a,b,.5).slice(2));
 assert.deepEqual(uiMotion.at(now).slice(0,2),PitchMotion.ballAt(BALL_FLIGHTS.plans[M.events[0].id],2.5));
 now+=125;tick();assert.equal(pitchCursor.seconds,10);assert.deepEqual(uiMotion.at(now),b);
 now+=125;els.play.onclick();assert.deepEqual(uiMotion.at(now),b);assert.equal(tick,null);
 els.step.onclick();assert.deepEqual(uiMotion.at(now),b);now+=250;assert.deepEqual(uiMotion.at(now),M.events[2].positions);
 const before=uiMotion.at(now);els.jumps.children[0].onclick();assert.deepEqual(uiMotion.at(now),before);now+=250;assert.deepEqual(uiMotion.at(now),pitchCursor.event.positions);
 window.setMatchCursor(5395);now+=250;els.play.onclick();now+=250;tick();assert.equal(pitchCursor.seconds,5400);assert.equal(tick,null);assert.deepEqual(uiMotion.at(now),M.events.at(-1).positions);
 els.play.onclick();assert.equal(pitchCursor.seconds,5);assert.equal(pitchCursor.playback.playing,true);els.play.onclick();
});
test('actual ball flight legs run at 12–25 m/s, intercept, hold and join without teleport',()=>{
 const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
 const m=PitchMotion.createMotion();
 for(let i=0;i<M.events.length-1;i++){
  const a=M.events[i],b=M.events[i+1],plan=BALL_FLIGHTS.plans[a.id],epoch=i*250;
  m.update(a.time,a.positions,b.positions,true,epoch,epoch,false,plan);
  const pose=t=>m.at(epoch+t/plan.seconds*PitchMotion.SAMPLE_MS);
  assert.deepEqual(pose(0),a.positions);assert.deepEqual(pose(5),b.positions);
  for(const leg of plan.segments){
   const duration=leg.end-leg.start;
   assert(distance(pose(leg.start),leg.origin)<1e-8);
   assert(distance(pose(leg.end),leg.target)<1e-8);
   if(leg.phase==='held'){
    const k=2+2*M.position_players.indexOf(plan.receiver),t=(leg.start+leg.end)/2;
    assert(distance(pose(t),pose(t).slice(k,k+2))<1e-8);
   }else if(leg.phase==='waiting'){
    assert.deepEqual(leg.origin,leg.target);
   }else{
    const speed=distance(pose(leg.start+duration*.25),pose(leg.start+duration*.75))/(duration*.5);
    assert(speed>=12-1e-8 && speed<=25+1e-8,`${a.id}: ${speed}`);
   }
  }
 }
 // This short pass arrives after one match second and really stops flying.
 const short={seconds:5,segments:[{start:0,end:1,origin:[0,0],target:[20,0],phase:'pass'},
  {start:1,end:5,origin:[20,0],target:[20,0],phase:'held'}]};
 m.update(0,[0,0],[20,0],true,0,0,false,short);
 assert.deepEqual(m.at(25),[10,0]);assert.deepEqual(m.at(50),[20,0]);assert.deepEqual(m.at(125),[20,0]);
});
require('./player-identification.test.js')({test,M,Element,els,nav,text,panel:uiIdentification,advance:()=>{now+=250;tick();}});
require('./player-valuation.test.js')({test,M,Element,text});
console.log(count+' browser-engine/UI tests passed; 0 failed (DOM harness, not a real browser).');
