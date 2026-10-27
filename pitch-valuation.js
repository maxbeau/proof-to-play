/* Display-only geometric proxies. No event, mode, motion or evidence mutation.
 * Regenerate new sidecars only: node pitch-valuation.js
 * All distances below are metres; C(z) = max(0, min(1, z)).
 */
(function (root) {
  'use strict';
  const VERSION = 'schematic-values-v1';
  const LABEL = "rule-computed schematic scores over synthetic positions — NOT learned Q-values, NOT the paper's trained model, NOT an equilibrium computation";
  const FEATURES = ['space', 'pass', 'shot', 'marking', 'ball'];
  const NAMES = ['Space score', 'Pass score', 'Shot score', 'Marking pressure', 'Ball accessibility'];
  // Percentage weights sum to 100. These are editorial rules, not fitted rewards
  // or the separately displayed movement/steering weights.
  const SETS = {
    holder: { weights: [15, 45, 20, 5, 15], emphasis: 'pass', why: 'Passing options lead for the default role-route mode; holder does not mean ball carrier.' },
    presser: { weights: [10, 10, 5, 25, 50], emphasis: 'ball', why: 'Ball reach leads for the mode assigned to pursue the previous sampled ball.' },
    runner: { weights: [40, 20, 25, 5, 10], emphasis: 'space', why: 'Room around the player leads for a role-shaped attacking run.' },
    supporter: { weights: [40, 30, 10, 5, 15], emphasis: 'space', why: 'Room around the player leads for midfield support on the role route.' },
    marker: { weights: [10, 10, 5, 60, 15], emphasis: 'marking', why: 'Opponent proximity and ball threat lead for lateral marking mode.' }
  };
  const C = value => Math.max(0, Math.min(1, value));
  const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  const rounded = value => Math.round(C(value) * 1e6) / 1e6;

  function segmentDistance(point, a, b) {
    const dx = b[0] - a[0], dy = b[1] - a[1], square = dx * dx + dy * dy;
    const t = square === 0 ? 0 : C(((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / square);
    return distance(point, [a[0] + t * dx, a[1] + t * dy]);
  }

  // A consistency check, not a security hash. Catches a stale same-seed sample.
  function signature(event) {
    let hash = 2166136261;
    for (const char of JSON.stringify(event.positions)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619) >>> 0;
    return hash.toString(16).padStart(8, '0');
  }

  function scoreSample(event, players, teams) {
    if (teams.length !== 2 || players.length !== 22 || event.positions?.length !== 46 ||
        !event.positions.every(Number.isFinite) || players.some(p => !teams.includes(p.team))) {
      throw new Error('Scores require two teams, 22 roster players and 46 finite position coordinates.');
    }
    const ball = event.positions.slice(0, 2);
    const points = players.map((_, i) => event.positions.slice(2 + 2 * i, 4 + 2 * i));
    return players.map((player, i) => {
      const point = points[i];
      const opponents = players.map((p, j) => p.team !== player.team ? j : -1).filter(j => j >= 0);
      const teammates = players.map((p, j) => p.team === player.team && j !== i ? j : -1).filter(j => j >= 0);
      if (!opponents.length || teammates.length < 3) throw new Error('Incomplete team geometry.');
      const nearestDistance = p => Math.min(...opponents.map(j => distance(p, points[j])));
      // Equal-distance ties use roster order; this is NOT the unexported assigned marker target.
      const target = opponents.reduce((a, b) => distance(point, points[b]) < distance(point, points[a]) ? b : a);
      const separation = distance(point, points[target]);
      // space = C(nearest opponent distance / 10).
      const space = C(separation / 10);
      // pass = mean(best 3 lane qualities); lane(i,j) = C(1-d(i,j)/45)
      //        * C(min opponent-to-closed-segment distance/4) * C(receiver space/10).
      // Hypothetical pass from this player, irrespective of actual possession.
      const lanes = teammates.map(j => C(1 - distance(point, points[j]) / 45) *
        C(Math.min(...opponents.map(k => segmentDistance(points[k], point, points[j]))) / 4) *
        C(nearestDistance(points[j]) / 10)).sort((a, b) => b - a);
      const pass = (lanes[0] + lanes[1] + lanes[2]) / 3;
      const direction = player.team === teams[0] ? 1 : -1;
      const goal = [direction * 52.5, 0], goalDistance = distance(point, goal);
      // shot = C(1-d(goal)/35)^2 * C(forward distance / d(goal)); angle=1 at goal.
      // Zero beyond 35m, role-independent, and hypothetical if the player had the ball.
      const shot = C(1 - goalDistance / 35) ** 2 *
        (goalDistance === 0 ? 1 : C(direction * (goal[0] - point[0]) / goalDistance));
      // marking = C(1-d(nearest opponent)/12) * (0.5 + 0.5*C(1-d(target,ball)/25)).
      // A proximity/threat proxy for every player; not observed defensive action.
      const marking = C(1 - separation / 12) * (0.5 + 0.5 * C(1 - distance(points[target], ball) / 25));
      // ball accessibility = C(1-d(player,ball)/30); no interception-time claim.
      const accessibility = C(1 - distance(point, ball) / 30);
      return { scores: [space, pass, shot, marking, accessibility].map(rounded), target };
    });
  }

  function decompose(scores, mode) {
    const set = SETS[mode];
    if (!set || !Array.isArray(scores) || scores.length !== FEATURES.length ||
        !scores.every(v => Number.isFinite(v) && v >= 0 && v <= 1 && rounded(v) === v)) return null;
    // Integer millionths x integer percentage => exact 1e-8 contribution units.
    // Sum the units before converting; the panel displays an exact decimal sum.
    const units = scores.map((value, i) => Math.round(value * 1e6) * set.weights[i]);
    return { scores: [...scores], weights: set.weights.map(w => w / 100),
      contributions: units.map(v => v / 1e8), value: units.reduce((a, b) => a + b, 0) / 1e8,
      mode, emphasis: set.emphasis, why: set.why };
  }

  function build(match, modes) {
    if (match.seed !== modes.seed || JSON.stringify(match.position_players) !== JSON.stringify(modes.position_players) ||
        modes.players.length !== 22 || modes.samples.length !== match.events.length ||
        modes.players.some((p, i) => p.id !== match.position_players[i])) throw new Error('Mismatched score inputs.');
    return { version: VERSION, label: LABEL, seed: match.seed, position_players: [...match.position_players],
      features: [...FEATURES], weight_sets: SETS,
      samples: match.events.map((event, i) => {
        const row = modes.samples[i];
        if (row.time !== event.time || row.modes.length !== 22 || row.modes.some(m => !Object.hasOwn(SETS, m))) throw new Error('Mismatched sample modes.');
        return { time: event.time, signature: signature(event), modes: [...row.modes],
          players: scoreSample(event, modes.players, match.teams).map(p => [...p.scores, p.target]) };
      }) };
  }

  function current(match, modes, data, index, seconds) {
    if (!data || data.version !== VERSION || data.label !== LABEL || data.seed !== match.seed ||
        JSON.stringify(data.position_players) !== JSON.stringify(match.position_players) ||
        JSON.stringify(data.features) !== JSON.stringify(FEATURES) ||
        JSON.stringify(data.weight_sets) !== JSON.stringify(SETS)) return null;
    const n = match.events.findIndex(e => e.time === seconds), event = match.events[n];
    const sample = data.samples?.[n], mode = modes?.samples?.[n]?.modes?.[index], player = sample?.players?.[index];
    if (!event || sample?.time !== seconds || sample?.modes?.[index] !== mode ||
        sample?.signature !== signature(event) || !Array.isArray(player) || player.length !== 6) return null;
    const target = player[5], targetPlayer = modes.players?.[target];
    if (!Number.isInteger(target) || !targetPlayer || targetPlayer.team === modes.players[index]?.team) return null;
    const result = decompose(player.slice(0, 5), mode);
    return result && { ...result, target: targetPlayer.id };
  }

  const serialized = data => JSON.stringify(data) + '\n';
  const api = { VERSION, LABEL, FEATURES, NAMES, SETS, segmentDistance, signature, scoreSample, decompose, build, current, serialized };
  root.PitchValuation = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
    if (require.main === module) {
      const fs = require('node:fs'), path = require('node:path');
      const args = process.argv.slice(2);
      if (args.length) throw new Error('No arguments: reads existing data and writes player-values sidecars only.');
      const dir = path.join(__dirname, 'data');
      const data = build(JSON.parse(fs.readFileSync(path.join(dir, 'match.json'), 'utf8')),
        JSON.parse(fs.readFileSync(path.join(dir, 'player-modes.json'), 'utf8')));
      fs.writeFileSync(path.join(dir, 'player-values.json'), serialized(data));
      fs.writeFileSync(path.join(dir, 'player-values.js'), 'window.PLAYER_VALUES = ' + serialized(data).trimEnd() + ';\n');
      console.log('Wrote player-values.json/js only: ' + data.samples.length + ' samples × 22 players.');
    }
  }
})(typeof window === 'undefined' ? globalThis : window);
