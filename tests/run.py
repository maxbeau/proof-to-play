"""Run local acceptance checks, including steering; derive totals from discovery.

Node is only needed for JS verification. No fixed test total is maintained.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import re
import json
import math
import unittest
root=Path(__file__).resolve().parents[1]
if not shutil.which('node'):
    sys.exit('FAIL: Node is required for browser-engine/UI tests (not for demo or generation).')
suite = unittest.defaultTestLoader.discover(str(root/'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
browser = subprocess.run(['node','tests/browser.test.js'], cwd=root, capture_output=True, text=True)
print(browser.stdout, end='')
print(browser.stderr, end='', file=sys.stderr)
js_passed = len(re.findall(r'^PASS ', browser.stdout, re.MULTILINE))
failed = len(result.failures) + len(result.errors) + int(browser.returncode != 0)
passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) + js_passed
print(f'Acceptance suite: {passed} passed, {failed} failed, {len(result.skipped)} skipped.')
if result.wasSuccessful() and browser.returncode == 0:
    # Report the very bundles verified above; do not generate a different run
    # for the README figures. Keep totals derived from test discovery.
    from test_pipeline import Acceptance
    import pipeline as p
    path=root/'tests/unified_movement_after.json'
    previous=json.loads(path.read_text()) if path.exists() else {}
    report={'description':'Verified synthetic/schematic movement and timed flight measurements.',
            'partial_repair_baseline':previous.get('partial_repair_baseline',previous.get('metrics')),
            'metrics':Acceptance.measurements[p.SEED],
            'verification':{'passed':passed,'failed':failed,'skipped':len(result.skipped)},'seeds':{}}
    for seed,bundle in Acceptance.bundles.items():
        events=bundle['events'];reversals=[];shots=[];speeds=[]
        for i,player in enumerate(p.POSITION_PLAYERS):
            k=2+2*i
            vectors=[(b['positions'][k]-a['positions'][k],b['positions'][k+1]-a['positions'][k+1]) for a,b in zip(events,events[1:])]
            lengths=[math.hypot(*v) for v in vectors]
            turns=[sum(x*y for x,y in zip(a,b))/(la*lb) for a,b,la,lb in zip(vectors,vectors[1:],lengths,lengths[1:]) if min(la,lb)>=.2]
            reversals.append({'player':player,'reversals':sum(t<-.5 for t in turns),'turns':len(turns),'fraction':sum(t<-.5 for t in turns)/len(turns)})
        flights=p.ball_flights(events,seed)['plans']
        for a,b in zip(events,events[1:]):
            if a['event_type']=='shot':
                goal=[52.5 if a['team']==p.TEAMS[0] else -52.5,0]
                shots.append({'event':a['id'],'metres':math.dist(a['positions'][:2],goal)+math.dist(goal,b['positions'][:2])})
            if a['event_type'] in ('pass','shot'):
                for leg in flights[a['id']]['segments']:
                    if leg['phase'] not in ('held','waiting'):
                        speeds.append(math.dist(leg['origin'],leg['target'])/(leg['end']-leg['start']))
        report['seeds'][str(seed)]={'metrics':Acceptance.measurements[seed],'reversals':reversals,'shots':shots,
                                  'flight_legs':len(speeds),'flight_speed_min':min(speeds),'flight_speed_max':max(speeds)}
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
sys.exit(0 if result.wasSuccessful() and browser.returncode == 0 else 1)
