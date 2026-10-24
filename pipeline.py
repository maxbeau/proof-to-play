"""Synthetic / Simulated Match: offline deterministic pipeline."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random

SEED = 20261024
LABEL = 'Synthetic / Simulated Match'
VERSION = 'events-v1.0'
TEAMS = ['Aster Quills', 'Mica Lanterns']
ROSTERS = {t: [f'{p}-{i:02d}' for i in range(1, 12)] for t, p in zip(TEAMS, ['AQ', 'ML'])}
KINDS = {'pressing': ('pressing_proxy', 1), 'flank': ('flank_share_pct', 15), 'fatigue': ('recovery_seconds', 3)}

def stamp(seconds):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')

def generate(seed=SEED):
    rng = random.Random(seed)
    events, score = [], dict.fromkeys(TEAMS, 0)
    for block in range(18):
        pressures = 26 if block == 5 else 8
        shots = 2 if block % 2 == 0 else 1
        deck = ['pass'] * (54-pressures-shots) + ['pressure'] * pressures + ['shot'] * shots + ['recovery'] * 6
        rng.shuffle(deck)
        for kind in deck:
            t = (len(events)+1)*5
            team = rng.choice(TEAMS)
            player = rng.choice(ROSTERS[team])
            zone = rng.choice(['left', 'center', 'right'])
            if kind == 'pass':
                zone = ('left' if rng.random() < .9 else 'center') if block == 10 else rng.choice(['left', 'center', 'center', 'right'])
                outcome = 'complete' if rng.random() < .82 else 'lost'
            elif kind == 'pressure':
                outcome = 'regain' if rng.random() < .35 else 'bypassed'
            elif kind == 'shot':
                outcome = 'goal' if rng.random() < .09 else 'saved_or_wide'
                if outcome == 'goal':
                    score[team] += 1
            else:
                outcome = 'recovered'
            recovery = (rng.randint(11, 15) if block == 15 else rng.randint(3, 6)) if kind == 'recovery' else None
            events.append({'id': f'E{len(events)+1:04d}', 'time': t, 'team': team, 'player': player, 'zone': zone, 'event_type': kind, 'outcome': outcome, 'recovery_seconds': recovery, 'state': {'score': score.copy(), 'possession_team': team, 'elapsed_seconds': t}, 'label': LABEL})
    return events

def window(events, start, end):
    return [e for e in events if start < e['time'] <= end]

def rounded(n):
    return int(n*100+.5)/100

def metrics(events, start, end):
    rows = window(events, start, end)
    if end <= start or not rows:
        raise ValueError('Empty window')
    minutes = (end-start)/60
    passes = [e for e in rows if e['event_type'] == 'pass']
    recoveries = [e['recovery_seconds'] for e in rows if e['event_type'] == 'recovery']
    players = {}
    for e in passes:
        if e['outcome'] == 'complete':
            players[e['player']] = players.get(e['player'], 0)+1
    leaders = sorted(players.items(), key=lambda x: (-x[1], x[0]))[:3]
    return {'possession_pct': {t: rounded(100*sum(e['state']['possession_team'] == t for e in rows)/len(rows)) for t in TEAMS}, 'pressing_proxy': rounded(sum(e['event_type'] == 'pressure' for e in rows)/minutes), 'tempo': rounded(len(passes)/minutes), 'flank_share_pct': rounded(100*sum(e['zone'] != 'center' for e in passes)/len(passes)) if passes else 0, 'recovery_seconds': rounded(sum(recoveries)/len(recoveries)) if recoveries else 0, 'pass_count': len(passes), 'shot_count': sum(e['event_type'] == 'shot' for e in rows), 'key_players': [{'player': p, 'completed_passes': n} for p, n in leaders]}

def evidence(events, start, end, kind):
    if kind not in KINDS or start < 0 or end > events[-1]['time'] or end-start != 600:
        raise ValueError('Unsupported window')
    mid = (start+end)/2
    first, last = metrics(events, start, mid), metrics(events, mid, end)
    field, threshold = KINDS[kind]
    if last[field]-first[field] < threshold:
        raise ValueError('Threshold not met')
    rows = window(events, start, end)
    return {'id': f'{kind}-{end}', 'kind': kind, 'label': LABEL, 'event_ids': [e['id'] for e in rows], 'window_start': start, 'window_end': end, 'metric_value': metrics(events, start, end), 'comparison': {'field': field, 'first_half': first[field], 'second_half': last[field]}, 'teams': sorted(set(e['team'] for e in rows)), 'players': sorted(set(e['player'] for e in rows)), 'formula_version': VERSION, 'fact_check_status': 'Verified', 'generation_time': stamp(end), 'generation_clock': 'fixed simulation clock'}

def validate(claim, events):
    try:
        return claim == evidence(events, claim['window_start'], claim['window_end'], claim['kind'])
    except (KeyError, ValueError, TypeError, IndexError):
        return False

def render(claim, events, density='Fan', language='en'):
    if not validate(claim, events):
        return {'status': 'Needs review', 'label': LABEL, 'what': 'Claim held for review.', 'why': 'Evidence validation failed. No unsupported claim is shown.', 'evidence': 'Template fallback; publication disabled.'}
    if density not in ['Fan', 'Analyst', 'Broadcast'] or language not in ['en', 'zh']:
        raise ValueError('Unsupported template')
    words = {'en': {'pressing': ('Pressure actions increased', 'More pressure actions suggest greater defensive activity; this is a proxy.'), 'flank': ('Passes shifted toward the flanks', 'A greater flank share suggests wider passing emphasis, not proven spatial superiority.'), 'fatigue': ('Recorded recovery slowed', 'Longer recovery is consistent with the scripted fatigue phase; causation is not inferred.')}, 'zh': {'pressing': ('压迫动作增加', '更多压迫动作提示防守活动增强；这只是代理指标。'), 'flank': ('传球更多转向边路', '边路传球占比增加提示更重视边路，并不证明空间优势。'), 'fatigue': ('记录的回收速度变慢', '回收用时增加符合预设疲劳阶段；不推断因果关系。')}}
    title, why = words[language][claim['kind']]
    c = claim['comparison']
    unit = {'pressing': 'actions/min', 'flank': '%', 'fatigue': 'seconds'}[claim['kind']]
    what = f'{title}: {c["first_half"]} → {c["second_half"]} {unit}.'
    if density == 'Analyst':
        what += f' {c["field"]}; first half → second half of this evidence window.'
    elif density == 'Broadcast':
        why = 'Directional reading of synthetic events.' if language == 'en' else '仅为合成事件的方向性解读。'
    return {'status': 'Verified', 'label': LABEL, 'what': what, 'why': why, 'evidence': {'event_ids': claim['event_ids'], 'window_start': claim['window_start'], 'window_end': claim['window_end'], 'formula_version': VERSION}}

def build(seed=SEED):
    events, claims = generate(seed), []
    for end in range(600, 5401, 300):
        for kind in KINDS:
            try:
                claims.append(evidence(events, end-600, end, kind))
            except ValueError:
                pass
    broken = copy.deepcopy(claims[0])
    broken['id'] = 'deliberately-broken'
    broken['event_ids'][0] = 'MISSING'
    broken['comparison']['second_half'] = 999
    broken['fact_check_status'] = 'Needs review'
    return {'label': LABEL, 'seed': seed, 'formula_version': VERSION, 'teams': TEAMS, 'events': events, 'metrics': metrics(events, 0, 5400), 'insights': claims, 'broken_claim': broken, 'templates': {c['id']: {lang: {d: render(c, events, d, lang) for d in ['Fan', 'Analyst', 'Broadcast']} for lang in ['en', 'zh']} for c in claims}}

def serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent/'data'
    root.mkdir(exist_ok=True)
    bundle = build(args.seed)
    (root/'match.json').write_text(serialized(bundle), encoding='utf-8')
    (root/'match.js').write_text('window.MATCH = '+serialized(bundle).rstrip()+';\n', encoding='utf-8')
    (root/'events.jsonl').write_text(''.join(serialized(e) for e in bundle['events']), encoding='utf-8')
    print(f'{LABEL}: {len(bundle["events"])} events; {bundle["metrics"]["pass_count"]} passes; {bundle["metrics"]["shot_count"]} shots; {len(bundle["insights"])} verified insights.')

if __name__ == '__main__':
    main()
