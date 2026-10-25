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
  function ballAt(flight, seconds) {
    const time = Math.max(0, Math.min(flight.seconds, seconds));
    const segment = flight.segments.find(part => time <= part.end) || flight.segments.at(-1);
    const duration = segment.end - segment.start;
    return interpolate(segment.origin, segment.target, duration > 0 ? (time - segment.start) / duration : 1);
  }
  function createMotion() {
    let state = null;
    function at(now) {
      if (!state) return null;
      const fraction = (now - state.start) / SAMPLE_MS;
      const pose = interpolate(state.from, state.to, fraction);
      if (state.playing && state.flight) {
        const ball = ballAt(state.flight, fraction * state.flight.seconds);
        pose[0] = ball[0]; pose[1] = ball[1];
      }
      return pose;
    }
    function update(cursor, current, next, playing, started, now, snap = false, flight = null) {
      if (!snap && state && state.cursor === cursor && state.playing === playing &&
          (!playing || state.start === started)) return;
      const displayed = at(now);
      state = {
        cursor, playing, flight,
        from: playing || snap || !displayed ? current.slice() : displayed,
        to: (playing ? next || current : current).slice(),
        start: playing ? started : now
      };
    }
    return { at, update };
  }
  root.PitchMotion = { SAMPLE_MS, interpolate, ballAt, createMotion };
})(typeof window === 'undefined' ? globalThis : window);
