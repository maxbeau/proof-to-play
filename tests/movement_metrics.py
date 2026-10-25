"""Offline measurements; speeds are endpoint displacement / five seconds."""
import math
import statistics
from collections import Counter, defaultdict
from pipeline import POSITION_PLAYERS


def roles():
    return (['goalkeeper'] + ['defender']*4 + ['winger', 'midfielder', 'midfielder', 'winger'] + ['forward']*2
            + ['goalkeeper'] + ['defender']*4 + ['midfielder']*3 + ['winger', 'forward', 'winger'])


def measure(events):
    speeds = defaultdict(list)
    shares, spreads, ball = [], [], []
    individual = [[] for _ in range(22)]
    minimum = float('inf')
    replay_minimum = float('inf')
    team_spreads, centroid_distances = [], []
    for event in events:
        xy = [event['positions'][i:i+2] for i in range(2, 46, 2)]
        minimum = min(minimum, min(math.dist(a,b) for i,a in enumerate(xy) for b in xy[i+1:]))
        for team in (xy[:11], xy[11:]):
            center = [sum(p[k] for p in team)/11 for k in (0,1)]
            team_spreads.append(math.sqrt(sum(math.dist(p,center)**2 for p in team)/11))
            centroid_distances.append(math.dist(center, event['positions'][:2]))
    for a,b in zip(events, events[1:]):
        for i in range(22):
            for j in range(i+1,22):
                k,l = 2+2*i,2+2*j
                rx,ry = a['positions'][k]-a['positions'][l],a['positions'][k+1]-a['positions'][l+1]
                dx = b['positions'][k]-b['positions'][l]-rx
                dy = b['positions'][k+1]-b['positions'][l+1]-ry
                length2 = dx*dx+dy*dy
                alpha = max(0,min(1,-(rx*dx+ry*dy)/length2)) if length2 else 0
                replay_minimum = min(replay_minimum, math.hypot(rx+alpha*dx,ry+alpha*dy))
        headings = []
        for j,role in enumerate(roles()):
            k=2+j*2
            dx,dy=b['positions'][k]-a['positions'][k],b['positions'][k+1]-a['positions'][k+1]
            length=math.hypot(dx,dy)
            speeds[role].append(length/5)
            individual[j].append(length/5)
            if length >= .2:
                headings.append(math.atan2(dy,dx))
        if headings:
            bins=Counter(int((angle+math.pi)/(math.pi/4))%8 for angle in headings)
            shares.append(max(bins.values())/len(headings))
            spreads.append(1-math.hypot(sum(math.cos(h) for h in headings),sum(math.sin(h) for h in headings))/len(headings))
        ball.append(math.dist(a['positions'][:2],b['positions'][:2]))
    duration = events[-1]['time']-events[0]['time']
    actor_distances = []
    nearest_distances = []
    for event in events:
        k = 2+2*POSITION_PLAYERS.index(event['player'])
        actor_distances.append(math.dist(event['positions'][:2], event['positions'][k:k+2]))
        nearest_distances.append(min(math.dist(event['positions'][:2], event['positions'][k:k+2]) for k in range(2,46,2)))
    def ranges(rows):
        return [[max(e['positions'][2+2*i+k] for e in rows)-min(e['positions'][2+2*i+k] for e in rows) for k in (0,1)] for i in range(22)]
    return {'role_mean_speed': {r:sum(v)/len(v) for r,v in speeds.items()},
            'role_distance_km': {r:sum(v)/len(v)*duration/1000 for r,v in speeds.items()},
            'player_distance_km': [sum(v)*5/1000 for v in individual],
            'player_range_xy': ranges(events),
            'player_first60_range_xy': ranges(events[:60]),
            'player_peak_sample_speed': [max(v) for v in individual],
            'ball_actor_mean': statistics.mean(actor_distances),
            'ball_actor_median': statistics.median(actor_distances),
            'ball_nearest_mean': statistics.mean(nearest_distances),
            'player_mean_speed': [sum(v)/len(v) for v in individual],
            'heading_mean_dominant_bin': sum(shares)/len(shares),
            'heading_max_dominant_bin': max(shares),
            'heading_fraction_above_75pct': sum(s>.75 for s in shares)/len(shares),
            'heading_mean_circular_spread': sum(spreads)/len(spreads),
            'minimum_separation': minimum, 'minimum_replay_separation': replay_minimum, 'minimum_team_rms_spread': min(team_spreads),
            'mean_centroid_ball_distance': sum(centroid_distances)/len(centroid_distances),
            'ball_mean_step':sum(ball)/len(ball),'ball_max_step':max(ball)}
