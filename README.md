# Evidence-to-Action Match Room

Turn synthetic match events into reproducible insights, auditable directional scenarios, and producer-approved bilingual captions.

**Synthetic / Simulated Match.** One newly generated fictional match: Aster Quills vs Mica Lanterns. Player identifiers AQ-01…AQ-11 and ML-01…ML-11 are fictional. No real match data, footage, badges, club or player names are used. This is a local prototype, not a prediction or a submission.

## Demo quickstart

Open **index.html** directly in a modern browser to use Live, Evidence, Scenario and Publish. Their classic scripts and generated data work under `file://`. The Pitch view uses local ES modules, which some browsers block under `file://`; use the local HTTP server or the GitHub Pages URL for Pitch.

Alternatively, from this directory:

    python3 -m http.server 8000 --bind 127.0.0.1

Open `http://127.0.0.1:8000/`. Stop the server with Ctrl+C. This serves only local files. Relative asset paths make this directory suitable for later static hosting, including GitHub Pages. Nothing has been deployed, pushed or submitted. The Pitch module and vendored Three.js files are loaded from this same directory; no network connection is required.

Regenerate the full **generate → metrics → evidence → template** pipeline:

    python3 pipeline.py

Run all acceptance tests:

    python3 tests/run.py

Generation requires Python 3.10+ and its standard library only. The tests additionally require Node 18+ and grep; Node is only a JavaScript test runtime, with no npm or packages. The demo itself requires neither Python nor Node. Verified here with Python 3.12.3 and the installed Node runtime.

## Walkthrough

1. **Live:** Play or step through five-second event samples. The state and trailing ten-minute metrics follow the cursor. Use the three jump buttons: pressing at 30:00, flank at 55:00, recovery at 80:00. No future insight appears before its evidence window ends.
2. **Evidence:** Expand a card's drawer for the entire evidence object and its source events. The deliberately broken claim stays **Needs review**, with a safe template fallback and disabled approval. Its fabricated numbers never appear in a caption.
3. **Scenario:** At a cursor of at least 10:00, freeze a snapshot. Adjust pressing intensity and flank bias. Compare the baseline continuation with the explicitly directional scenario. Later replay movement does not alter the frozen snapshot. Expand details for the source IDs and assumptions.
4. **Publish:** Draft items can become Approved or Rejected. Only verified Approved items reach Broadcast. Rewinding before an item's evidence window ends hides it from Broadcast. Reset or reload clears decisions; there is no persistence or external publishing.
5. Switch Fan / Analyst / Broadcast density and English / 中文. Broadcast density previews in other views do not constitute approval. Only the Publish view's Broadcast output contains approved captions.
6. **Pitch:** At the same five-second cursor as Live, inspect the schematic positions of both fictional teams and the ball. Play, step, jump and either replay slider all move the shared cursor. Drag to rotate, scroll to zoom, right-drag to pan, or press Reset view. When a verified evidence window is active, its flank passing zone or pressing-event locations are highlighted from that claim's source events.

## Studio interface

The five views share a dark broadcast-control-room design: deep navy surfaces, mint replay and verification accents, amber review notices, violet scenario controls, and high-contrast caption output. Local CSS tokens define the system-font typography, spacing, radii, borders and shadows. Clocks, scores and metrics use tabular numbers. The view navigation stays visible while scrolling, with visible keyboard focus and reduced-motion support.

Live pairs a broadcast-style score panel with a replay console, turning-point buttons, metric tiles and ranked fictional player IDs. Evidence drawers lead with window, formula version, source-row count and event-ID bounds, followed by the complete original evidence and source rows. Invalid claims remain visibly held. Scenario places the frozen snapshot and labelled controls beside the comparison table, with assumptions visible. Publish uses a decision board and a separate approved-caption output stage. Pitch has a responsive canvas stage, team legend and shared replay controls; its module-load fallback remains available.

On phones the main workspaces stack into one column, metric tiles use a compact grid, and controls retain generous touch targets. The redesign changes presentation only: deterministic calculations, evidence validation, approval rules, synthetic geometry and shared-cursor behavior remain the same. No dependencies, assets or services were added.

## Five-stage architecture

| Stage | Local implementation | Responsibility |
| --- | --- | --- |
| Ingest | pipeline.py generator; events.jsonl | Seeded fictional events and state |
| Interpret | Python metrics; engine.js recomputation | Event-only arithmetic and window detection |
| Explain | Canonical evidence and strict validation | Admit only exact, recomputed claims |
| Render | index.html, app.js, style.css | Replay, evidence drawers, What-If and approval gate |
| Personalize | Fixed Python/JS templates | Fan / Analyst / Broadcast density and English / Chinese from identical evidence |

The browser rechecks evidence rather than trusting the stored Verified label or generated prose. Python-generated templates are retained as auditable pipeline output; browser templates are independently regenerated and tested for parity. No model, agent service or API participates.

## Data and reproducibility

Fixed default seed: **20261024**. The generator uses a dedicated random.Random instance. There are 1,080 events over 90 simulated minutes, sampled every five seconds. Each has:

- id, time (elapsed seconds), team, player, zone (left / center / right).
- event_type (pass / pressure / shot / recovery), outcome, recovery_seconds (only for recovery events).
- state: cumulative fictional score, possession_team, elapsed_seconds; and a synthetic label.
- positions: 46-number flat array per sample: ball `[x,y]`, followed by the 22 players' `[x,y]` pairs in `position_players` order, all in metres and rounded to 0.1. Each position is labelled **SYNTHETIC / SIMULATED — generated schematic positions; not real tracking data or measured player locations**.

The schematic formations start from formation references in roster order (goalkeeper, four defenders, midfielders, forwards). Aster Quills attacks toward +x in a 4-4-2: `(-48.5,0)`; defenders `(-34,-23), (-35,-8), (-35,8), (-34,23)`; midfielders `(-16,-23), (-15,-8), (-15,8), (-16,23)`; forwards `(5,-10), (18,10)`. Mica Lanterns attacks toward −x in a 4-3-3: `(48.5,0)`; defenders `(34,-23), (35,-8), (35,8), (34,23)`; midfielders `(16,-18), (15,0), (16,18)`; forwards `(-5,-18), (-5,0), (-5,18)`. Anchors are formation references, not measured player locations.

### Pitch player identification

In **Pitch**, click a player token's body or head to open **Player identification**. Click another token to switch players; click empty canvas space or **Close** to dismiss. Dragging, panning, scrolling and multi-touch gestures do not select players. Reset view retains the selection. The panel overlays the right side of the pitch on wide screens and appears below it on narrow screens; it uses the existing dark studio theme and system fonts.

Identification follows the **shared five-second sample cursor** through Play/Pause, Step, Jump, either slider, rewind and end-of-match. It shows the fictional player ID, team, role, current generated mode, simulated speed, all six configured steering weights and the player's seeded role attributes. The timestamp and sample number refer to the stored sample, not the animation interpolating between samples. If the selected player, matching mode data or speed positions are unavailable, the panel removes all previous values and displays a timestamped unavailable message; it never presents the previous sample as current.

**Modes and speeds are synthetic / simulated, not tracked data.** Speed is the Euclidean displacement of that player's stored positions divided by elapsed **match seconds**, using the interval ending at the cursor. For sample 1 (00:05), the starting position is the generator's actual formation at time zero, exported in the sidecar. Later samples use the previous stored sample; sample 1080 (90:00) uses 89:55–90:00. This five-second displacement estimate is not instantaneous velocity, integrated route length or a speed based on the accelerated 250 ms playback interval. Coordinates are rounded to 0.1 m, so displayed speed inherits that quantization.

The always-visible mode legend uses the generator's **assign_behaviours** definitions:

| Mode | Meaning in this generator |
| --- | --- |
| holder | Default assignment, including both goalkeepers: follows the role route. It does **not** identify the ball carrier. |
| presser | One or two defending outfield players chosen nearest the previous sampled ball when assignments change; adds a pursuit term. |
| runner | Attacking wingers and forwards assigned to role-shaped runs. |
| supporter | The first two attacking midfielders in roster order assigned to support. |
| marker | Up to two available defending back-line players assigned distinct nearby attacking runners; adds lateral marking. |

Assignments persist until the generator's debounced possession/phase change. They are exported from the diagnostics of the same integration pass, not inferred from the event actor or guessed from the nearest token. All players follow their role-shaped route with feed-forward velocity and Seek/Arrive correction; holder, runner and supporter are tactical labels, not three separate steering implementations in e172f6a.

| Steering weight | Meaning and actual use in e172f6a |
| --- | --- |
| anchor | Configured formation/route anchoring weight. **Stored but unused as a multiplier**; all players already receive the route's Seek/Arrive correction. |
| pursuit | Multiplies the capped vector toward the previous sampled ball, only for a presser. Inactive for other modes. |
| mark | Multiplies the capped lateral correction toward the assigned opponent, only for a marker. Inactive for other modes. |
| space | Configured space-seeking weight, **stored but unused**; there is no separate space-seeking term in this model. |
| wander | Configured wandering weight, **stored but unused**; variation comes from seeded role routes, not a wander-force term. |
| separation | Multiplies local repulsion when neighbours on either team are within 4 m, with stronger response inside 2 m. The existing contact constraints also remain in effect. |

The panel labels unused and mode-conditional weights explicitly. These are seeded configuration weights, not sampled force magnitudes or a claim that a neighbour is currently within range. Attributes are the actual per-player seeded values: **maxSpeed** is the base speed cap in m/s, **maxForce** the unit-mass acceleration cap in m/s², **response** the velocity response time in seconds, and **stamina** the multiplier on speed and force caps during the inclusive 75:00–80:00 fatigue phase. Display rounds weights/attributes to three decimals; the exported data retains full precision.

**data/player-modes.json** and **data/player-modes.js** follow the existing ball-flight sidecar pattern. They include roster order, fictional team/role metadata, seeded weights/attributes, time-zero positions and **all 1,080 samples × 22 players (23,760 mode assignments)**. Rows have exact sample times and modes in position_players order. The classic script loads locally before the Pitch module without fetch, dependencies or external assets; the existing file:// Pitch fallback and other views remain available if ES modules cannot load. The UI rejects missing samples, unknown modes, mismatched seeds or mismatched roster order rather than reusing stale values.

This separate file keeps mode diagnostics out of match.json/events.jsonl and all evidence objects, preserving the non-position hash checks. Both sidecar formats regenerate byte-identically for the default seed. Full-file SHA-256 tests also pin all five pre-existing generated artifacts to **e172f6a**, including positions and ball flights: this feature changes display/export only, not the simulation, steering, events, metrics or evidence gate.

### Synthetic/schematic ball flight

All positions remain **SYNTHETIC / SIMULATED — generated schematic positions; not real tracking data or measured player locations**. Events, actors, timestamps, outcomes, metrics, evidence objects and the evidence gate stay unchanged. The ball is exactly on its event actor at every stored sample. There is one player integration pass, with no independent frozen ball guide or post-hoc ball-step cap.

Spatial flight data lives separately in `data/ball-flights.json` and its classic-script equivalent `data/ball-flights.js`; it is not inserted into event/evidence objects. Each interval stores its duration, next observed actor, and timed segments with explicit origin, target, start, end and phase. Pass/transfer legs use seeded 18–23 m/s speeds, increasing only when the actual distance requires it, never beyond 25 m/s. Shots and goal-area returns use 25 m/s. An impossible path raises an error before generated artifacts are written.

`pitch-motion.js` maps the 250 ms playback interval to five match seconds and evaluates these segment durations. The ball intercepts the next actor's actual interpolated player path, then enters **held** possession and follows that same player for the remainder. It does not continue a five-second flight chord. A repeated-actor pass is an explicit short knock into that player's run: it flies to the one-second receiving point, waits there, and attaches when the player arrives. Waiting segments have identical endpoints and are tested separately from flight. These are schematic next-touch paths, not new event claims or inferred successful passes.

The old speed test could not measure this representation: a 20 m pass flying for 1 s and then held for 4 s is **20 m/s in flight**, although stored endpoint distance divided by 5 s gives 4 m/s. Its replacement measures every actual flight leg's distance/duration at the unchanged **12–25 m/s** limit, checks joins, deadlines and receiver attachment, and requires a flight for moving pass observations. The JS harness independently measures motion returned by the real animation module, including a 20 m / 1 s flight followed by a hold.

### Shot and rebound rule

Every shot travels from its actor to the attacking goal centre, then returns continuously to the next actor's interception point. The original shot-plus-goal-to-next-actor **125 m / 5 s** acceptance test is retained unchanged. There is no teleport, time reset, goal omission or speed exception. The return is a schematic rebound/save/goal-area return; it is not an additional football event or a claim about a real restart.

Before player integration, the offline generator plans spatial arrival regions for the unchanged shooter and next actor. Players begin converging up to 50 seconds before the touch, using the same velocity/acceleration-limited steering and collision constraints as their runs; the commitment releases over 15 seconds afterward. Role-zone minimum distances allocate the travel budget, reserving steering/rounding headroom. This also handles a next-touch goalkeeper in their own goal area: the shooter must be sufficiently close to the attacking goal to leave time for the long return. No player position is moved after sampling to satisfy the ball test.

### Synthetic/schematic movement

Movement budgets are simulation design targets, not measured athletic performance. Distance uses all 1,079 stored intervals (5,395 seconds). Each five-second sample integrates 50 steps of 0.1 seconds with persistent velocity, acceleration-limited Seek/Arrive steering, individual seeded attributes, debounced tactical assignments and the existing fatigue period.

| Role | Mean target (m/s) | Distance target (km/player) | Base maxSpeed (m/s) | Acceleration (m/s²) | Response (s) | Run cycle (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Goalkeeper | 0.7–1.0 | 3.78–5.40 | 4.0 | 2.0 | 0.85 | 47 |
| Defender | 1.6–1.9 | 8.63–10.25 | 7.2 | 3.2 | 0.75 | 49 |
| Midfielder | 1.9–2.2 | 10.25–11.87 | 8.3 | 3.8 | 0.65 | 58 |
| Forward | 1.8–2.2 | 9.71–11.87 | 9.0 | 4.2 | 0.55 | 66.5 |
| Winger | 1.8–2.2 | 9.71–11.87 | 9.5 | 4.8 | 0.45 | 65 |

Outfield routes use sustained advances/recoveries with ten-second semicircle turnarounds. Complete routes fit within each role zone, instead of clipping targets at a wall and reversing there. Independent phases, periods, clockwise/counterclockwise choices and individually warped lateral-arc timing spread headings even during long runs. Opposing players no longer share an imposed run clock. Goalkeepers retain their smaller curved patrol. The wide defensive screen stays outside ±16 m laterally, inside the unchanged legal role zones, so simultaneous inward wing turns cannot collapse team width below 30 m. Run periods are calibrated to retain the improved role distance budgets after removing artificial backtracking.

Territory follows the displayed actor at debounced tactical changes, with persistent velocity, a 1 m/s limit and gentle acceleration. It no longer jolts every player's route centre toward a newly selected actor every five seconds. Formation movement and individual runs therefore continue smoothly through observation changes.

Collision handling measures the **minimum separation over the entire linear replay chord**. It allows safe crossings that the old fixed start-normal planes incorrectly rejected. Unsafe paths slide along a tangent separating plane feasible at the starting sample. Both sides are checked against available room in each player’s lane; a wall-blocked side is rejected, and the correction is shared according to available room. Corrections never divide by a tiny closest-approach fraction. Local repulsion and removal of closing normal velocity remain. The acceptance floor stays **1.50 m**; formation RMS spread >16 m, length >35 m, width >30 m, bounds, role zones and player speed caps remain unchanged.

Play uses the shared Live playback epoch. Pause, Step, Jump, sliders, end-of-match and manual seek behavior remain covered by the UI harness. The harness is **not a real-browser visual check**: ball flight smoothness, shot rebounds, continuity at joins/seeks, token overlap and heading variety still need a visual browser review.

The Pitch view builds its field, lines, goal frames, players and ball from Three.js primitives. It uses the local `vendor/three.module.js` and `vendor/OrbitControls.js` files only; Three.js v0.160.0 is MIT licensed and vendored under `vendor/`. There are no downloaded models, textures, remote scripts or other external assets. Its ES modules require HTTP(S) in browsers that block modules under `file://`; if module loading fails, the Pitch view shows the local-server command while the other views remain available.

Default output contains **783 pass attempts and 27 shots**, broad illustrative football-scale magnitudes across both teams. These are design constraints, not calibration against a real match or empirical dataset. Event ordering, actors and outcomes are generated afresh from the seed. The schedule deliberately introduces more pressure actions in minute 25–30, flank-heavy passes in minute 50–55, and longer recovery observations in minute 75–80. The detectors still require measured window changes; time alone does not produce a claim.

Output files:

- data/events.jsonl: raw event stream.
- data/match.json: events, aggregate metrics, evidence, bilingual templates and the broken test fixture.
- data/match.js: the same bundle as a local classic script, enabling direct file opening.
- data/ball-flights.json and data/ball-flights.js: spatial-only, timed ball segments for replay.
- data/player-modes.json and data/player-modes.js: complete per-sample modes, seeded player attributes and initial positions for display-only identification.

JSON keys are sorted, UTF-8 output is fixed, and no wall-clock timestamp enters the pipeline. generation_time is an explicitly labelled **simulation clock**, anchored at 2026-01-01T00:00:00Z plus window_end, not the time the program was actually run. This permits byte-identical full regeneration on the supported runtime. Alternative seed: python3 pipeline.py --seed INTEGER; regenerate the default before running default artifact acceptance checks. Cross-version Python random algorithm compatibility is not promised.

## Metric formulas — events-v1.0

Windows are **(window_start, window_end]**. Live metrics use the last ten minutes available, with a shorter opening window. All final values round to two decimal places using floor(nonnegative_value × 100 + 0.5) / 100.

| Metric | Formula |
| --- | --- |
| Possession proxy (%) | Team possession-state samples / all window samples × 100; equal-duration samples, not ball tracking |
| Pressing proxy | Count of pressure events / window minutes; not a validated intensity score |
| Tempo | Pass attempts / window minutes |
| Flank share (%) | Pass attempts in left or right zone / all pass attempts × 100 |
| Recovery time | Mean recovery_seconds over recovery events |
| Key players | Top three by completed passes; ties sorted by fictional player ID |
| Passes / shots | Event counts in window |

An absent pass or recovery denominator yields zero for that metric, meaning no observations, not observed zero recovery time. Empty windows are rejected.

Turning-point detection compares the first and second five-minute halves of each ten-minute window ending on a five-minute boundary. Thresholds: pressing proxy increase ≥1 action/minute; flank share increase ≥15 percentage points; mean recovery increase ≥3 seconds. All comparison numbers are derived inside the same evidence window. “Flank overload” is represented only by flank passing concentration; spatial superiority is not established. Fatigue is a scripted generator phase, not a causal inference from tracking data.

## Evidence and grounding gate

Every verified insight contains event_ids, window_start/end, metric_value, formula_version, fact_check_status, generation_time, comparison, and window entity lists. The gate recomputes the complete expected object from the raw window and requires exact canonical equality:

- Every ID must be the correct ID for that window, in order, with no missing, duplicated, future or substituted event.
- Window metrics and both half-window comparisons must match recomputation; version and deterministic timestamp must match.
- Teams and players must occur in that window. Additional arbitrary prose, numbers or fields invalidate the object.
- Fixed templates interpolate only checked metric values. Evidence IDs, time bounds and version remain attached to every rendered insight in the drawer.
- Invalid claims render only the generic **Needs review** fallback, not their content, and cannot be approved. The fallback is a status notice, not an insight.

Archived insights retain their own explicitly displayed evidence windows. They are not relabelled as current live statistics. The browser also blocks claims whose window extends beyond the replay cursor. Local files and code are trusted inputs; this is not a security boundary against someone modifying the application itself.

## What-If assumptions — scenario-v1.0

Freeze clones the current event state, trailing ten-minute metric baseline and event IDs. The next ten minutes are a **directional continuation**, not generated future events or probabilities:

- Baseline pressure actions = observed pressure actions/minute × 10.
- Scenario pressure actions = baseline × (1 + pressing change / 100).
- Scenario flank share = observed flank share + flank change in percentage points, clamped to 0–100.
- Scenario recovery time = observed recovery time × (1 + pressing change / 200).
- Both controls range from −20 to +20. Zero adjustments reproduce the baseline exactly.

The linear recovery cost is a transparent invented assumption, not a learned relationship. The controls act independently; opponents do not adapt. Fractional pressure counts are directional indices, not discrete event forecasts. No scores, win probabilities or player-performance predictions are produced. Scenario results stay in Scenario and cannot bypass the caption approval queue.

## Microsoft technology mapping — honest local status

Actual runtime technologies: Python standard library, HTML, CSS and JavaScript. No Microsoft-specific service or SDK is integrated. This local demo may be edited in Visual Studio Code or opened in Microsoft Edge; neither editor nor browser usage is claimed as verified deployment evidence.

Azure and Microsoft Foundry are **optional future ideas / not used**. No adapters, accounts, resources or cloud deployments have been created. No LLM API, paid service, remote fonts, analytics, external assets or data feeds are used. There is no backend, GitHub repository creation, push or hackathon submission in this deliverable.

## Tests and limitations

The suite covers seed byte reproducibility, alternate seed behavior, stored-event recomputation, artifact parity, magnitude bounds, three turning points, provenance in every template, malformed claims, score snapshots, local assets, Python/JavaScript agreement, frozen scenario stability, and approval/rejection/rewind behavior. A grep extraction verifies that every generated entity field belongs to the closed fictional allowlist. This is a positive entity-inventory check, not a claim to maintain an exhaustive worldwide real-person-name blacklist; no external name dataset is used.

Verification: **python3 pipeline.py succeeded. python3 tests/run.py reported 51 passed, 0 failed, 0 skipped**: 32 Python checks and 19 JavaScript engine/UI checks. All 41 existing checks remain; identification adds four Python and six JavaScript checks. tests/run.py derives totals from discovery and records them in tests/unified_movement_after.json. The earlier movement-repair results below remain unchanged by this display-only feature.

| Previously failing requirement | Before this repair | Verified after repair |
| --- | --- | --- |
| Pass/shot flight speed | 2,141 stored-chord intervals outside 12–25 m/s | 0 invalid active flight legs; 2509 pass/shot flight legs measured, 18.000000–25.000000 m/s |
| Shot → goal → next actor | 40 paths over 125 m; maximum 202.568060 m | 0 of 81 paths over 125 m; maximum 123.909923 m (seed 42, E0407) |
| Dominant 45-degree heading bin | Default maximum 54.545455% | Maximum 50.000000% across the three seeds |
| Turns >120 degrees | First failing player AQ-02: 141/1,072 = 13.152985%; default worst 255/1,078 = 23.654917% | AQ-02: 48/1078 = 4.452690%; worst across all seeds 75/1076 = 6.970260% (AQ-02, seed 42) |

The flight test changes the **measurement**, not the 12–25 m/s threshold; the 20 m / 1 s example and actual renderer checks are documented above. Shot budget, heading thresholds (maximum ≤50%, mean <40%, circular spread >0.45), reversal ceiling (<10%) and all other acceptance limits remain unchanged.

| Seed | Mean dominant bin | Maximum dominant bin | Circular spread | Minimum replay separation (m) |
| --- | ---: | ---: | ---: | ---: |
| 20261024 | 28.867719% | 50.000000% | 0.813340 | 1.753387 |
| 20261025 | 28.899815% | 50.000000% | 0.818786 | 1.766939 |
| 42 | 28.481960% | 50.000000% | 0.814732 | 1.749286 |

All three original non-position SHA-256 checks pass, including events, metrics, evidence and templates. The evidence gate and event actors/times/outcomes are unchanged. All seven generated artifacts, including flight and player-mode sidecars, regenerate byte-identically. The five pre-existing artifacts are also byte-identical to e172f6a. Ball-to-actor and ball-to-nearest-player distances stay **0 m** at stored samples. Separation stays ≥1.50 m; formation spread/width/length, role zones, bounds, player speed caps and sustained runs all pass. No dependencies, assets, CDN, npm or build step were added.

### Retained movement gains (default seed)

These are endpoint measurements of synthetic positions, not real tracking. “Before” is the partial fix at the start of this task, not the much earlier low-motion baseline. Role distance levels remain close; exact totals change with the repaired paths.

| Role | Before mean m/s | After mean m/s | Before km/player | After km/player |
| --- | ---: | ---: | ---: | ---: |
| Goalkeeper | 0.879806 | 0.855999 | 4.746553 | 4.618114 |
| Defender | 1.819217 | 1.804444 | 9.814677 | 9.734974 |
| Midfielder | 2.121397 | 2.133370 | 11.444936 | 11.509532 |
| Forward | 1.926987 | 1.920192 | 10.396097 | 10.359437 |
| Winger | 2.107471 | 2.110941 | 11.369807 | 11.388525 |

Default outfield longitudinal ranges remain **50–100 m**; both goalkeeper ranges remain **13.5 m**. Full per-player ranges, distances, reversal counts and all 81 shot-path lengths are retained in the measurement report. `tests/unified_movement_before.json` remains the earlier low-motion historical fixture; `partial_repair_baseline` in the updated after-report preserves the baseline for this task.

No real-browser visual check was performed. Still check **ball flight smoothness, goal/rebound behavior, no visible teleport at phase/sample joins or seeks, player overlap, and heading variety** in the intended browser.

The UI interaction tests execute actual app.js handlers in a minimal DOM harness. The identification checks exercise the real pure JS helper for every sample/player, the real panel DOM renderer, mode transitions, speed calculations (including both endpoints), switching and Close, missing/mismatched data, stale-value clearing, and Play/Pause/Step/Jump/slider/rewind/end updates. Synthetic pointer events verify body/head ancestry, empty-space deselection and suppression of drag, pan, pinch, cancel and zoom gestures. A source wiring check confirms recursive player-only raycasting, fresh camera/scene transforms and update ordering; it does **not** execute WebGL or certify physical ray hits. The module-failure handler still exposes the local-server fallback while Live handlers work.

**No real browser or screenshot verification has been performed in this environment.** Still check actual token and empty-space ray hits, panel readability/scrolling at desktop and narrow sizes, switching and Close during playback, and orbit/zoom/pan plus Reset view before and after selecting. Confirm evidence overlays and ball rendering remain visible and file:// still shows the Pitch fallback while the other views work. Layout, keyboard and direct-file behavior need manual review in the intended browser. Native controls, visible focus rings, high-contrast captions, textual evidence and English/Chinese templates are provided; formal accessibility or screen-reader certification is not claimed.

Deliberately omitted: real data and footage, machine learning, cloud, audio, accounts, multiplayer, durable approvals, deployment and submission. The simplified event cadence, proxy possession, scripted changes and linear What-If rules are illustrative. This is not a real match, a calibrated tactical model or a prediction.
