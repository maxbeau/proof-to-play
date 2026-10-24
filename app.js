/* Synthetic / Simulated Match — all UI is local, text-only DOM rendering. */
'use strict';
const M=window.MATCH,E=window.MatchEngine,$=id=>document.getElementById(id);
let cursor=5,timer=null,frozen=null,queue={};
const all=[...M.insights,M.broken_claim];
const clock=s=>Math.floor(s/60).toString().padStart(2,'0')+':'+(s%60).toString().padStart(2,'0');
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function button(text,fn){const b=node('button',text);b.onclick=fn;return b;}
function stop(){clearInterval(timer);timer=null;$('play').textContent='Play';}
function pitchUpdate(){
 if(!window.PitchView)return;
 const current=M.events.find(e=>e.time===cursor),active=M.insights.find(c=>c.window_start<=cursor&&cursor<=c.window_end)||null;
 window.PitchView.update(cursor,current,active,M.events);
}
function view(name){document.querySelectorAll('main>section').forEach(s=>s.hidden=s.id!==name);document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===name)));if(name==='pitch'){pitchUpdate();window.PitchView?.resize();}}
window.setMatchCursor=seconds=>{stop();cursor=Math.max(5,Math.min(5400,Math.round(Number(seconds)/5)*5));paint();};
window.pitchModuleFailed=()=>{const message=$('pitch-fallback');if(message){message.hidden=false;message.textContent='Pitch view needs a local server or the GitHub Pages link; use python3 -m http.server 8000';}};
window.pitchViewReady=api=>{window.PitchView=api;pitchUpdate();};
function card(c,publishing=false,air=false){
 const out=E.render(c,M.events,M.teams,air?'Broadcast':$('density').value,$('language').value,cursor),valid=out.status==='Verified';
 const box=node('article',undefined,'card');box.append(node('small',M.label),node('p',out.status+(publishing?' · '+queue[c.id]:''),valid?'badge':'badge held'));
 const cap=node('div',undefined,'caption');cap.lang=$('language').value;
 cap.append(node('small',cap.lang==='zh'?'发生了什么':'What happened'),node('p',out.what),node('small',cap.lang==='zh'?'为什么重要':'Why it matters'),node('p',out.why));box.append(cap);
 if(valid){
  box.append(node('p','Evidence · '+clock(c.window_start)+'–'+clock(c.window_end)+' · '+c.formula_version));
  const drawer=node('details'),summary=node('summary','Evidence drawer · event IDs, formula and source rows');drawer.append(summary,node('pre',JSON.stringify(c,null,2)));
  const raw=node('details');raw.append(node('summary','Source events in this window'),node('pre',JSON.stringify(M.events.filter(e=>c.event_ids.includes(e.id)),null,2)));drawer.append(raw);box.append(drawer);
 }else box.append(node('p',out.evidence));
 if(publishing){
  const controls=node('div',undefined,'controls');
  for(const action of ['Approved','Rejected']){const b=button(action==='Approved'?'Approve':'Reject',()=>{E.decide(queue,c,action,M.events,M.teams,cursor);paint();});b.disabled=queue[c.id]!=='Draft'||(action==='Approved'&&!valid);controls.append(b);}box.append(controls);
 }else if(valid&&!air)box.append(button('Open producer queue',()=>view('publish')));
 return box;
}
function fill(id,claims,publication=false,air=false){$(id).replaceChildren();if(!claims.length)$(id).append(node('p',air?'No approved captions at this cursor.':'No verified moments yet. Use a turning-point jump or play the timeline.'));claims.forEach(c=>$(id).append(card(c,publication,air)));}
function paint(){
 $('timeline').value=cursor;if($('pitch-timeline'))$('pitch-timeline').value=cursor;$('clock').textContent=clock(cursor)+' / 90:00';
 const current=M.events.find(e=>e.time===cursor),start=Math.max(0,cursor-600),m=E.metrics(M.events,start,cursor,M.teams);
 $('score').textContent=M.teams.map(t=>t+' '+current.state.score[t]).join(' · ');
 $('state').textContent=JSON.stringify(current,null,2);
 $('metrics').replaceChildren();
 const values=[...M.teams.map(t=>[t+' possession proxy',m.possession_pct[t]+'%']),['Pressing proxy',m.pressing_proxy+' /min'],['Passing tempo',m.tempo+' /min']];
 values.forEach(([label,value])=>{const n=node('div',undefined,'metric');n.append(node('strong',value),node('span',label));$('metrics').append(n);});
 $('players').textContent='Key players by completed passes · '+(m.key_players.map(p=>p.player+': '+p.completed_passes).join(' · ')||'No completed passes yet')+' · Window '+clock(start)+'–'+clock(cursor);
 const visible=M.insights.filter(c=>c.window_end<=cursor);
 fill('live-cards',visible);fill('evidence-cards',[...visible,M.broken_claim]);fill('queue',[...visible,M.broken_claim],true);
 fill('broadcast',E.broadcast(all,queue,M.events,M.teams,cursor),false,true);
 pitchUpdate();
}
function scenario(){
 $('press-value').textContent=$('press').value+'%';$('flank-value').textContent=$('flank').value+' percentage points';if(!frozen)return;
 const result=E.scenario(frozen,Number($('press').value),Number($('flank').value));
 const table=node('table'),head=node('tr');['Next ten minutes','Baseline continuation','Directional scenario'].forEach(t=>head.append(node('th',t)));table.append(head);
 [['pressure_actions','Pressure actions (index count)'],['flank_share_pct','Flank pass share (%)'],['recovery_seconds','Recovery (seconds)']].forEach(([key,label])=>{const row=node('tr');[label,result.baseline[key],result.scenario[key]].forEach(t=>row.append(node('td',t)));table.append(row);});
 const details=node('details');details.append(node('summary','Frozen snapshot, source IDs and scenario formulas'),node('pre',JSON.stringify({snapshot:frozen,result},null,2)));
 $('comparison').replaceChildren(node('h3',result.label),table,node('p',result.assumptions),details);
}
all.forEach(c=>queue[c.id]='Draft');
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
$('pitch-timeline').oninput=()=>window.setMatchCursor(Number($('pitch-timeline').value));
$('play').onclick=()=>{if(timer){stop();return;}if(cursor>=5400)cursor=5;$('play').textContent='Pause';timer=setInterval(()=>{cursor=Math.min(5400,cursor+5);paint();if(cursor===5400)stop();},250);};
$('step').onclick=()=>{stop();cursor=Math.min(5400,cursor+5);paint();};
$('timeline').oninput=()=>{stop();cursor=Number($('timeline').value);paint();};
M.insights.forEach(c=>$('jumps').append(button(c.kind+' · '+clock(c.window_end),()=>{stop();cursor=c.window_end;paint();})));
$('density').onchange=paint;$('language').onchange=paint;
$('freeze').onclick=()=>{stop();try{frozen=E.freeze(M.events,cursor,M.teams);$('freeze-status').textContent='Frozen at '+clock(cursor)+'. Moving replay will not change this snapshot.';scenario();}catch(err){$('freeze-status').textContent=err.message;}};
$('press').oninput=scenario;$('flank').oninput=scenario;
$('reset').onclick=()=>{all.forEach(c=>queue[c.id]='Draft');paint();};
paint();
