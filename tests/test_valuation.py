"""Reuse the established suite's three seed bundles; never change legacy checks."""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
import test_pipeline

ROOT = Path(__file__).resolve().parents[1]

class ValuationAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        existing = test_pipeline.Acceptance
        if not hasattr(existing, 'bundles'):
            existing.setUpClass()
        cls.inputs = [dict(match=bundle, modes=test_pipeline.p.player_modes(existing.traces[seed], seed))
                      for seed, bundle in existing.bundles.items()]
        program = r'''
const fs=require('node:fs'), crypto=require('node:crypto'), V=require('./pitch-valuation.js');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(input.map(({match,modes})=>{
 const before=JSON.stringify([match,modes]), a=V.serialized(V.build(match,modes));
 const data=JSON.parse(a); let valid=true, count=0, low=1, high=0;
 for(const sample of data.samples) for(const [i,row] of sample.players.entries()) {
  const d=V.decompose(row.slice(0,5),sample.modes[i]);
  if(!d || d.value<0 || d.value>1 || modes.players[row[5]].team===modes.players[i].team) valid=false;
  for(const score of row.slice(0,5)) {low=Math.min(low,score);high=Math.max(high,score);count++;}
 }
 return {seed:match.seed,hash:crypto.createHash('sha256').update(a).digest('hex'),
  repeat:a===V.serialized(V.build(match,modes)),unchanged:before===JSON.stringify([match,modes]),
  valid,count,low,high};
})));
'''
        def run():
            return json.loads(subprocess.run(['node', '-e', program], cwd=ROOT,
                input=json.dumps(cls.inputs), capture_output=True, text=True, check=True).stdout)
        cls.first, cls.second = run(), run()

    def test_all_existing_seeds_regenerate_byte_identically_across_processes(self):
        self.assertEqual(self.first, self.second)
        self.assertEqual({r['seed'] for r in self.first}, {20261024, 20261025, 42})
        self.assertTrue(all(r['repeat'] and r['unchanged'] for r in self.first))
        self.assertEqual(len({r['hash'] for r in self.first}), 3)

    def test_all_existing_seeds_have_complete_bounded_scores_and_decomposition(self):
        for row in self.first:
            self.assertTrue(row['valid'], row)
            self.assertEqual(row['count'], 1080 * 22 * 5)
            self.assertGreaterEqual(row['low'], 0)
            self.assertLessEqual(row['high'], 1)

    def test_default_sidecar_matches_regenerated_seed(self):
        self.assertEqual(self.first[0]['hash'], hashlib.sha256((ROOT/'data/player-values.json').read_bytes()).hexdigest())

    def test_player_modes_artifacts_remain_at_head_baseline(self):
        expected = {
            'player-modes.json': 'e61a176c26a1e560e47ef65523d70353d4dfbbe69a827b02b9945457e51a55c6',
            'player-modes.js': '0f357cc1c576130ea66a45545192df21adb9cc8802963a61cd88a82826e8dd90',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/'data'/name).read_bytes()).hexdigest(), digest)
