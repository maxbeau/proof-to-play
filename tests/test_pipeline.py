import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline as p
from movement_metrics import measure, roles

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = {seed: [] for seed in (p.SEED, p.SEED+1, 42)}
        cls.bundles = {seed: p.build(seed, cls.traces[seed]) for seed in cls.traces}
        cls.bundle = cls.bundles[p.SEED]
        cls.events = cls.bundle['events']
        cls.measurements = {seed: measure(bundle['events']) for seed, bundle in cls.bundles.items()}
        cls.before = json.loads((ROOT/'tests/unified_movement_before.json').read_text())['metrics']

    def test_role_attributes_and_seeded_variation(self):
        self.assertEqual(p.PLAYER_ROLES, roles())
        attrs = p.player_attributes(p.SEED)
        self.assertEqual(attrs, p.player_attributes(p.SEED))
        self.assertNotEqual(attrs, p.player_attributes(p.SEED+1))
        self.assertEqual(len({tuple(a.values()) for a in p.ROLE_ATTRIBUTES.values()}), 5)
        for role in set(roles()):
            members = [a for a in attrs if a['role'] == role]
            self.assertEqual(len({a['maxSpeed'] for a in members}), len(members))
            for a in members:
                for key, base in p.ROLE_ATTRIBUTES[role].items():
                    self.assertTrue(.94*base <= a[key] <= 1.06*base)
        self.assertGreater(p.ROLE_ATTRIBUTES['forward']['maxSpeed'], p.ROLE_ATTRIBUTES['defender']['maxSpeed'])
        self.assertLess(p.ROLE_ATTRIBUTES['winger']['response'], p.ROLE_ATTRIBUTES['defender']['response'])

    def test_role_mean_speed_and_match_distance(self):
        # Endpoint distance, not hidden substep path length. The stored interval
        # duration is 5,395 seconds, rather than rounding it up to 90 minutes.
        ranges = {'goalkeeper':(.7,1.0), 'defender':(1.6,1.9),
                  'midfielder':(1.9,2.2), 'forward':(1.8,2.2), 'winger':(1.8,2.2)}
        for seed, stats in self.measurements.items():
            for role,(low,high) in ranges.items():
                with self.subTest(seed=seed,role=role):
                    self.assertTrue(low <= stats['role_mean_speed'][role] <= high, stats['role_mean_speed'])
                    self.assertTrue(low*5.395 <= stats['role_distance_km'][role] <= high*5.395)
                    values = [s for s,r in zip(stats['player_mean_speed'], roles()) if r == role]
                    self.assertGreater(max(values)-min(values), .001)
                    self.assertLess(self.before['role_mean_speed'][role],low)
            self.assertGreater(max(stats['player_mean_speed'])-min(stats['player_mean_speed']), .8)
            self.assertTrue(8 <= max(max(row['peak_speeds']) for row in self.traces[seed]) <= 10.1)

    def test_heading_diversity(self):
        for seed, stats in self.measurements.items():
            self.assertLessEqual(stats['heading_max_dominant_bin'], .5, seed)
            self.assertLess(stats['heading_mean_dominant_bin'], .4, seed)
            self.assertGreater(stats['heading_mean_circular_spread'], .45, seed)

    def test_separation_and_formation_preserved(self):
        for seed, stats in self.measurements.items():
            self.assertGreaterEqual(stats['minimum_separation'], 1.5, seed)
            self.assertGreaterEqual(stats['minimum_replay_separation'], 1.5, seed)
            self.assertGreater(stats['minimum_team_rms_spread'], 16, seed)
            for event in self.bundles[seed]['events']:
                for i in range(22):
                    x,y = event['positions'][2+2*i:4+2*i]
                    xmin,xmax,ymin,ymax = p.role_zone(i)
                    self.assertTrue(xmin-.05 <= x <= xmax+.05)
                    self.assertTrue(ymin-.05 <= y <= ymax+.05)
                for offset in (2,24):
                    xs = event['positions'][offset:offset+22:2]
                    ys = event['positions'][offset+1:offset+22:2]
                    self.assertLess(abs(sum(ys)/11), 9)
                    self.assertGreater(max(xs)-min(xs), 35)
                    self.assertGreater(max(ys)-min(ys), 30)

    def test_ball_attaches_to_event_actor_and_nearest_player(self):
        for seed, bundle in self.bundles.items():
            for event in bundle['events']:
                i = 2+2*p.POSITION_PLAYERS.index(event['player'])
                self.assertLessEqual(math.dist(event['positions'][:2],event['positions'][i:i+2]),1, (seed,event['id']))
            self.assertLessEqual(self.measurements[seed]['ball_nearest_mean'],1)
        self.assertGreater(self.before['ball_actor_mean'],30)
        self.assertGreater(self.before['ball_nearest_mean'],5)

    def test_team_shape_progresses_and_runs_persist(self):
        for seed,bundle in self.bundles.items():
            events=bundle['events']
            for offset in (2,24):
                centers=[sum(e['positions'][offset:offset+22:2])/11 for e in events]
                self.assertGreater(max(centers)-min(centers),20,seed)
            for i,role in enumerate(roles()):
                k=2+i*2
                xs=[e['positions'][k] for e in events]
                self.assertGreater(max(xs)-min(xs),10 if role=='goalkeeper' else 40,(seed,i))
                dx=[b-a for a,b in zip(xs,xs[1:])]
                sustained=sum(all(v>1 for v in dx[j:j+3]) or all(v < -1 for v in dx[j:j+3]) for j in range(len(dx)-2))
                self.assertGreater(sustained,20,(seed,i))

    def test_vehicle_acceleration_arrival_and_curved_motion(self):
        a = p.player_attributes(p.SEED)[9]
        position, velocity = [0.,0.], [0.,0.]
        speeds = []
        for _ in range(100):
            old = velocity.copy()
            position,velocity = p.vehicle_step(position, velocity, [100.,0.], a)
            self.assertLessEqual(math.dist(old,velocity), a['maxForce']*p.STEERING_DT+1e-10)
            self.assertLessEqual(math.hypot(*velocity), a['maxSpeed']+1e-10)
            speeds.append(math.hypot(*velocity))
        self.assertLess(speeds[0], speeds[20])
        # Turning retains forward inertia; a changed target cannot reset velocity.
        old_position = position.copy()
        position,velocity = p.vehicle_step(position, velocity, [0.,a['maxSpeed']], a)
        self.assertGreater(position[0], old_position[0])
        self.assertGreater(position[1], old_position[1])
        position,velocity = [0.,0.],[0.,0.]
        for _ in range(600):
            desired = p.limit_vector((3-position[0])/a['response'], -position[1]/a['response'], a['maxSpeed'])
            position,velocity = p.vehicle_step(position,velocity,desired,a)
        self.assertLess(math.dist(position,[3,0]), .01)
        self.assertLess(math.hypot(*velocity), .01)

    def test_behaviour_assignments_persist_and_limit_pressers(self):
        for trace in self.traces.values():
            previous = None
            for row in trace:
                modes = row['modes']
                self.assertTrue(1 <= modes.count('presser') <= 2)
                self.assertEqual(modes.count('marker'), 2)
                self.assertGreaterEqual(modes.count('supporter'), 2)
                self.assertGreaterEqual(modes.count('runner'), 3)
                self.assertEqual(modes[0], 'holder')
                self.assertEqual(modes[11], 'holder')
                if previous and row['assigned_at'] != previous['assigned_at']:
                    self.assertTrue(row['phase'] != previous['phase'] or row['possession'] != previous['possession'])
                    if row['phase'] == previous['phase']:
                        self.assertGreaterEqual(row['assigned_at']-previous['assigned_at'], 30)
                if row['assignment_positions'] is not None:
                    xy, ball = row['assignment_positions'], row['ball']
                    candidates = range((1-row['possession'])*11+1,(1-row['possession'])*11+11)
                    nearest = sorted(candidates,key=lambda i:(math.dist(xy[i],ball),i))[:modes.count('presser')]
                    self.assertEqual(set(nearest), {i for i,m in enumerate(modes) if m == 'presser'})
                previous = row

    def test_seed_byte_identical(self):
        trace = []
        self.assertEqual(p.serialized(self.bundle), p.serialized(p.build(diagnostics=trace)))
        self.assertEqual(p.serialized(p.player_modes(self.traces[p.SEED])), p.serialized(p.player_modes(trace)))

    def test_player_modes_cover_every_generated_sample_and_player(self):
        known = {'holder', 'presser', 'runner', 'supporter', 'marker'}
        for seed, trace in self.traces.items():
            data = p.player_modes(trace, seed)
            self.assertEqual(data['position_players'], p.POSITION_PLAYERS)
            self.assertEqual(len(data['samples']), 1080)
            self.assertEqual([row['time'] for row in data['samples']], list(range(5, 5401, 5)))
            for row, diagnostic in zip(data['samples'], trace):
                self.assertEqual(len(row['modes']), 22)
                self.assertTrue(set(row['modes']) <= known)
                self.assertEqual(row['modes'], diagnostic['modes'])
            self.assertEqual({mode for row in data['samples'] for mode in row['modes']}, known)

    def test_player_modes_attributes_and_initial_positions_match_generator(self):
        for seed, trace in self.traces.items():
            data = p.player_modes(trace, seed)
            self.assertEqual(data['seed'], seed)
            self.assertEqual(data['initial'], {'time': 0, 'positions': [list(xy) for team in p.TEAMS for xy in p.FORMATIONS[team]]})
            self.assertEqual(len(data['players']), 22)
            for i, (player, attrs) in enumerate(zip(data['players'], p.player_attributes(seed))):
                self.assertEqual(player['id'], p.POSITION_PLAYERS[i])
                self.assertEqual(player['team'], p.TEAMS[i//11])
                for key in ('role', 'weights', 'maxSpeed', 'maxForce', 'response', 'stamina'):
                    self.assertEqual(player[key], attrs[key])

    def test_player_modes_local_files_and_classic_script_parity(self):
        modes = p.serialized(p.player_modes(self.traces[p.SEED]))
        self.assertEqual((ROOT/'data/player-modes.json').read_text(), modes)
        self.assertEqual((ROOT/'data/player-modes.js').read_text(), 'window.PLAYER_MODES = '+modes.rstrip()+';\n')
        html = (ROOT/'index.html').read_text()
        self.assertIn('src="data/player-modes.js"', html)
        self.assertIn('src="pitch-identification.js"', html)
        self.assertLess(html.index('src="data/player-modes.js"'), html.index('src="pitch.js"'))
        helper = (ROOT/'pitch-identification.js').read_text()
        for external in ('fetch(', 'XMLHttpRequest', 'innerHTML'):
            self.assertNotIn(external, helper)

    def test_display_change_preserves_e172f6a_artifacts_byte_for_byte(self):
        # Full files, including positions and ball flights, captured at e172f6a.
        expected = {
            'match.json': 'f7bb1e77d69119d87e360c0e696a8a17439388d0af40402e0d6155ec4379e042',
            'match.js': '03a5faab76624e9ab6bd499bdf28d2c7fe7e16f850ff624ba31d3d4cd7dd4c2c',
            'events.jsonl': '03d81a8d4d6ebfdb6ced2202662bf403334b87c26a29ddc934134c20bb617424',
            'ball-flights.json': '656da64ea65d9a1c90adf26bd14440ec1bde5d4a9083ee5af0192579fa851701',
            'ball-flights.js': '8dcf4a6e799a537469c9269bdab71c4d7630609c134369483998b2a9973f6988',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/'data'/name).read_bytes()).hexdigest(), digest, name)

    def test_positions_bounds_and_player_speed_cap(self):
        for event in self.events:
            self.assertEqual(len(event['positions']), 46)
            self.assertEqual(event['position_label'], p.POSITION_LABEL)
            self.assertTrue(all(value == round(value, 1) for value in event['positions']))
            coords = [event['positions'][0:2]] + [event['positions'][2+i*2:4+i*2] for i in range(22)]
            for x, y in coords:
                self.assertTrue(-52.5 <= x <= 52.5)
                self.assertTrue(-34 <= y <= 34)
        for previous, current in zip(self.events, self.events[1:]):
            for player in range(22):
                i = 2 + player*2
                distance = math.hypot(current['positions'][i]-previous['positions'][i], current['positions'][i+1]-previous['positions'][i+1])
                a = p.player_attributes(p.SEED)[player]
                cap = a['maxSpeed']*5 + p.ROUNDING_MARGIN
                self.assertLessEqual(distance, cap, f'{current["id"]}, player {player}: {distance}m/5s')

    def test_pass_ball_starts_on_actor_receiver_segment(self):
        # No recipient is stored. Only consecutive same-team actors are an
        # unambiguous candidate segment; other observations require a handoff.
        for seed,bundle in self.bundles.items():
            for current,nxt in zip(bundle['events'],bundle['events'][1:]):
                if current['event_type'] != 'pass' or current['team'] != nxt['team']:
                    continue
                a=2+2*p.POSITION_PLAYERS.index(current['player'])
                b=2+2*p.POSITION_PLAYERS.index(nxt['player'])
                origin=current['positions'][a:a+2];target=nxt['positions'][b:b+2]
                ball=current['positions'][:2]
                dx,dy=target[0]-origin[0],target[1]-origin[1]
                q=dx*dx+dy*dy
                t=max(0,min(1,((ball[0]-origin[0])*dx+(ball[1]-origin[1])*dy)/q)) if q else 0
                self.assertLessEqual(math.dist(ball,[origin[0]+t*dx,origin[1]+t*dy]),1,(seed,current['id']))

    def test_pass_shot_replay_flight_speed(self):
        # A 20 m pass flying for 1 s then held for 4 s is 20 m/s, not 4 m/s.
        # Endpoint / 5 s cannot measure that phase. Measure EVERY active flight
        # leg and its actual duration; preserve 12–25 m/s and the 5 s deadline.
        for seed,bundle in self.bundles.items():
            plans=p.ball_flights(bundle['events'],seed)['plans']
            for a,b in zip(bundle['events'],bundle['events'][1:]):
                plan=plans[a['id']];segments=plan['segments']
                self.assertEqual(plan['seconds'],b['time']-a['time'])
                self.assertEqual(plan['receiver'],b['player'])
                self.assertEqual(segments[0]['origin'],a['positions'][:2])
                self.assertEqual(segments[0]['start'],0)
                self.assertEqual(segments[-1]['target'],b['positions'][:2])
                self.assertEqual(segments[-1]['end'],plan['seconds'])
                self.assertEqual(segments[-1]['phase'],'held')
                for previous,current in zip(segments,segments[1:]):
                    self.assertEqual(previous['target'],current['origin'])
                    self.assertEqual(previous['end'],current['start'])
                for leg in segments:
                    self.assertTrue(0 <= leg['start'] <= leg['end'] <= plan['seconds'])
                    if leg['phase']=='waiting':
                        self.assertEqual(leg['origin'],leg['target'])
                        continue
                    if leg['phase']=='held':
                        continue
                    self.assertGreater(leg['end'],leg['start'])
                    speed=math.dist(leg['origin'],leg['target'])/(leg['end']-leg['start'])
                    self.assertTrue(12 <= round(speed,8) <= 25,(seed,a['id'],speed))
                if a['event_type']=='pass' and math.dist(a['positions'][:2],b['positions'][:2])>1:
                    self.assertTrue(any(s['phase']=='pass' for s in segments),(seed,a['id']))
                if a['event_type']=='shot':
                    self.assertEqual(segments[0]['phase'],'shot')
                    self.assertEqual(segments[0]['target'],[52.5 if a['team']==p.TEAMS[0] else -52.5,0])
                    self.assertEqual(segments[1]['phase'],'rebound')
                # Once received, ball and player share the SAME replay chord.
                held=segments[-1];k=2+2*p.POSITION_PLAYERS.index(b['player'])
                fraction=held['start']/plan['seconds']
                receiver=[a['positions'][k+j]+(b['positions'][k+j]-a['positions'][k+j])*fraction for j in (0,1)]
                self.assertLess(math.dist(held['origin'],receiver),1e-8)

    def test_shot_goal_and_next_actor_fit_physical_budget(self):
        # Fundamental acceptance constraint: outgoing shot + next event touch
        # must fit without a reset or a >25m/s handoff. Do not relax this test.
        impossible=[]
        for seed,bundle in self.bundles.items():
            for a,b in zip(bundle['events'],bundle['events'][1:]):
                if a['event_type']!='shot':
                    continue
                goal=[52.5 if a['team']==p.TEAMS[0] else -52.5,0]
                length=math.dist(a['positions'][:2],goal)+math.dist(goal,b['positions'][:2])
                if length > 25*(b['time']-a['time']):
                    impossible.append((seed,a['id'],round(length,1)))
        self.assertFalse(impossible,f'{len(impossible)} shot/next-actor paths exceed 125 m; first {impossible[:5]}')

    def test_player_smoothness_and_field_coverage(self):
        for seed in [p.SEED, p.SEED+1, 42]:
            events = self.bundles[seed]['events']
            for i in range(2, 46, 2):
                vectors = [(b['positions'][i]-a['positions'][i], b['positions'][i+1]-a['positions'][i+1])
                           for a, b in zip(events, events[1:])]
                lengths = [math.hypot(*v) for v in vectors]
                self.assertLess(sum(lengths)/len(lengths), p.player_attributes(seed)[(i-2)//2]['maxSpeed']*5)
                # Ignore <0.2m quantization jitter; reversal means a turn >120 degrees.
                turns = [sum(x*y for x, y in zip(a, b))/(la*lb)
                         for a, b, la, lb in zip(vectors, vectors[1:], lengths, lengths[1:]) if min(la, lb) >= .2]
                self.assertGreater(len(turns), len(vectors)*.5)
                self.assertLess(sum(c < -.5 for c in turns)/len(turns), .10)
                xs = [e['positions'][i] for e in events]
                # Goalkeepers may cover less ground; outfield players must keep roaming.
                self.assertGreater(max(xs)-min(xs), 4 if i in (2, 24) else 10)

    def test_nonposition_data_unchanged(self):
        # Baselines captured before the continuity fix: includes metrics/evidence/templates.
        expected = {
            p.SEED: '18327c7466cb94dff22fb93cfae8eee1d63450d07f4d3c7eba7154fe3912acb7',
            p.SEED+1: '2a269442c9a59476664161573cf03631ba8483244105e934b8ea5ad860aa3915',
            42: 'f022d78126e4e45ff8087d6577652da3bf813d7ed5a820c54f3322527ae50db4'
        }
        for seed, digest in expected.items():
            bundle = copy.deepcopy(self.bundles[seed])
            for event in bundle['events']:
                del event['positions']
            self.assertEqual(hashlib.sha256(p.serialized(bundle).encode()).hexdigest(), digest)

    def test_positions_change_with_seed_and_default_regeneration_is_identical(self):
        alternate = self.bundles[p.SEED+1]
        self.assertNotEqual([e['positions'] for e in self.events], [e['positions'] for e in alternate['events']])
        files = ['match.json', 'match.js', 'events.jsonl', 'ball-flights.json', 'ball-flights.js', 'player-modes.json', 'player-modes.js']
        expected = {name: (ROOT/'data'/name).read_bytes() for name in files}
        subprocess.run([sys.executable, str(ROOT/'pipeline.py')], cwd=ROOT, check=True, capture_output=True, text=True)
        for name in files:
            actual = (ROOT/'data'/name).read_bytes()
            self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(expected[name]).digest(), name)

    def test_seed_changes_events(self):
        self.assertNotEqual(self.events, self.bundles[p.SEED+1]["events"])

    def test_stored_event_metric_recomputation(self):
        stored = [json.loads(line) for line in (ROOT/'data/events.jsonl').read_text().splitlines()]
        bundle = json.loads((ROOT/'data/match.json').read_text())
        self.assertEqual(stored, bundle['events'])
        self.assertEqual(p.metrics(stored, 0, 5400), bundle['metrics'])
        for claim in bundle['insights']:
            self.assertEqual(p.metrics(stored, claim['window_start'], claim['window_end']), claim['metric_value'])
            self.assertTrue(p.validate(claim, stored))

    def test_full_pipeline_artifacts_current(self):
        self.assertEqual((ROOT/'data/match.json').read_text(), p.serialized(self.bundle))
        self.assertEqual((ROOT/'data/match.js').read_text(), 'window.MATCH = '+p.serialized(self.bundle).rstrip()+';'+chr(10))
        flights=p.serialized(p.ball_flights(self.events))
        self.assertEqual((ROOT/'data/ball-flights.json').read_text(),flights)
        self.assertEqual((ROOT/'data/ball-flights.js').read_text(),'window.BALL_FLIGHTS = '+flights.rstrip()+';'+chr(10))

    def test_plausible_magnitudes(self):
        m = self.bundle['metrics']
        self.assertTrue(600 <= m['pass_count'] <= 1200)
        self.assertTrue(10 <= m['shot_count'] <= 40)
        self.assertEqual(self.events[-1]['time'], 5400)
        self.assertEqual(len({e['id'] for e in self.events}), len(self.events))

    def test_three_window_turning_points(self):
        self.assertEqual([(c['kind'], c['window_end']) for c in self.bundle['insights']], [('pressing',1800),('flank',3300),('fatigue',4800)])
        flat = copy.deepcopy(self.events)
        for e in flat:
            if e['event_type']=='pressure': e['event_type']='pass'
        self.assertFalse(p.validate(self.bundle['insights'][0], flat))

    def test_every_template_carries_evidence(self):
        for c in self.bundle['insights']:
            for language in ['en','zh']:
                for density in ['Fan','Analyst','Broadcast']:
                    out = p.render(c,self.events,density,language)
                    self.assertEqual(out['status'],'Verified')
                    self.assertEqual(out['evidence']['event_ids'],c['event_ids'])
                    self.assertEqual(out['evidence']['window_start'],c['window_start'])
                    self.assertEqual(out['evidence']['window_end'],c['window_end'])
                    self.assertEqual(out['evidence']['formula_version'],p.VERSION)

    def test_broken_claim_held(self):
        out = p.render(self.bundle['broken_claim'],self.events)
        self.assertEqual(out['status'],'Needs review')
        self.assertNotIn('999', json.dumps(out))
        self.assertNotIn('MISSING', json.dumps(out))

    def test_gate_rejects_each_tamper(self):
        for field,value in [('event_ids',['MISSING']),('teams',['Invented outsider']),('players',['OUTSIDE']),('window_end',2100),('formula_version','unknown'),('generation_time','wrong'),('extra_text','untrusted prose')]:
            c=copy.deepcopy(self.bundle['insights'][0]); c[field]=value
            self.assertFalse(p.validate(c,self.events),field)
        c=copy.deepcopy(self.bundle['insights'][0]); c['metric_value']['tempo']=99
        self.assertFalse(p.validate(c,self.events))
        c=copy.deepcopy(self.bundle['insights'][0]); c['event_ids'][0]=self.events[-1]['id']
        self.assertFalse(p.validate(c,self.events))

    def test_fictional_entity_allowlist_grep(self):
        # Positive allowlist is stricter for generated entity fields than a finite real-name denylist.
        pattern=r'"(?:team|player|possession_team)":"[^"]+"'
        result=subprocess.run(['grep','-Eo',pattern.replace('(?:','('),str(ROOT/'data/events.jsonl')],capture_output=True,text=True,check=True)
        allowed=set(p.TEAMS)|{n for roster in p.ROSTERS.values() for n in roster}
        self.assertEqual(len(result.stdout.splitlines()),len(self.events)*3)
        for line in result.stdout.splitlines():
            self.assertIn(line.split(':',1)[1].strip('"'),allowed)
        for c in self.bundle['insights']:
            self.assertTrue(set(c['teams']+c['players'])<=allowed)

    def test_state_score_recomputed(self):
        score=dict.fromkeys(p.TEAMS,0)
        for e in self.events:
            if e['outcome']=='goal':score[e['team']]+=1
            self.assertEqual(e['state']['score'],score)
            self.assertEqual(e['label'],p.LABEL)

    def test_static_local_assets(self):
        from html.parser import HTMLParser
        class Assets(HTMLParser):
            paths=[]
            def handle_starttag(self,tag,attrs):
                for k,v in attrs:
                    if k in ('src','href'):self.paths.append(v)
        parser=Assets();parser.feed((ROOT/'index.html').read_text())
        for path in parser.paths:
            self.assertNotIn('://',path)
            self.assertTrue((ROOT/path).is_file())
        for file in ['app.js','engine.js']:
            source=(ROOT/file).read_text()
            self.assertNotIn('fetch(',source)
            self.assertNotIn('XMLHttpRequest',source)
            self.assertNotIn('innerHTML',source)

    def test_pitch_modules_and_import_map_are_local(self):
        html = (ROOT/'index.html').read_text()
        self.assertTrue((ROOT/'pitch.js').is_file())
        self.assertTrue((ROOT/'vendor/three.module.js').is_file())
        self.assertTrue((ROOT/'vendor/OrbitControls.js').is_file())
        self.assertIn('"three":"./vendor/three.module.js"', html)
        self.assertIn('"OrbitControls":"./vendor/OrbitControls.js"', html)
        self.assertNotIn('://', html)

if __name__=='__main__':unittest.main()
