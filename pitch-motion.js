/* Synthetic / schematic positions only. Pure motion state shared with tests. */
(function (root) {
  'use strict';
  const SAMPLE_MS = 250;
  function interpolate(from, to, fraction) {
    const alpha = Math.max(0, Math.min(1, fraction));
    if (alpha === 0) return from.slice();
    if (alpha === 1) return to.slice();
    return from.map((value, i) => value + (to[i] - value) * alpha);
  }
  function createMotion() {
    let state = null;
    function at(now) {
      if (!state) return null;
      return interpolate(state.from, state.to, (now - state.start) / SAMPLE_MS);
    }
    function update(cursor, current, next, playing, started, now, snap = false) {
      if (!snap && state && state.cursor === cursor && state.playing === playing &&
          (!playing || state.start === started)) return;
      const displayed = at(now);
      state = {
        cursor, playing,
        from: playing || snap || !displayed ? current.slice() : displayed,
        to: (playing ? next || current : current).slice(),
        start: playing ? started : now
      };
    }
    return { at, update };
  }
  root.PitchMotion = { SAMPLE_MS, interpolate, createMotion };
})(typeof window === 'undefined' ? globalThis : window);
