/* Display only. Reads stored samples and the generator's diagnostics sidecar. */
(function (root) {
  'use strict';
  const MODES = {
    holder: 'Keeps the role route; holder does not mean ball carrier.',
    presser: 'Defending outfielder assigned to pursue the previous sampled ball.',
    runner: 'Attacking winger or forward assigned to a role-shaped run.',
    supporter: 'Attacking midfielder assigned to support on the role route.',
    marker: 'Defender assigned to track an attacking player laterally.'
  };
  const WEIGHTS = ['anchor', 'pursuit', 'mark', 'space', 'wander', 'separation'];
  const ATTRIBUTES = ['maxSpeed', 'maxForce', 'response', 'stamina'];
  const ROLES = ['goalkeeper', 'defender', 'midfielder', 'winger', 'forward'];
  const clock = seconds => Math.floor(seconds / 60).toString().padStart(2, '0') + ':' + (seconds % 60).toString().padStart(2, '0');

  function currentPlayer(match, data, index, seconds) {
    const unavailable = reason => ({ status: 'unavailable', seconds,
      message: 'Selection unavailable at ' + clock(seconds) + ': ' + reason + ' No previous sample is shown.' });
    if (!Number.isInteger(index) || index < 0 || index >= match.position_players.length) return unavailable('player is not in this roster.');
    if (!data || data.seed !== match.seed || data.position_players?.length !== match.position_players.length ||
        !match.position_players.every((id, i) => data.position_players[i] === id)) return unavailable('player-mode data is missing or does not match this replay.');
    const sampleIndex = match.events.findIndex(event => event.time === seconds);
    const event = match.events[sampleIndex];
    const sample = data.samples?.[sampleIndex];
    const player = data.players?.[index];
    const mode = sample?.modes?.[index];
    if (!event || sample?.time !== seconds || !Object.hasOwn(MODES, mode)) return unavailable('no valid mode for this sample.');
    if (player?.id !== match.position_players[index] || !match.teams.includes(player.team) || !ROLES.includes(player.role) ||
        !WEIGHTS.every(key => Number.isFinite(player.weights?.[key])) ||
        !ATTRIBUTES.every(key => Number.isFinite(player[key]))) return unavailable('player attributes do not match.');
    const offset = 2 + index * 2;
    const position = event.positions?.slice(offset, offset + 2);
    const previous = match.events[sampleIndex - 1];
    const from = sampleIndex === 0 ? data.initial?.positions?.[index] : previous?.positions?.slice(offset, offset + 2);
    const fromTime = sampleIndex === 0 ? data.initial?.time : previous?.time;
    if (position?.length !== 2 || from?.length !== 2 || ![...position, ...from, fromTime].every(Number.isFinite) || fromTime >= seconds) {
      return unavailable('positions for simulated speed are missing.');
    }
    return { status: 'selected', index, id: player.id, team: player.team, role: player.role, mode,
      seconds, sampleNumber: sampleIndex + 1, fromTime,
      speed: Math.hypot(position[0] - from[0], position[1] - from[1]) / (seconds - fromTime),
      weights: { ...player.weights },
      attributes: Object.fromEntries(ATTRIBUTES.map(key => [key, player[key]])) };
  }

  function createSelection(match, data) {
    let index = null, seconds = null;
    const state = () => index === null ? { status: 'closed' } : currentPlayer(match, data, index, seconds);
    return {
      select(tokenIndex) { index = tokenIndex; return state(); },
      update(cursor) { seconds = cursor; return state(); },
      clear() { index = null; return state(); },
      state
    };
  }

  function weightStatus(name, mode) {
    if (name === 'pursuit') return mode === 'presser' ? 'Used for ball pursuit' : 'Inactive in this mode';
    if (name === 'mark') return mode === 'marker' ? 'Used for lateral marking' : 'Inactive in this mode';
    if (name === 'separation') return 'Used when neighbours are within 4 m';
    return 'Stored weight; unused in this model';
  }

  function createPanel(match, data, elements, values = root.PLAYER_VALUES) {
    const selection = createSelection(match, data);
    const { panel, content, close } = elements;
    const node = (tag, text, className) => {
      const element = document.createElement(tag);
      element.textContent = text;
      if (className) element.className = className;
      return element;
    };
    function render(state) {
      // Always replace, including missing samples: old values cannot survive a seek.
      content.replaceChildren();
      panel.hidden = state.status === 'closed';
      if (state.status === 'closed') return;
      if (state.status === 'unavailable') {
        content.append(node('p', state.message, 'identification-unavailable'));
        return;
      }
      content.append(node('p', state.id + ' · ' + state.team, 'identification-player'),
        node('p', 'Current sample ' + state.sampleNumber + ' · ' + clock(state.seconds), 'identification-sample'));
      const facts = node('dl', '', 'identification-facts');
      for (const [label, value] of [['Role', state.role], ['Mode', state.mode], ['Simulated speed', state.speed.toFixed(2) + ' m/s']]) {
        const row = node('div', ''); row.append(node('dt', label), node('dd', value)); facts.append(row);
      }
      content.append(facts, node('p', MODES[state.mode], 'muted'));
      const valuation = root.PitchValuation?.current(match, data, values, state.index, state.seconds);
      content.append(node('h4', 'Interpretable value'),
        node('p', "rule-computed schematic scores over synthetic positions — NOT learned Q-values, NOT the paper's trained model, NOT an equilibrium computation", 'identification-score-label'));
      if (!valuation) {
        content.append(node('p', 'Scores unavailable at ' + clock(state.seconds) + ': missing or mismatched valuation sidecar. No previous scores are shown.', 'identification-unavailable'));
      } else {
        content.append(node('p', valuation.value.toFixed(8) + ' / 1', 'identification-value'),
          node('p', 'Active weight set: ' + valuation.mode + ' · ' + valuation.why, 'identification-weight-set'),
          node('p', 'Each contribution = score × weight. Weights sum to 1; these are fixed display rules, separate from steering weights.', 'muted'));
        const scores = node('dl', '', 'identification-scores');
        root.PitchValuation.FEATURES.forEach((key, i) => {
          const emphasized = key === valuation.emphasis;
          const row = node('div', '', 'identification-score' + (emphasized ? ' is-emphasized' : ''));
          row.dataset.feature = key;
          row.append(node('dt', root.PitchValuation.NAMES[i] + (emphasized ? ' · MODE FOCUS' : '')),
            node('dd', valuation.scores[i].toFixed(6) + ' × ' + valuation.weights[i].toFixed(2) + ' = ' + valuation.contributions[i].toFixed(8)));
          scores.append(row);
        });
        content.append(scores,
          node('p', 'Total = ' + valuation.contributions.map(v => v.toFixed(8)).join(' + ') + ' = ' + valuation.value.toFixed(8), 'identification-sum'),
          node('p', 'Marking target proxy: ' + valuation.target + ' (nearest opponent at this sample; not the generator’s assigned target). Pass and shot scores are hypothetical from this position, regardless of possession. Ball accessibility measures proximity, not interception probability.', 'muted'));
      }
      content.append(node('p', 'Speed = position displacement / elapsed match seconds, ' + clock(state.fromTime) + '–' + clock(state.seconds) + '. Sample estimate, not instantaneous or tracked speed.', 'muted'),
        node('h4', 'Steering weights'));
      const weights = node('dl', '', 'identification-weights');
      for (const name of WEIGHTS) {
        const row = node('div', '');
        row.append(node('dt', name), node('dd', state.weights[name].toFixed(3) + ' · ' + weightStatus(name, state.mode)));
        weights.append(row);
      }
      content.append(weights, node('p', 'All players follow a role-shaped route with Seek/Arrive correction. Its anchor weight is not multiplied in this model. Weights are configured values, not measured force contributions.', 'muted'),
        node('h4', 'Seeded role attributes'));
      const attributes = node('dl', '', 'identification-facts');
      for (const [name, unit] of [['maxSpeed', ' m/s'], ['maxForce', ' m/s²'], ['response', ' s'], ['stamina', ' ×']]) {
        const row = node('div', ''); row.append(node('dt', name), node('dd', state.attributes[name].toFixed(3) + unit)); attributes.append(row);
      }
      content.append(attributes, node('p', 'Base attributes; stamina multiplies speed and force caps during 75:00–80:00. All modes and speeds are synthetic / simulated.', 'muted'));
    }
    close.addEventListener('click', () => render(selection.clear()));
    render(selection.state());
    return {
      select(index) { render(index === null ? selection.clear() : selection.select(index)); },
      update(seconds) { render(selection.update(seconds)); },
      state: selection.state
    };
  }

  function tokenIndex(object) {
    // Raycasts hit body/head meshes; the roster index belongs to their group.
    while (object) {
      if (Number.isInteger(object.userData?.playerIndex)) return object.userData.playerIndex;
      object = object.parent;
    }
    return null;
  }

  function attachPicking(canvas, pick, select) {
    let gesture = null;
    const pointers = new Set();
    const moved = event => {
      if (gesture && event.pointerId === gesture.id && Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y) > 5) gesture.dragged = true;
    };
    // Observe events only: OrbitControls keeps its pointer capture and gestures.
    canvas.addEventListener('pointerdown', event => {
      pointers.add(event.pointerId);
      if (pointers.size !== 1 || event.button !== 0 || event.isPrimary === false || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
        gesture = null; return;
      }
      gesture = { id: event.pointerId, x: event.clientX, y: event.clientY, dragged: false };
    });
    canvas.addEventListener('pointermove', moved);
    canvas.addEventListener('pointerup', event => {
      moved(event);
      const click = gesture && gesture.id === event.pointerId && !gesture.dragged && event.button === 0;
      pointers.delete(event.pointerId); gesture = null;
      if (!click) return;
      const box = canvas.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) return;
      select(pick(event.clientX, event.clientY));
    });
    canvas.addEventListener('pointercancel', event => { pointers.delete(event.pointerId); gesture = null; });
    canvas.addEventListener('wheel', () => { gesture = null; }, { passive: true });
  }

  root.PitchIdentification = { MODES, WEIGHTS, currentPlayer, createSelection, createPanel, tokenIndex, attachPicking, weightStatus };
})(typeof window === 'undefined' ? globalThis : window);
