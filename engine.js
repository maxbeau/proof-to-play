/* Synthetic / Simulated Match — pure deterministic browser functions. */
(function(root){
'use strict';
const LABEL='Synthetic / Simulated Match', VERSION='events-v1.0';
const kinds={pressing:['pressing_proxy',1],flank:['flank_share_pct',15],fatigue:['recovery_seconds',3]};
const round=n=>Math.floor(n*100+.5)/100;
const slice=(events,start,end)=>events.filter(e=>e.time>start&&e.time<=end);
function metrics(events,start,end,teams){
 const rows=slice(events,start,end); if(!rows.length||end<=start) throw Error('Empty window');
 const passes=rows.filter(e=>e.event_type==='pass'), recovery=rows.filter(e=>e.event_type==='recovery');
 const counts={}; passes.filter(e=>e.outcome==='complete').forEach(e=>counts[e.player]=(counts[e.player]||0)+1);
 return {possession_pct:Object.fromEntries(teams.map(t=>[t,round(100*rows.filter(e=>e.state.possession_team===t).length/rows.length)])),pressing_proxy:round(rows.filter(e=>e.event_type==='pressure').length/((end-start)/60)),tempo:round(passes.length/((end-start)/60)),flank_share_pct:passes.length?round(100*passes.filter(e=>e.zone!=='center').length/passes.length):0,recovery_seconds:recovery.length?round(recovery.reduce((n,e)=>n+e.recovery_seconds,0)/recovery.length):0,pass_count:passes.length,shot_count:rows.filter(e=>e.event_type==='shot').length,key_players:Object.entries(counts).sort((a,b)=>b[1]-a[1]||(a[0]<b[0]?-1:1)).slice(0,3).map(([player,completed_passes])=>({player,completed_passes}))};
}
const canonical=o=>JSON.stringify(o&&typeof o==='object'?(Array.isArray(o)?o.map(x=>JSON.parse(canonical(x))):Object.fromEntries(Object.keys(o).sort().map(k=>[k,JSON.parse(canonical(o[k]))]))):o);
function validate(c,events,teams,now=5400){
 try {
 const s=c.window_start,e=c.window_end, spec=kinds[c.kind];
 if(!spec||!Number.isInteger(s)||!Number.isInteger(e)||e-s!==600||s<0||e>now||e>events.at(-1).time)return false;
 const rows=slice(events,s,e),a=metrics(events,s,(s+e)/2,teams),b=metrics(events,(s+e)/2,e,teams);
 if(b[spec[0]]-a[spec[0]]<spec[1])return false;
 const expected={id:c.kind+'-'+e,kind:c.kind,label:LABEL,event_ids:rows.map(r=>r.id),window_start:s,window_end:e,metric_value:metrics(events,s,e,teams),comparison:{field:spec[0],first_half:a[spec[0]],second_half:b[spec[0]]},teams:[...new Set(rows.map(r=>r.team))].sort(),players:[...new Set(rows.map(r=>r.player))].sort(),formula_version:VERSION,fact_check_status:'Verified',generation_time:new Date(Date.UTC(2026,0,1)+e*1000).toISOString().replace('.000Z','Z'),generation_clock:'fixed simulation clock'};
 return canonical(expected)===canonical(c)&&new Set(events.map(r=>r.id)).size===events.length;
 }catch{return false;}
}
const words={en:{pressing:['Pressure actions increased','More pressure actions suggest greater defensive activity; this is a proxy.'],flank:['Passes shifted toward the flanks','A greater flank share suggests wider passing emphasis, not proven spatial superiority.'],fatigue:['Recorded recovery slowed','Longer recovery is consistent with the scripted fatigue phase; causation is not inferred.']},zh:{pressing:['压迫动作增加','更多压迫动作提示防守活动增强；这只是代理指标。'],flank:['传球更多转向边路','边路传球占比增加提示更重视边路，并不证明空间优势。'],fatigue:['记录的回收速度变慢','回收用时增加符合预设疲劳阶段；不推断因果关系。']}};
function render(c,events,teams,density='Fan',lang='en',now=5400){
 if(!validate(c,events,teams,now))return {status:'Needs review',label:LABEL,what:'Claim held for review.',why:'Evidence validation failed. No unsupported claim is shown.',evidence:'Template fallback; publication disabled.'};
 const [title,why]=words[lang][c.kind],comp=c.comparison,unit={pressing:'actions/min',flank:'%',fatigue:'seconds'}[c.kind];
 let what=title+': '+comp.first_half+' → '+comp.second_half+' '+unit+'.';
 if(density==='Analyst')what+=' '+comp.field+'; first half → second half of this evidence window.';
 return {status:'Verified',label:LABEL,what,why:density==='Broadcast'?(lang==='en'?'Directional reading of synthetic events.':'仅为合成事件的方向性解读。'):why,evidence:{event_ids:c.event_ids,window_start:c.window_start,window_end:c.window_end,formula_version:VERSION}};
}
function freeze(events,time,teams){
 if(time<600)throw Error('Replay at least ten minutes first.');
 const row=events.find(e=>e.time===time);if(!row)throw Error('Snapshot must match an event.');
 return JSON.parse(JSON.stringify({time,state:row.state,event_ids:slice(events,time-600,time).map(e=>e.id),baseline:metrics(events,time-600,time,teams),formula_version:VERSION}));
}
function scenario(snapshot,press,flank){
 if(!Number.isFinite(press)||press< -20||press>20||!Number.isFinite(flank)||flank< -20||flank>20)throw Error('Invalid controls');
 const b=snapshot.baseline;
 return {label:LABEL+' — Directional scenario, not a prediction',horizon_minutes:10,baseline:{pressure_actions:round(b.pressing_proxy*10),flank_share_pct:b.flank_share_pct,recovery_seconds:b.recovery_seconds},scenario:{pressure_actions:round(b.pressing_proxy*10*(1+press/100)),flank_share_pct:round(Math.max(0,Math.min(100,b.flank_share_pct+flank))),recovery_seconds:round(b.recovery_seconds*(1+press/200))},assumptions:'Last ten minutes held constant for the next ten. Pressure scales linearly; flank adjustment is percentage points; recovery cost changes by half the pressure percentage. Independent controls; no score, probability or causal forecast.',event_ids:snapshot.event_ids,window_start:snapshot.time-600,window_end:snapshot.time,formula_version:'scenario-v1.0'};
}
function decide(queue,claim,action,events,teams,now){
 if(queue[claim.id]!=='Draft'||!['Approved','Rejected'].includes(action))return false;
 if(action==='Approved'&&!validate(claim,events,teams,now))return false;
 queue[claim.id]=action; return true;
}
function broadcast(claims,queue,events,teams,now){return claims.filter(c=>queue[c.id]==='Approved'&&validate(c,events,teams,now));}
root.MatchEngine={metrics,validate,render,freeze,scenario,decide,broadcast,canonical};
})(typeof window==='undefined'?globalThis:window);
