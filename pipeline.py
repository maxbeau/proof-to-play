"""Synthetic / Simulated Match: offline deterministic pipeline."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random

SEED = 20261024
LABEL = 'Synthetic / Simulated Match'
VERSION = 'events-v1.0'
TEAMS = ['Aster Quills', 'Mica Lanterns']
ROSTERS = {t: [f'{p}-{i:02d}' for i in range(1, 12)] for t, p in zip(TEAMS, ['AQ', 'ML'])}
POSITION_PLAYERS = [player for team in TEAMS for player in ROSTERS[team]]
POSITION_LABEL = 'SYNTHETIC / SIMULATED — generated schematic positions; not real tracking data or measured player locations'
BALL_STEP_CAP = 8.0  # metres per five-second sample, including rounding
PLAYER_STEP_CAP = 3.8
ROUNDING_MARGIN = .15  # maximum two-endpoint 0.1m rounding error is < .142m
KINDS = {'pressing': ('pressing_proxy', 1), 'flank': ('flank_share_pct', 15), 'fatigue': ('recovery_seconds', 3)}

# Roster order is goalkeeper, back line, midfield line, then forwards. The first
# side attacks toward +x; the second mirrors it and attacks toward -x.
FORMATIONS = {
    TEAMS[0]: [(-48.5, 0), (-34, -23), (-35, -8), (-35, 8), (-34, 23),
               (-16, -23), (-15, -8), (-15, 8), (-16, 23), (5, -10), (18, 10)],
    TEAMS[1]: [(48.5, 0), (34, -23), (35, -8), (35, 8), (34, 23),
               (16, -18), (15, 0), (16, 18), (-5, -18), (-5, 0), (-5, 18)]
}

def clamp(value, low, high):
    return max(low, min(high, value))

def position_samples(events, seed):
    """Attach deterministic, schematic metre coordinates to each event sample."""
    # Keep the event stream's random draws independent of all position details.
    rng = random.Random(seed ^ 0x5A17C0DE)
    player_index = {player: i for i, player in enumerate(POSITION_PLAYERS)}
    team_offset = {team: i * 11 for i, team in enumerate(TEAMS)}
    attack_sign = {TEAMS[0]: 1, TEAMS[1]: -1}
    anchors = FORMATIONS

    pressing_rows = [e for e in events if 25*60 <= e['time'] <= 30*60 and e['event_type'] == 'pressure']
    pressing_team = max(TEAMS, key=lambda team: (sum(e['team'] == team for e in pressing_rows), -TEAMS.index(team)))
    flank_rows = [e for e in events if 50*60 <= e['time'] <= 55*60 and e['event_type'] == 'pass']
    flank_counts = {side: sum(e['zone'] == side for e in flank_rows) for side in ('left', 'right')}
    flank_direction = -1 if flank_counts['left'] >= flank_counts['right'] else 1

    player_positions = []
    for team in TEAMS:
        for x, y in anchors[team]:
            player_positions.append([clamp(x + rng.uniform(-.8, .8), -52.5, 52.5),
                                     clamp(y + rng.uniform(-.8, .8), -34, 34)])

    smooth_targets = [xy.copy() for xy in player_positions]
    velocities = [[0.0, 0.0] for _ in player_positions]
    last_ball = [0.0, 0.0]
    ball_target = None
    for event in events:
        t = event['time']
        pressing = 25*60 <= t <= 30*60
        flank = 50*60 <= t <= 55*60
        fatigue = 75*60 <= t <= 80*60
        zone_y = {'left': -18.0, 'center': 0.0, 'right': 18.0}[event['zone']]
        for team in TEAMS:
            is_pressing = pressing and team == pressing_team
            compact_x = .88 if is_pressing else 1.0
            compact_y = .78 if is_pressing else 1.0
            flank_bias = flank_direction * (6.0 if team == event['team'] else 3.0) if flank else 0.0
            contextual_y = zone_y * (.16 if team == event['team'] else .10)
            contextual_x = attack_sign[team] * 2.0 if team == event['team'] else clamp(last_ball[0] * .10, -5, 5)
            press_push = attack_sign[team] * 5.0 if is_pressing else 0.0
            for local_i, (anchor_x, anchor_y) in enumerate(anchors[team]):
                i = team_offset[team] + local_i
                shape_center_x = sum(x for x, _ in anchors[team]) / 11
                target_x = shape_center_x + (anchor_x - shape_center_x) * compact_x + contextual_x + press_push
                target_y = anchor_y * compact_y + contextual_y + flank_bias
                # Slow shared shape drift; context changes settle over tens of seconds.
                target_x += 8 * math.sin(2 * math.pi * t / 180) * (.25 if local_i == 0 else 1)
                target_y += 4 * math.sin(2 * math.pi * t / 240)
                smooth_targets[i][0] += .12 * (target_x - smooth_targets[i][0])
                smooth_targets[i][1] += .12 * (target_y - smooth_targets[i][1])
                current_x, current_y = player_positions[i]
                movement_scale = .5 if fatigue else 1.0
                dx = .75 * velocities[i][0] + .25 * (.35 * (smooth_targets[i][0] - current_x) + rng.gauss(0, .06)) * movement_scale
                dy = .75 * velocities[i][1] + .25 * (.35 * (smooth_targets[i][1] - current_y) + rng.gauss(0, .06)) * movement_scale
                distance = (dx*dx + dy*dy) ** .5
                step_cap = (1.35 if fatigue else PLAYER_STEP_CAP) - ROUNDING_MARGIN
                if distance > step_cap:
                    dx *= step_cap / distance
                    dy *= step_cap / distance
                velocities[i] = [dx, dy]
                player_positions[i] = [clamp(current_x + dx, -52.5, 52.5),
                                       clamp(current_y + dy, -34, 34)]

        # Finish a schematic trip before selecting another event's destination.
        # Intermediate events remain intact; this is not a reconstruction of touches.
        if ball_target is None or math.dist(last_ball, ball_target) < .4:
            actor = player_positions[player_index[event['player']]]
            if event['event_type'] == 'pass':
                roster = ROSTERS[event['team']]
                receiver = roster[(roster.index(event['player']) + 4) % len(roster)]
                ball_target = player_positions[player_index[receiver]].copy()
            elif event['event_type'] == 'shot':
                ball_target = [attack_sign[event['team']] * 51.0, clamp(actor[1] * .20, -3.2, 3.2)]
            else:
                ball_target = actor.copy()
        dx, dy = ball_target[0] - last_ball[0], ball_target[1] - last_ball[1]
        distance = math.hypot(dx, dy)
        travel = min(BALL_STEP_CAP - ROUNDING_MARGIN, distance * .4)
        if distance < 1:
            travel = distance
        fraction = travel / distance if distance else 0
        ball = [clamp(last_ball[0] + dx * fraction, -52.5, 52.5),
                clamp(last_ball[1] + dy * fraction, -34, 34)]
        flat = [round(ball[0], 1), round(ball[1], 1)]
        for x, y in player_positions:
            flat.extend((round(x, 1), round(y, 1)))
        event['positions'] = flat
        event['position_label'] = POSITION_LABEL
        last_ball = ball

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
    position_samples(events, seed)
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
    return {'label': LABEL, 'seed': seed, 'formula_version': VERSION, 'teams': TEAMS,
            'position_label': POSITION_LABEL, 'position_players': POSITION_PLAYERS,
            'position_encoding': '[ball_x, ball_y, then x,y pairs in position_players order; metres]',
            'formations': {'Aster Quills': '4-4-2', 'Mica Lanterns': '4-3-3'},
            'events': events, 'metrics': metrics(events, 0, 5400), 'insights': claims,
            'broken_claim': broken,
            'templates': {c['id']: {lang: {d: render(c, events, d, lang) for d in ['Fan', 'Analyst', 'Broadcast']} for lang in ['en', 'zh']} for c in claims}}

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
