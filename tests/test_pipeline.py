import copy
import json
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

if __name__=='__main__':unittest.main()
