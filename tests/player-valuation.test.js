'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const V = require('../pitch-valuation.js');
const values = require('../data/player-values.json');

module.exports = ({test, M, Element, text}) => {
 const modes = global.PLAYER_MODES;
 const make = (sidecar = values) => {
  const content = new Element(), box = new Element(), close = new Element('button');
  const panel = PitchIdentification.createPanel(M, modes, {panel:box,content,close}, sidecar);
  panel.update(1800); panel.select(6); return {panel,content,box,close};
 };
 const rows = content => content.children.find(e => e.className === 'identification-scores')?.children || [];

 test('valuation sidecars regenerate identically and do not mutate source inputs', () => {
  const before = JSON.stringify([M,modes]);
  const a = V.serialized(V.build(M,modes)), b = V.serialized(V.build(M,modes));
  assert.equal(a,b); assert.equal(a,fs.readFileSync(path.join(__dirname,'../data/player-values.json'),'utf8'));
  const script=fs.readFileSync(path.join(__dirname,'../data/player-values.js'),'utf8');
  assert.equal(script,'window.PLAYER_VALUES = '+a.trimEnd()+';\n');
  const context={window:{}}; vm.runInNewContext(script,context);
  assert.equal(JSON.stringify(context.window.PLAYER_VALUES),JSON.stringify(values));
  assert.equal(JSON.stringify([M,modes]),before);
 });

 test('all player scores and weighted values stay in range and decomposition sums exactly', () => {
  assert.equal(values.samples.length,1080);
  for (const [n,sample] of values.samples.entries()) {
   assert.equal(sample.time,M.events[n].time); assert.equal(sample.players.length,22);
   for (const [i,player] of sample.players.entries()) {
    const state=V.current(M,modes,values,i,sample.time); assert(state);
    for(const value of state.scores) assert(value>=0 && value<=1 && Number.isFinite(value));
    assert(state.value>=0 && state.value<=1);
    assert.equal(V.SETS[state.mode].weights.reduce((a,b)=>a+b),100);
    assert.equal(Math.round(state.value*1e8),state.contributions.reduce((sum,v)=>sum+Math.round(v*1e8),0));
    assert.notEqual(modes.players[player[5]].team,modes.players[i].team);
   }
  }
 });

 test('AQ-07 sample 360 panel renders all five scores and exact visible decomposition', () => {
  const {content}=make(), rendered=text(content), state=V.current(M,modes,values,6,1800);
  assert(rendered.includes('AQ-07')); assert(rendered.includes('Current sample 360 · 30:00'));
  assert.deepEqual(state.scores,[0.821340,0.638793,0,0.194410,0.576667]);
  assert.equal(state.value,0.48294930);
  assert.equal(rows(content).length,5);
  rows(content).forEach((row,i)=> {
   assert(text(row).includes(V.NAMES[i]));
   assert(text(row).includes(state.scores[i].toFixed(6)+' × '+state.weights[i].toFixed(2)+' = '+state.contributions[i].toFixed(8)));
  });
  assert(rendered.includes('Total = 0.08213400 + 0.06387930 + 0.00000000 + 0.04860250 + 0.28833350 = 0.48294930'));
  assert(rendered.includes('Active weight set: presser'));
 });

 test('all five modes emphasize the relevant feature and explain the active weight set', () => {
  const {panel,content}=make();
  const focus={holder:'pass',presser:'ball',runner:'space',supporter:'space',marker:'marking'};
  for(const [mode,key] of Object.entries(focus)) {
   const index=modes.samples[359].modes.indexOf(mode); assert(index>=0); panel.select(index);
   const emphasized=rows(content).filter(row=>row.className.includes('is-emphasized'));
   assert.equal(emphasized.length,1); assert.equal(emphasized[0].dataset.feature,key);
   assert(text(emphasized[0]).includes('MODE FOCUS')); assert.equal(rows(content).length,5);
   assert(text(content).includes('Active weight set: '+mode)); assert(text(content).includes(V.SETS[mode].why));
  }
  panel.select(6);
  const transition=modes.samples.findIndex((row,n)=>n>0 && row.modes[6]!==modes.samples[n-1].modes[6]);
  for(const n of [transition-1,transition]) {
   panel.update(modes.samples[n].time);
   assert(text(content).includes('Active weight set: '+modes.samples[n].modes[6]));
   assert.equal(rows(content).filter(row=>row.className.includes('is-emphasized'))[0].dataset.feature,focus[modes.samples[n].modes[6]]);
  }
 });

 test('valuation updates sample endpoints switches closes and removes stale or invalid scores', () => {
  const sidecar=structuredClone(values), {panel,content,box,close}=make(sidecar);
  for(const seconds of [5,1800,5400,1800]) {
   panel.update(seconds); const state=V.current(M,modes,values,6,seconds);
   assert(text(content).includes(state.value.toFixed(8)+' / 1'));
  }
  panel.select(2); assert(text(content).includes('0.44124335 / 1')); assert(!text(content).includes('0.48294930 / 1'));
  sidecar.samples[359].players[2][0]=NaN; panel.update(1800);
  assert(text(content).includes('Scores unavailable at 30:00')); assert.equal(rows(content).length,0);
  assert(!text(content).includes('Total =')); assert(!text(content).includes('0.44124335'));
  panel.update(1805); assert.equal(rows(content).length,5);
  panel.update(1807); assert(text(content).includes('Selection unavailable')); assert.equal(rows(content).length,0);
  close.dispatch('click'); assert(box.hidden); assert.equal(content.children.length,0);
  for(const mutate of [d=>d.seed=-1,d=>d.version='bad',d=>d.position_players.reverse(),d=>d.features.reverse(),
    d=>d.weight_sets.marker.weights[0]=90,d=>d.samples[359].time=0,d=>d.samples[359].signature='stale',
    d=>d.samples[359].modes[6]='runner',d=>d.samples[359].players[6]=[],
    d=>d.samples[359].players[6][0]=1.1,d=>d.samples[359].players[6][0]=0.1234567,
    d=>d.samples[359].players[6][5]=6]) {
   const bad=structuredClone(values); mutate(bad); const view=make(bad);
   assert(text(view.content).includes('Scores unavailable')); assert.equal(rows(view.content).length,0);
  }
  const absent=make(null); assert(text(absent.content).includes('Scores unavailable'));
 });

 test('geometric formulas obey lane obstruction distance cutoff symmetry and nearest-target rules', () => {
  assert.equal(V.segmentDistance([5,3],[0,0],[10,0]),3);
  assert.equal(V.segmentDistance([-3,4],[0,0],[10,0]),5);
  assert.equal(V.segmentDistance([3,4],[0,0],[0,0]),5);
  const players=modes.players, event=structuredClone(M.events[359]);
  const set=(i,xy)=>event.positions.splice(2+2*i,2,...xy);
  // Clear lanes: teammates 10m away, opponent 20m behind. Every best lane = 7/9.
  for(let i=0;i<22;i++) set(i,i===0?[0,0]:i<11?[10,0]:[-20,0]);
  event.positions.splice(0,2,0,0);
  let a=V.scoreSample(event,players,M.teams); assert.equal(a[0].scores[1],0.777778);
  set(11,[5,0]); a=V.scoreSample(event,players,M.teams);
  assert.equal(a[0].scores[1],0); assert.equal(a[0].scores[0],0.5);
  assert.equal(a[0].scores[3],0.525); assert.equal(a[0].scores[4],1); assert.equal(a[0].target,11);
  set(12,[-5,0]); assert.equal(V.scoreSample(event,players,M.teams)[0].target,11);
  for(const [x,shot] of [[0,0],[17.5,0],[35,0.25],[52.5,1],[53,0]]) {
   set(0,[x,0]); assert.equal(V.scoreSample(event,players,M.teams)[0].scores[2],shot);
  }
  set(0,[0,0]); event.positions.splice(0,2,30,0); assert.equal(V.scoreSample(event,players,M.teams)[0].scores[4],0);
  const original=M.events[359], mirror=structuredClone(original);
  mirror.positions=original.positions.map((v,i)=>i%2===0?-v:v);
  const swapped=players.map(p=>({...p,team:M.teams[1-M.teams.indexOf(p.team)]}));
  assert.deepEqual(V.scoreSample(original,players,M.teams),V.scoreSample(mirror,swapped,M.teams));
  assert.throws(()=>V.scoreSample({...event,positions:[NaN]},players,M.teams));
 });

 test('sample marker exceeds distant attacker pressure and deep defenders have zero shot score', () => {
  const get=id=>V.current(M,modes,values,M.position_players.indexOf(id),1800);
  const marker=get('AQ-03'), runner=get('ML-10'), far=get('AQ-10');
  assert.equal(marker.mode,'marker'); assert.equal(runner.mode,'runner');
  assert.equal(marker.target,'ML-07'); assert.equal(marker.scores[3],0.306178);
  assert(marker.scores[3]>far.scores[3]); assert.equal(far.scores[3],0);
  for(const id of ['AQ-01','AQ-02','AQ-03','AQ-04','AQ-05']) assert.equal(get(id).scores[2],0);
  assert.equal(runner.scores[2],0.031610); assert.equal(runner.value,0.48067760);
 });

 test('panel and README disclose synthetic nonlearned valuation and load only local scripts', () => {
  const {content}=make(), read=name=>fs.readFileSync(path.join(__dirname,'..',name),'utf8');
  assert(text(content).includes(V.LABEL)); assert(read('README.md').includes(V.LABEL));
  assert(text(content).includes('not the generator’s assigned target'));
  assert(text(content).includes('regardless of possession'));
  const html=read('index.html');
  for(const file of ['data/player-values.js','pitch-valuation.js']) {
   assert(html.includes('src="'+file+'"')); assert(html.indexOf('src="'+file+'"')<html.indexOf('src="pitch.js"'));
  }
  for(const file of ['pitch-identification.js','pitch-valuation.js']) {
   for(const forbidden of ['fetch(','XMLHttpRequest','innerHTML']) assert(!read(file).includes(forbidden));
  }
 });
};
