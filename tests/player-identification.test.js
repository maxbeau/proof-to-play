'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

module.exports = ({test, M, Element, els, nav, text, panel, advance}) => {
 const I = global.PitchIdentification, data = global.PLAYER_MODES;
 test('identification maps all 1080 samples x 22 token indices to generated state and simulated speed', () => {
  const before = JSON.stringify([M, data]);
  const roles = ['goalkeeper', ...Array(4).fill('defender'), 'winger', 'midfielder', 'midfielder', 'winger', 'forward', 'forward',
   'goalkeeper', ...Array(4).fill('defender'), 'midfielder', 'midfielder', 'midfielder', 'winger', 'forward', 'winger'];
  for (let n = 0; n < M.events.length; n++) for (let i = 0; i < 22; i++) {
   const event = M.events[n], state = I.currentPlayer(M, data, i, event.time), k = 2 + 2*i;
   const previous = n ? M.events[n-1].positions.slice(k,k+2) : data.initial.positions[i];
   const speed = Math.hypot(event.positions[k]-previous[0], event.positions[k+1]-previous[1])/5;
   assert.equal(state.status, 'selected'); assert.equal(state.id, M.position_players[i]);
   assert.equal(state.team, M.teams[Math.floor(i/11)]); assert.equal(state.role, roles[i]);
   assert.equal(state.mode, data.samples[n].modes[i]); assert.equal(state.speed, speed);
   assert.equal(state.seconds, event.time); assert.equal(state.sampleNumber, n+1);
   assert.deepEqual(state.weights, data.players[i].weights);
   for (const key of ['maxSpeed','maxForce','response','stamina']) assert.equal(state.attributes[key], data.players[i][key]);
  }
  assert.equal(JSON.stringify([M, data]), before);
 });

 test('identification follows actual Play Pause Step Jump sliders rewind and end-of-match handlers', () => {
  const check = seconds => {
   const state = panel.state(); assert.equal(state.seconds, seconds); assert.equal(state.id, 'AQ-06');
   assert.deepEqual(state, I.currentPlayer(M, data, 5, seconds));
   assert(text(els['pitch-identification-content']).includes('Current sample ' + seconds/5 + ' ·'));
   assert(text(els['pitch-identification-content']).includes(state.speed.toFixed(2) + ' m/s'));
  };
  window.setMatchCursor(5); panel.select(5); check(5);
  els.play.onclick(); advance(); check(10); els.play.onclick(); check(10);
  els.step.onclick(); check(15);
  els.jumps.children[0].onclick(); check(1800);
  els.timeline.value = '3300'; els.timeline.oninput(); check(3300);
  els['pitch-timeline'].value = '4500'; els['pitch-timeline'].oninput(); check(4500);
  nav[0].onclick(); els.step.onclick(); check(4505); nav[4].onclick(); check(4505);
  window.setMatchCursor(5395); els.play.onclick(); advance(); check(5400);
  els.play.onclick(); check(5); els.play.onclick();
  // Pick a real assignment transition for this player, not just unchanged holder samples.
  const transition = data.samples.findIndex((row,n) => n > 0 && row.modes[5] !== data.samples[n-1].modes[5]);
  assert(transition > 0); window.setMatchCursor(data.samples[transition-1].time);
  const oldMode = panel.state().mode; els.step.onclick(); check(data.samples[transition].time);
  assert.notEqual(panel.state().mode, oldMode);
 });

 test('panel switches player closes and clears every stale field when sample or sidecar is missing', () => {
  const source = structuredClone(data), box = new Element(), content = new Element(), close = new Element('button');
  const local = I.createPanel(M, source, {panel:box, content, close});
  local.update(5); local.select(5); assert(text(content).includes('AQ-06'));
  local.select(19); assert(text(content).includes('ML-09')); assert(!text(content).includes('AQ-06'));
  const old = text(content); source.samples[1].modes[19] = 'invalid'; local.update(10);
  assert.equal(local.state().status, 'unavailable'); assert.notEqual(text(content), old);
  assert(text(content).includes('Selection unavailable at 00:10'));
  for (const stale of ['ML-09','Simulated speed','Steering weights','Current sample 1']) assert(!text(content).includes(stale));
  local.update(15); assert.equal(local.state().status, 'selected');
  local.update(17); assert.equal(local.state().status, 'unavailable'); assert(!text(content).includes('ML-09'));
  local.update(5400); assert(text(content).includes('Current sample 1080'));
  local.select(null); assert.equal(box.hidden, true); assert.equal(content.children.length, 0);
  local.select(0); close.dispatch('click'); assert.equal(box.hidden, true); assert.equal(local.state().status, 'closed');
  local.update(5); assert.equal(box.hidden, true);
  for (const bad of [undefined, {...data,seed:-1}, {...data,position_players:[]}, {...data,samples:[]}]) {
   assert.equal(I.currentPlayer(M,bad,0,5).status,'unavailable');
  }
  for (const index of [-1,22,NaN,1.5]) assert.equal(I.currentPlayer(M,data,index,5).status,'unavailable');
  const missingPositions = {...M,events:[{...M.events[0],positions:[]},...M.events.slice(1)]};
  assert.equal(I.currentPlayer(missingPositions,data,0,5).status,'unavailable');
  assert.equal(I.currentPlayer(M,{...data,initial:null},0,5).status,'unavailable');
 });

 test('token mesh ancestry and click gestures select while drag pan pinch cancel and zoom do not', () => {
  const canvas = new Element('canvas'); canvas.getBoundingClientRect = () => ({left:100,top:20,right:700,bottom:420});
  const group = {userData:{playerIndex:19}}, head = {userData:{},parent:group};
  assert.equal(I.tokenIndex(head),19); assert.equal(I.tokenIndex({userData:{}}),null);
  let hit = head, picks = 0; const selected = [];
  I.attachPicking(canvas, (x,y) => { assert.equal(x,150); assert.equal(y,80); picks++; return I.tokenIndex(hit); }, index => selected.push(index));
  const event = (extra={}) => ({pointerId:1,button:0,isPrimary:true,clientX:150,clientY:80,...extra,
   preventDefault:()=>assert.fail('selection must not cancel OrbitControls'),stopPropagation:()=>assert.fail('selection must not intercept OrbitControls')});
  const fire = (type,extra) => canvas.dispatch(type,event(extra));
  fire('pointerdown'); fire('pointerup'); assert.deepEqual(selected,[19]);
  hit = {userData:{},parent:{userData:{playerIndex:5}}}; fire('pointerdown'); fire('pointerup'); assert.deepEqual(selected,[19,5]);
  hit = null; fire('pointerdown'); fire('pointerup'); assert.deepEqual(selected,[19,5,null]);
  fire('pointerdown'); fire('pointermove',{clientX:170}); fire('pointermove'); fire('pointerup'); // dragged away and back
  fire('pointerdown',{button:2}); fire('pointerup',{button:2});
  fire('pointerdown',{button:1}); fire('pointerup',{button:1});
  fire('pointerdown',{ctrlKey:true}); fire('pointerup');
  fire('pointerdown'); fire('wheel'); fire('pointerup');
  fire('pointerdown'); fire('pointercancel'); fire('pointerup');
  fire('pointerdown'); fire('pointerdown',{pointerId:2,isPrimary:false}); fire('pointerup',{pointerId:2,isPrimary:false}); fire('pointerup');
  fire('pointerdown'); fire('pointerup',{clientX:701});
  assert.equal(picks,3); assert.equal(selected.length,3);
  fire('pointerdown'); fire('pointerup'); assert.equal(picks,4); // cancelled gestures do not strand the picker
 });

 test('steering display distinguishes used conditional weights from stored unused weights', () => {
  for (const mode of Object.keys(I.MODES)) {
   for (const weight of ['anchor','space','wander']) assert(I.weightStatus(weight,mode).includes('unused'));
   assert.equal(I.weightStatus('pursuit',mode).startsWith('Used'),mode==='presser');
   assert.equal(I.weightStatus('mark',mode).startsWith('Used'),mode==='marker');
   assert(I.weightStatus('separation',mode).includes('within 4 m'));
  }
 });

 test('Pitch source wires current sample raycasting without changing fallback or motion paths', () => {
  const source = fs.readFileSync(path.join(__dirname,'../pitch.js'),'utf8');
  assert(source.includes('group.userData.playerIndex = index'));
  assert(source.includes('raycaster.intersectObjects(players, true)'));
  assert(source.includes('raycaster.setFromCamera(pointer, camera)'));
  assert(source.includes('scene.updateMatrixWorld(true)'));
  assert(source.includes('camera.updateMatrixWorld()'));
  assert(source.includes('window.PitchIdentification.attachPicking(canvas, pickPlayer, index => identification.select(index))'));
  assert(source.indexOf('identification.update(seconds)') < source.indexOf('if (!event?.positions) return'));
  window.pitchModuleFailed(); assert.equal(els['pitch-canvas'].hidden,true);
  assert(text(els['pitch-fallback']).includes('python3 -m http.server 8000'));
  nav[0].onclick(); els.step.onclick(); assert.equal(els.live.hidden,false);
 });
};
