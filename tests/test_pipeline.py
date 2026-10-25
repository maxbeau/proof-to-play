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

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = p.build()
        cls.events = cls.bundle['events']

    def test_seed_byte_identical(self):
        self.assertEqual(p.serialized(p.build()), p.serialized(p.build()))

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
                cap = 1.35 if 75*60 <= current['time'] <= 80*60 else p.PLAYER_STEP_CAP
                self.assertLessEqual(distance, cap, f'{current["id"]}, player {player}: {distance}m/5s')

    def test_ball_travel_cap_and_persistent_pass_shot_targets(self):
        for seed in [p.SEED, p.SEED+1, 42]:
            events = p.generate(seed)
            for previous, current in zip(events, events[1:]):
                self.assertLessEqual(math.dist(previous['positions'][:2], current['positions'][:2]), p.BALL_STEP_CAP)
        # A new unrelated event must not replace an in-flight pass/shot destination.
        for kind in ['pass', 'shot']:
            events = copy.deepcopy(self.events[:4])
            events[0].update(event_type=kind, team=p.TEAMS[0], player=p.ROSTERS[p.TEAMS[0]][0])
            for event in events[1:]:
                event.update(event_type='recovery', team=p.TEAMS[1], player=p.ROSTERS[p.TEAMS[1]][0])
            p.position_samples(events, p.SEED)
            first = events[0]['positions']
            target = first[10:12] if kind == 'pass' else [51, 0]
            distances = [math.dist(e['positions'][:2], target) for e in events]
            self.assertTrue(all(b < a for a, b in zip(distances, distances[1:])), distances)

    def test_player_smoothness_and_field_coverage(self):
        for seed in [p.SEED, p.SEED+1, 42]:
            events = p.generate(seed)
            for i in range(2, 46, 2):
                vectors = [(b['positions'][i]-a['positions'][i], b['positions'][i+1]-a['positions'][i+1])
                           for a, b in zip(events, events[1:])]
                lengths = [math.hypot(*v) for v in vectors]
                self.assertLess(sum(lengths)/len(lengths), 1.5)
                # Ignore <0.2m quantization jitter; reversal means a turn >120 degrees.
                turns = [sum(x*y for x, y in zip(a, b))/(la*lb)
                         for a, b, la, lb in zip(vectors, vectors[1:], lengths, lengths[1:]) if min(la, lb) >= .2]
                self.assertGreater(len(turns), len(vectors)*.5)
                self.assertLess(sum(c < -.5 for c in turns)/len(turns), .05)
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
            bundle = p.build(seed)
            for event in bundle['events']:
                del event['positions']
            self.assertEqual(hashlib.sha256(p.serialized(bundle).encode()).hexdigest(), digest)

    def test_positions_change_with_seed_and_default_regeneration_is_identical(self):
        alternate = p.build(p.SEED+1)
        self.assertNotEqual([e['positions'] for e in self.events], [e['positions'] for e in alternate['events']])
        files = ['match.json', 'match.js', 'events.jsonl']
        expected = {name: (ROOT/'data'/name).read_bytes() for name in files}
        subprocess.run([sys.executable, str(ROOT/'pipeline.py')], cwd=ROOT, check=True, capture_output=True, text=True)
        for name in files:
            actual = (ROOT/'data'/name).read_bytes()
            self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(expected[name]).digest(), name)

    def test_seed_changes_events(self):
        self.assertNotEqual(p.generate(), p.generate(p.SEED+1))

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
