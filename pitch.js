/* Synthetic / Simulated Match — local Three.js pitch renderer. */
import * as THREE from 'three';
import { OrbitControls } from 'OrbitControls';

const M = window.MATCH;
const canvas = document.getElementById('pitch-canvas');
const pitchClock = document.getElementById('pitch-clock');
const evidenceLabel = document.getElementById('pitch-evidence');
const pitchTimeline = document.getElementById('pitch-timeline');
const fallback = message => {
  const box = document.getElementById('pitch-fallback');
  if (box) { box.hidden = false; box.textContent = message; }
  if (canvas) canvas.hidden = true;
  window.pitchModuleFailed?.();
};

function clock(seconds) {
  return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
}

function line(points, material) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const object = new THREE.Line(geometry, material);
  scene.add(object);
  return object;
}

function rectangle(x1, z1, x2, z2, material) {
  return line([
    new THREE.Vector3(x1, .08, z1), new THREE.Vector3(x2, .08, z1),
    new THREE.Vector3(x2, .08, z2), new THREE.Vector3(x1, .08, z2),
    new THREE.Vector3(x1, .08, z1)
  ], material);
}

let scene, camera, renderer, controls, pitchGroup, players = [], ball, highlight, activeHighlightId = '';
const teamColors = [0x38d39f, 0xffb25c];
const white = new THREE.LineBasicMaterial({ color: 0xf4fff9, transparent: true, opacity: .9 });

function addPitch() {
  pitchGroup = new THREE.Group();
  scene.add(pitchGroup);
  for (let i = 0; i < 7; i += 1) {
    const material = new THREE.MeshBasicMaterial({ color: i % 2 ? 0x1b714d : 0x196744, side: THREE.DoubleSide });
    const strip = new THREE.Mesh(new THREE.PlaneGeometry(105 / 7, 68), material);
    strip.rotation.x = -Math.PI / 2;
    strip.position.set(-52.5 + 105 / 14 + i * 105 / 7, 0, 0);
    pitchGroup.add(strip);
  }
  rectangle(-52.5, -34, 52.5, 34, white);
  line([new THREE.Vector3(0, .08, -34), new THREE.Vector3(0, .08, 34)], white);
  const circle = new THREE.EllipseCurve(0, 0, 9.15, 9.15, 0, Math.PI * 2, false, 0);
  line(circle.getPoints(64).map(p => new THREE.Vector3(p.x, .08, p.y)), white);
  rectangle(-52.5, -20.16, -36, 20.16, white);
  rectangle(36, -20.16, 52.5, 20.16, white);
  rectangle(-52.5, -9.16, -47, 9.16, white);
  rectangle(47, -9.16, 52.5, 9.16, white);
  const goalMaterial = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 });
  const goal = (x, direction) => {
    const outer = direction < 0 ? x - 5.5 : x + 5.5;
    return line([
      new THREE.Vector3(x, .1, -3.66), new THREE.Vector3(x, 8, -3.66),
      new THREE.Vector3(x, 8, -3.66), new THREE.Vector3(x, 8, 3.66),
      new THREE.Vector3(x, 8, 3.66), new THREE.Vector3(x, .1, 3.66),
      new THREE.Vector3(x, .1, 3.66), new THREE.Vector3(x, .1, -3.66),
      new THREE.Vector3(x, 8, -3.66), new THREE.Vector3(outer, 8, -3.66),
      new THREE.Vector3(outer, 8, -3.66), new THREE.Vector3(outer, .1, -3.66),
      new THREE.Vector3(x, 8, 3.66), new THREE.Vector3(outer, 8, 3.66),
      new THREE.Vector3(outer, 8, 3.66), new THREE.Vector3(outer, .1, 3.66)
    ], goalMaterial);
  };
  goal(-52.5, -1); goal(52.5, 1);
}

function addPlayers() {
  const cylinder = new THREE.CylinderGeometry(.85, 1.05, 2.8, 12);
  const head = new THREE.SphereGeometry(.62, 12, 8);
  M.position_players.forEach((player, index) => {
    const group = new THREE.Group();
    const body = new THREE.Mesh(cylinder, new THREE.MeshStandardMaterial({ color: teamColors[index < 11 ? 0 : 1], roughness: .8 }));
    body.position.y = 1.55;
    const face = new THREE.Mesh(head, new THREE.MeshStandardMaterial({ color: 0xf0c39b, roughness: .9 }));
    face.position.y = 3.25;
    group.add(body, face);
    group.userData.player = player;
    scene.add(group);
    players.push(group);
  });
  ball = new THREE.Mesh(new THREE.SphereGeometry(.65, 16, 12), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .55 }));
  ball.position.y = .75;
  scene.add(ball);
}

function addHighlight() {
  highlight = new THREE.Group();
  scene.add(highlight);
}

function clearHighlight() {
  while (highlight?.children.length) {
    const child = highlight.children[0];
    highlight.remove(child);
    child.geometry?.dispose();
    if (Array.isArray(child.material)) child.material.forEach(material => material.dispose());
    else child.material?.dispose();
  }
}

function rowsForClaim(claim, events) {
  if (!claim) return [];
  const ids = new Set(claim.event_ids);
  return events.filter(event => ids.has(event.id));
}

function showHighlight(claim, events) {
  const key = claim?.id || '';
  if (key === activeHighlightId) return;
  activeHighlightId = key;
  clearHighlight();
  if (!claim) { evidenceLabel.textContent = 'No active evidence window.'; return; }
  const rows = rowsForClaim(claim, events);
  if (!rows.length) return;
  const material = new THREE.MeshBasicMaterial({ color: 0xffcf66, transparent: true, opacity: .22, side: THREE.DoubleSide });
  if (claim.kind === 'flank') {
    const flankRows = rows.filter(row => row.zone !== 'center');
    const ys = flankRows.map(row => row.positions?.[1]).filter(Number.isFinite);
    if (ys.length) {
      const low = Math.min(...ys), high = Math.max(...ys), width = Math.max(.1, high - low);
      const zone = new THREE.Mesh(new THREE.PlaneGeometry(105, width), material);
      zone.rotation.x = -Math.PI / 2; zone.position.set(0, .12, (low + high) / 2); highlight.add(zone);
    }
  } else if (claim.kind === 'pressing') {
    rows.filter(row => row.event_type === 'pressure' && row.positions).forEach(row => {
      const pressMaterial = new THREE.MeshBasicMaterial({ color: 0x82e8c0, transparent: true, opacity: .48 });
      const point = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.15, .1, 24), pressMaterial);
      point.position.set(row.positions[0], .14, row.positions[1]); highlight.add(point);
    });
  }
  evidenceLabel.textContent = `${claim.kind} evidence window · ${clock(claim.window_start)}–${clock(claim.window_end)} · source events ${rows.length}`;
}

function update(seconds, event, claim, events) {
  if (!event?.positions) return;
  const flat = event.positions;
  ball.position.set(flat[0], .75, flat[1]);
  for (let i = 0; i < players.length; i += 1) {
    const x = flat[2 + i * 2], z = flat[3 + i * 2];
    players[i].position.set(x, 0, z);
  }
  pitchTimeline.value = seconds;
  pitchClock.textContent = `${clock(seconds)} / 90:00 · Sample ${Math.floor(seconds / 5)}`;
  showHighlight(claim, events);
}

function resetView() {
  camera.position.set(82, 78, 88);
  controls.target.set(0, 0, 0);
  controls.update();
}

function resize() {
  if (!renderer || !canvas) return;
  const width = Math.max(320, canvas.clientWidth || canvas.parentElement.clientWidth || 900);
  const height = Math.max(360, Math.min(650, width * .58));
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

try {
  if (!canvas || !window.WebGLRenderingContext) throw new Error('WebGL unavailable');
  scene = new THREE.Scene(); scene.background = new THREE.Color(0x09131d);
  camera = new THREE.PerspectiveCamera(42, 1, .1, 500);
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.minDistance = 35; controls.maxDistance = 180;
  scene.add(new THREE.HemisphereLight(0xe8fff3, 0x163725, 2.4));
  const sun = new THREE.DirectionalLight(0xffffff, 1.8); sun.position.set(20, 90, 30); scene.add(sun);
  addPitch(); addPlayers(); addHighlight(); resetView(); resize();
  window.addEventListener('resize', resize);
  document.getElementById('pitch-reset')?.addEventListener('click', resetView);
  const render = () => { controls.update(); renderer.render(scene, camera); requestAnimationFrame(render); };
  render();
  window.pitchViewReady?.({ update, resize, resetView });
} catch (error) {
  fallback('Pitch view needs a local server or the GitHub Pages link; use python3 -m http.server 8000');
}
