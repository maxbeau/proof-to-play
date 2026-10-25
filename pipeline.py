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

# Schematic units: maxSpeed m/s, maxForce m/s² (unit mass), response seconds.
# Fatigue is a speed/acceleration multiplier in minutes 75–80, not real physiology.
# Wingers are wide midfielders in 4-4-2 and wide forwards in 4-3-3.
ROLE_ATTRIBUTES = {
    'goalkeeper': dict(maxSpeed=4.0, maxForce=2.0, response=.85, stamina=.95, shift=.10, roam=5.0, width=7.5, period=47.0, runFraction=.50),
    'defender': dict(maxSpeed=7.2, maxForce=3.2, response=.75, stamina=.90, shift=.60, roam=17.0, width=9.0, period=49.0, runFraction=.42),
    'midfielder': dict(maxSpeed=8.3, maxForce=3.8, response=.65, stamina=.88, shift=.85, roam=24.0, width=12.0, period=58.0, runFraction=.40),
    'winger': dict(maxSpeed=9.5, maxForce=4.8, response=.45, stamina=.86, shift=1.00, roam=31.0, width=7.0, period=65.0, runFraction=.22),
    'forward': dict(maxSpeed=9.0, maxForce=4.2, response=.55, stamina=.88, shift=.95, roam=26.0, width=11.0, period=66.5, runFraction=.30),
}
PLAYER_ROLES = (['goalkeeper'] + ['defender']*4
                + ['winger', 'midfielder', 'midfielder', 'winger'] + ['forward']*2
                + ['goalkeeper'] + ['defender']*4 + ['midfielder']*3
                + ['winger', 'forward', 'winger'])
STEERING_DT = .1
PERSONAL_SPACE = 2.0
CONTACT_DISTANCE = 1.85  # >=1.50m after two-endpoint 0.1m quantization.


def player_attributes(seed):
    """Independent seeded movement attributes; never consume event RNG draws."""
    rng = random.Random(seed ^ 0x71A6BEEF)
    result = []
    for role in PLAYER_ROLES:
        attributes = {key: value*rng.uniform(.94, 1.06)
                      for key, value in ROLE_ATTRIBUTES[role].items()}
        attributes.update(role=role, phase=rng.uniform(0, 2*math.pi),
                          weights={name: weight*rng.uniform(.9, 1.1) for name, weight in
                                   [('anchor', 1), ('pursuit', .85), ('mark', .65),
                                    ('space', .55), ('wander', .18), ('separation', 2.8)]})
        result.append(attributes)
    for attributes in result:
        attributes['arc_direction'] = rng.choice((-1, 1))
    return result


def limit_vector(x, y, maximum):
    length = math.hypot(x, y)
    scale = min(1, maximum/length) if length else 1
    return x*scale, y*scale


def vehicle_step(position, velocity, desired, attributes, fatigue=1):
    """YUKA-style unit-mass vehicle: steering = desired velocity - velocity.

    Relax response, clamp force, integrate persistent velocity, cap speed, then
    integrate position. No shared displacement cap or per-sample velocity reset.
    """
    ax, ay = limit_vector((desired[0]-velocity[0])/attributes['response'],
                          (desired[1]-velocity[1])/attributes['response'],
                          attributes['maxForce']*fatigue)
    vx, vy = limit_vector(velocity[0]+ax*STEERING_DT, velocity[1]+ay*STEERING_DT,
                          attributes['maxSpeed']*fatigue)
    return [position[0]+vx*STEERING_DT, position[1]+vy*STEERING_DT], [vx, vy]


def role_zone(i):
    """Broad tactical lanes, not kickoff-centred cages (synthetic/schematic)."""
    x, y = FORMATIONS[TEAMS[i//11]][i%11]
    role = PLAYER_ROLES[i]
    if role == 'goalkeeper':
        return (-51.5, -38, -11, 11) if i < 11 else (38, 51.5, -11, 11)
    half_width = {'defender': 9, 'midfielder': 13, 'winger': 8, 'forward': 13}[role]
    xmin, xmax = (0, 50) if role == 'forward' and i < 11 else (-50, 0) if role == 'forward' else (-50, 50)
    return xmin, xmax, max(-32.5, y-half_width), min(32.5, y+half_width)


def run_zone(i):
    """Keep the wide defensive screen inside its unchanged legal role zone.

    Its two sides retain at least 32 m width while independent midfield and
    wing runs turn inward. This is a route constraint, not a test exemption.
    """
    xmin,xmax,ymin,ymax = role_zone(i)
    if PLAYER_ROLES[i]=='defender' and i%11 in (1,4):
        if ymin < 0:
            ymax = min(ymax,-16)
        else:
            ymin = max(ymin,16)
    return xmin,xmax,ymin,ymax


def run_target(i, a, now, territory, possession, pressing, tired, flank_direction):
    """A sustained advance then recovery on a role-shaped closed route.

    The short attacking leg gives wide players sprint opportunities; the long
    recovery leg pays for those bursts in the match displacement budget. Each
    player's phase/period is independent. Lateral arcs make turns continuous.
    """
    sign = 1 if i < 11 else -1
    anchor = FORMATIONS[TEAMS[i//11]][i%11]
    role = a['role']
    u = (now/a['period'] + a['phase']/(2*math.pi)) % 1
    fraction = a['runFraction']
    theta = math.pi*u/fraction if u < fraction else math.pi+math.pi*(u-fraction)/(1-fraction)
    if role == 'goalkeeper':
        center = [-45*sign + a['shift']*territory, 0]
    else:
        base_x = {'defender': -25, 'midfielder': -4, 'winger': 0, 'forward': 14}[role]
        tactical = 3-6*abs(i//11-possession) + (3 if pressing else 0)
        center = [sign*(base_x+tactical) + a['shift']*territory, anchor[1]]
    fatigue = a['stamina'] if tired else 1
    zone = run_zone(i)
    # Fit the complete curved route inside the lane. Clipping individual
    # target coordinates created stationary wall segments followed by U-turns.
    rx = min(a['roam']*fatigue, (zone[1]-zone[0])/2)
    ry = min(a['width'], (zone[3]-zone[2])/2)
    center[0] = clamp(center[0], zone[0]+rx, zone[1]-rx)
    if flank_direction and role == 'winger':
        center[1] += flank_direction*2
    center[1] = clamp(center[1], zone[2]+ry, zone[3]-ry)
    if role == 'goalkeeper':
        dx, dy = -rx*math.cos(theta), ry*math.sin(theta)
    else:
        # Give each 180-degree turn ten seconds. A narrow ellipse rushes its
        # tight ends, producing >120-degree changes between five-second chords.
        turn = 10.0
        straight = a['period']-2*turn
        advance = straight*fraction
        recover = straight-advance
        clock = u*a['period']
        half = max(0, rx-ry)
        arc = ry*(.42+.08*math.sin(a['phase']))
        if clock < advance:
            progress = clock/advance
            lateral = progress+.1*math.sin(2*math.pi*progress+a['phase'])*math.sin(math.pi*progress)**2
            dx, dy = -half+2*half*progress, ry-arc*math.sin(math.pi*lateral)**2
        elif clock < advance+turn:
            angle = math.pi*(clock-advance)/turn
            dx, dy = half+ry*math.sin(angle), ry*math.cos(angle)
        elif clock < advance+turn+recover:
            progress = (clock-advance-turn)/recover
            lateral = progress+.1*math.sin(2*math.pi*progress-a['phase'])*math.sin(math.pi*progress)**2
            dx, dy = half-2*half*progress, -ry+arc*math.sin(math.pi*lateral)**2
        else:
            angle = math.pi*(clock-advance-turn-recover)/turn
            dx, dy = -half-ry*math.sin(angle), -ry*math.cos(angle)
    target = [center[0]+sign*dx, center[1]+a['arc_direction']*dy]
    return target, 'advance' if u < fraction else 'recover'


def shot_arrivals(events):
    """Spatial commitments only; immutable event actors/times are not rewritten.

    Reserve 13 m of the 125 m shot-plus-return budget for steering/rounding.
    Each actor approaches its feasible goal-centred receiving region ahead
    of the shot, including the long return when a goalkeeper is next to touch.
    """
    arrivals = [[] for _ in POSITION_PLAYERS]
    for event, nxt in zip(events, events[1:]):
        if event['event_type'] != 'shot':
            continue
        goal = [52.5 if event['team'] == TEAMS[0] else -52.5, 0]
        actors = [POSITION_PLAYERS.index(e['player']) for e in (event, nxt)]
        minimum = [math.dist(goal, in_zone(goal, run_zone(i))) for i in actors]
        slack = 125-sum(minimum)
        if slack < 0:
            raise ValueError(f'{event["id"]}: role zones cannot fit shot/return budget')
        spare = slack-min(13,slack/2)
        for e, i, distance in zip((event, nxt), actors, minimum):
            arrivals[i].append((e['time'], goal, distance+spare/2))
    return arrivals


def arrive_for_shot(target, now, commitments, zone):
    for deadline, goal, radius in commitments:
        remaining = deadline-now
        if not -15 <= remaining <= 50:
            continue
        # Gradual convergence well before the touch, then release the run.
        radius += max(0, remaining-5)*1.1 + max(0, -remaining)*2.0
        distance = math.dist(target, goal)
        if distance > radius:
            target = in_zone([goal[k]+(target[k]-goal[k])*radius/distance for k in (0, 1)], zone)
    return target


def in_zone(point, zone):
    return [clamp(point[0], zone[0], zone[1]), clamp(point[1], zone[2], zone[3])]


def assign_behaviours(positions, ball, possession, pressing):
    """Assign only at tactical possession/phase changes, never on every sample."""
    modes = ['holder']*22
    opponents = [None]*22
    defending = 1-possession
    candidates = range(defending*11+1, defending*11+11)
    pressers = sorted(candidates, key=lambda i: (math.dist(positions[i], ball), i))[:2 if pressing else 1]
    for i in pressers:
        modes[i] = 'presser'
    attackers = [i for i in range(possession*11+1, possession*11+11)
                 if PLAYER_ROLES[i] in ('winger', 'forward')]
    for i in attackers:
        modes[i] = 'runner'
    supporters = [i for i in range(possession*11+1, possession*11+11)
                  if PLAYER_ROLES[i] == 'midfielder'][:2]
    for i in supporters:
        modes[i] = 'supporter'
    available = [i for i in range(defending*11+1, defending*11+5) if i not in pressers]
    for i in available[:2]:
        opponent = min(attackers, key=lambda j: (math.dist(positions[i], positions[j]), j))
        modes[i], opponents[i] = 'marker', opponent
        attackers.remove(opponent)
    return modes, opponents


def position_samples(events, seed, diagnostics=None):
    """One synthetic/schematic simulation: balls use the displayed actors.

    Event actors are independent observations, not a continuous possession
    chain. Each stored sample is the event's touch, using the final displayed
    player coordinates. Anticipated shot arrivals fit the goal-and-return path
    into the five-second budget without moving a sample after integration.
    """
    attributes = player_attributes(seed)
    arrivals = shot_arrivals(events)
    pressures = [e for e in events if 1500 <= e['time'] <= 1800 and e['event_type'] == 'pressure']
    pressing_team = max(range(2), key=lambda team: (sum(e['team'] == TEAMS[team] for e in pressures), -team))
    flank_passes = [e for e in events if 3000 <= e['time'] <= 3300 and e['event_type'] == 'pass']
    flank_direction = -1 if sum(e['zone'] == 'left' for e in flank_passes) >= sum(e['zone'] == 'right' for e in flank_passes) else 1
    zones = [run_zone(i) for i in range(22)]
    positions = [list(anchor) for team in TEAMS for anchor in FORMATIONS[team]]
    velocities = [[0., 0.] for _ in positions]
    previous_ball = positions[POSITION_PLAYERS.index(events[0]['player'])].copy()
    territory = 0.0
    territory_velocity, territory_aim = 0.0, 0.0
    shape_possession = TEAMS.index(events[0]['state']['possession_team'])
    possession, phase, assigned_at = None, None, -30
    modes, opponents = [], []
    pending_possession, pending_count = None, 0
    for event in events:
        t = event['time']
        pressing, flank, tired = 1500 <= t <= 1800, 3000 <= t <= 3300, 4500 <= t <= 4800
        new_phase = (pressing, flank, tired)
        candidate = TEAMS.index(event['state']['possession_team'])
        # Event teams are independently sampled, not continuous possession runs.
        # Require three matching observations and >=30s dwell for a tactical
        # handover; phase boundaries may also change assignments. Events stay intact.
        if candidate == pending_possession:
            pending_count += 1
        else:
            pending_possession, pending_count = candidate, 1
        if possession is None or new_phase != phase or (candidate != possession and pending_count >= 3 and t-assigned_at >= 30):
            possession, phase, assigned_at = candidate, new_phase, t
            modes, opponents = assign_behaviours(positions, previous_ball, possession, pressing and 1-possession == pressing_team)
            territory_aim = clamp(previous_ball[0], -28, 28)
        if diagnostics is not None:
            diagnostics.append({'time': t, 'modes': modes.copy(), 'possession': possession,
                                'phase': phase, 'assigned_at': assigned_at, 'ball': previous_ball.copy(),
                                'assignment_positions': [xy.copy() for xy in positions] if assigned_at == t else None})
        sample_start = [xy.copy() for xy in positions]
        contact_planes = []
        for i in range(22):
            for j in range(i+1,22):
                sx,sy = sample_start[i][0]-sample_start[j][0],sample_start[i][1]-sample_start[j][1]
                contact_planes.append((i,j,sx,sy))
        peak_speeds = [0.0]*22
        run_phases = []
        for substep in range(50):
            now = t-5+(substep+1)*STEERING_DT
            # Follow the actual prior possessor with a tactical response time;
            # the ball is never supplied by a second player simulation.
            # Do not jerk every route centre toward a new independent actor
            # every five seconds. Tactical arrivals have persistent velocity,
            # gentle acceleration and the same debounced assignment lifetime.
            territory_desired = clamp((territory_aim-territory)/10, -1, 1)
            territory_velocity += STEERING_DT*clamp((territory_desired-territory_velocity)/6, -.15, .15)
            territory += STEERING_DT*territory_velocity
            shape_possession += STEERING_DT/8*(possession-shape_possession)
            desired = []
            run_phases = []
            for i, a in enumerate(attributes):
                target, run_phase = run_target(i, a, now, territory, shape_possession, pressing and i//11 == pressing_team, tired, flank_direction if flank else 0)
                future, _ = run_target(i, a, now+STEERING_DT, territory, shape_possession, pressing and i//11 == pressing_team, tired, flank_direction if flank else 0)
                target = arrive_for_shot(target, now, arrivals[i], zones[i])
                future = arrive_for_shot(future, now+STEERING_DT, arrivals[i], zones[i])
                run_phases.append(run_phase)
                # Feed-forward follows a sustained route, while arrive corrects
                # tracking error. Physical velocity/acceleration stay persistent.
                velocity = [(future[k]-target[k])/STEERING_DT + (target[k]-positions[i][k])/a['response'] for k in (0,1)]
                mode = modes[i]
                if mode == 'presser':
                    pursuit = limit_vector(previous_ball[0]-positions[i][0], previous_ball[1]-positions[i][1], 1.2 if pressing else .5)
                    velocity = [velocity[k]+pursuit[k]*a['weights']['pursuit'] for k in (0,1)]
                elif mode == 'marker':
                    opponent = positions[opponents[i]]
                    velocity[1] += clamp((opponent[1]-positions[i][1])*.04,-.6,.6)*a['weights']['mark']
                fatigue = a['stamina'] if tired else 1
                desired.append(list(limit_vector(*velocity, a['maxSpeed']*fatigue)))
            # Symmetric social repulsion applies across BOTH teams. Snapshot update
            # avoids roster-order advantage. Only near neighbours contribute.
            for i in range(22):
                for j in range(i+1, 22):
                    dx, dy = positions[i][0]-positions[j][0], positions[i][1]-positions[j][1]
                    if abs(dx) >= PERSONAL_SPACE*2 or abs(dy) >= PERSONAL_SPACE*2:
                        continue
                    distance = math.hypot(dx, dy)
                    if distance < PERSONAL_SPACE*2:
                        nx, ny = (dx/distance, dy/distance) if distance else (1., 0.)
                        push = (1-distance/(PERSONAL_SPACE*2))**2
                        if distance < PERSONAL_SPACE:
                            push += (PERSONAL_SPACE-distance)*3
                        for index, direction in ((i,1),(j,-1)):
                            strength = push*attributes[index]['weights']['separation']
                            desired[index][0] += direction*nx*strength
                            desired[index][1] += direction*ny*strength
            for i, a in enumerate(attributes):
                fatigue = a['stamina'] if tired else 1
                positions[i], velocities[i] = vehicle_step(positions[i], velocities[i], desired[i], a, fatigue)
                peak_speeds[i] = max(peak_speeds[i], math.hypot(*velocities[i]))
                bounded = in_zone(positions[i], zones[i])
                for k in (0, 1):
                    if bounded[k] != positions[i][k]:
                        velocities[i][k] = 0
                positions[i] = bounded
            # Test the actual chord, not a fixed start-normal half-plane. The
            # latter forbids safe side-by-side passing and kicks players back
            # into their old lane. For an unsafe chord choose a tangent plane
            # feasible at the start, then slide along it. No division by the
            # closest-approach fraction, and the complete replay stays clear.
            for _ in range(16):
                contact = False
                for i,j,sx,sy in contact_planes:
                    dx,dy = positions[i][0]-positions[j][0], positions[i][1]-positions[j][1]
                    if ((sx >= CONTACT_DISTANCE and dx >= CONTACT_DISTANCE) or
                        (sx <= -CONTACT_DISTANCE and dx <= -CONTACT_DISTANCE) or
                        (sy >= CONTACT_DISTANCE and dy >= CONTACT_DISTANCE) or
                        (sy <= -CONTACT_DISTANCE and dy <= -CONTACT_DISTANCE)):
                        continue
                    vx,vy = dx-sx,dy-sy
                    q = vx*vx+vy*vy
                    fraction = clamp(-(sx*vx+sy*vy)/q,0,1) if q else 0
                    cx,cy = sx+fraction*vx,sy+fraction*vy
                    clearance = math.hypot(cx,cy)
                    if clearance >= CONTACT_DISTANCE-1e-4:
                        continue
                    length = math.hypot(sx,sy)
                    angle = math.acos(min(1,CONTACT_DISTANCE/length))
                    side = 1 if sx*dy-sy*dx > 0 else -1
                    choices = []
                    for rotation in (side*angle,-side*angle,0):
                        cosine,sine = math.cos(rotation),math.sin(rotation)
                        nx,ny = (sx*cosine-sy*sine)/length,(sx*sine+sy*cosine)/length
                        deficit = max(0,CONTACT_DISTANCE-dx*nx-dy*ny)+2e-6
                        axes = []
                        for player,direction in ((i,1),(j,-1)):
                            for k,normal in enumerate((nx,ny)):
                                movement = direction*normal
                                if abs(movement)>1e-12:
                                    boundary = zones[player][2*k+(1 if movement>0 else 0)]
                                    room = max(0,(boundary-positions[player][k])*(1 if movement>0 else -1))
                                    axes.append((player,k,movement,room))
                        capacity = sum(abs(component)*room for _,_,component,room in axes)
                        choices.append((deficit+(1e6 if capacity<deficit else 0),nx,ny,axes))
                    # A lane wall may block the naturally preferred side. Use
                    # the other tangent before pushing anyone into that wall.
                    _,nx,ny,axes = min(choices,key=lambda choice:choice[0])
                    gap = dx*nx+dy*ny
                    if gap < CONTACT_DISTANCE-1e-4:
                        correction = CONTACT_DISTANCE-gap+2e-6
                        # Box-constrained plane projection: when a lateral
                        # axis reaches its lane wall, the free longitudinal
                        # axes still brake the crossing. Do not discard the
                        # entire correction just because one axis is blocked.
                        while axes and correction>1e-10:
                            scale = correction/sum(component*component for _,_,component,_ in axes)
                            blocked = [axis for axis in axes if scale*abs(axis[2])>axis[3]]
                            if not blocked:
                                for player,k,component,_ in axes:
                                    positions[player][k] += scale*component
                                break
                            for axis in blocked:
                                player,k,component,room = axis
                                positions[player][k] += math.copysign(room,component)
                                correction -= abs(component)*room
                                axes.remove(axis)
                        positions[i] = in_zone(positions[i],zones[i])
                        positions[j] = in_zone(positions[j],zones[j])
                        closing = (velocities[i][0]-velocities[j][0])*nx+(velocities[i][1]-velocities[j][1])*ny
                        if closing < 0:
                            for k, normal in enumerate((nx,ny)):
                                velocities[i][k] -= normal*closing/2
                                velocities[j][k] += normal*closing/2
                        contact = True
                if not contact:
                    break
        flat = [round(value,1) for xy in positions for value in xy]
        actor = POSITION_PLAYERS.index(event['player'])
        ball = flat[2*actor:2*actor+2]
        event['positions'] = ball + flat
        event['position_label'] = POSITION_LABEL
        if diagnostics is not None:
            diagnostics[-1].update(territory=territory, run_phases=run_phases, peak_speeds=peak_speeds)
        previous_ball = ball


def ball_flights(events, seed=SEED):
    """Spatial-only sidecar: flight legs followed by held receiver motion.

    The receiver is the next observed actor, not an inferred successful pass.
    Interception solves against the same linear player path used in replay.
    No leg may be cut short or snapped to a new actor at the next sample.
    """
    plans = {}
    for event, nxt in zip(events, events[1:]):
        seconds = nxt['time']-event['time']
        origin = event['positions'][:2]
        endpoint = nxt['positions'][:2]
        offset = 2+2*POSITION_PLAYERS.index(nxt['player'])
        receiver_start = event['positions'][offset:offset+2]
        def receiver_at(time):
            return [receiver_start[k]+(endpoint[k]-receiver_start[k])*time/seconds for k in (0, 1)]
        shot = event['event_type'] == 'shot'
        goal = [52.5 if event['team'] == TEAMS[0] else -52.5, 0]
        path = math.dist(origin, goal)+math.dist(goal, endpoint) if shot else math.dist(origin, endpoint)
        speed = 25.0 if shot else max(18+(seed ^ int(event['id'][1:])) % 6, path/(seconds-.1))
        if speed > 25 or path > 25*seconds:
            raise ValueError(f'{event["id"]}: {path:.6f} m cannot fit {seconds} s flight budget')
        segments = []
        start = 0.0
        source = origin
        if shot:
            end = math.dist(origin, goal)/speed
            segments.append(dict(phase='shot', start=start, end=end, origin=source, target=goal))
            start, source = end, goal
        if not shot and event['event_type']=='pass' and event['player']==nxt['player'] and math.dist(origin, endpoint)>1e-10:
            # A repeated actor can knock the ball into their own run. The
            # flight ends at the one-second receiving point; the ball waits
            # there explicitly until the player arrives, then stays attached.
            touch = min(1.0, seconds)
            target = receiver_at(touch)
            end = math.dist(source, target)/speed
            segments.append(dict(phase='pass', start=0.0, end=end, origin=source, target=target))
            segments.append(dict(phase='waiting', start=end, end=touch, origin=target, target=target))
            start, source = touch, target
        elif math.dist(source, receiver_at(start)) > 1e-10:
            low, high = start, seconds
            for _ in range(48):
                middle = (low+high)/2
                if math.dist(source, receiver_at(middle)) > speed*(middle-start):
                    low = middle
                else:
                    high = middle
            end = high
            target = receiver_at(end)
            segments.append(dict(phase='rebound' if shot else 'pass' if event['event_type']=='pass' else 'transfer',
                                 start=start, end=end, origin=source, target=target))
            start, source = end, target
        # HOLD means possession at the moving receiver, not continued flight.
        # The carrier follows exactly the displayed player chord.
        segments.append(dict(phase='held', start=start, end=seconds, origin=source, target=endpoint))
        plans[event['id']] = dict(seconds=seconds, receiver=nxt['player'], segments=segments)
    return dict(label=POSITION_LABEL, seed=seed, plans=plans)


def player_modes(diagnostics, seed=SEED):
    """Display-only sidecar from the integration trace; never infer assignments.

    Attributes use the same independent seeded function as position_samples.
    Initial positions support a trailing speed estimate at the first sample.
    Some stored weights are unused by this model; the UI labels that explicitly.
    """
    attributes = player_attributes(seed)
    return {
        'label': POSITION_LABEL, 'seed': seed,
        'position_players': POSITION_PLAYERS,
        'players': [dict(id=player, team=TEAMS[i//11],
                         **{key: attributes[i][key] for key in
                            ('role', 'weights', 'maxSpeed', 'maxForce', 'response', 'stamina')})
                    for i, player in enumerate(POSITION_PLAYERS)],
        'initial': {'time': 0, 'positions': [list(xy) for team in TEAMS for xy in FORMATIONS[team]]},
        'samples': [{'time': row['time'], 'modes': row['modes'].copy()} for row in diagnostics],
    }


def stamp(seconds):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')

def generate(seed=SEED, diagnostics=None):
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
    position_samples(events, seed, diagnostics)
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

def build(seed=SEED, diagnostics=None):
    events, claims = generate(seed, diagnostics), []
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
    diagnostics = []
    bundle = build(args.seed, diagnostics)
    flights = serialized(ball_flights(bundle['events'], args.seed))
    modes = serialized(player_modes(diagnostics, args.seed))
    (root/'match.json').write_text(serialized(bundle), encoding='utf-8')
    (root/'match.js').write_text('window.MATCH = '+serialized(bundle).rstrip()+';\n', encoding='utf-8')
    (root/'events.jsonl').write_text(''.join(serialized(e) for e in bundle['events']), encoding='utf-8')
    (root/'ball-flights.json').write_text(flights, encoding='utf-8')
    (root/'ball-flights.js').write_text('window.BALL_FLIGHTS = '+flights.rstrip()+';\n', encoding='utf-8')
    (root/'player-modes.json').write_text(modes, encoding='utf-8')
    (root/'player-modes.js').write_text('window.PLAYER_MODES = '+modes.rstrip()+';\n', encoding='utf-8')
    print(f'{LABEL}: {len(bundle["events"])} events; {bundle["metrics"]["pass_count"]} passes; {bundle["metrics"]["shot_count"]} shots; {len(bundle["insights"])} verified insights.')

if __name__ == '__main__':
    main()
