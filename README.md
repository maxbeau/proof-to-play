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

The schematic formations use fixed formation anchors in roster order (goalkeeper, four defenders, midfielders, forwards). Aster Quills attacks toward +x in a 4-4-2: `(-48.5,0)`; defenders `(-34,-23), (-35,-8), (-35,8), (-34,23)`; midfielders `(-16,-23), (-15,-8), (-15,8), (-16,23)`; forwards `(5,-10), (18,10)`. Mica Lanterns attacks toward −x in a 4-3-3: `(48.5,0)`; defenders `(34,-23), (35,-8), (35,8), (34,23)`; midfielders `(16,-18), (15,0), (16,18)`; forwards `(-5,-18), (-5,0), (-5,18)`. Anchors are formation references, not measured player locations.

### Position steering and role attributes

Positions are **synthetic/schematic, not tracked data**. The generator ports the elementary YUKA-style steering maths directly into Python's standard library; it does not import YUKA, download assets, or add a browser dependency or build step. These are deliberately modest schematic speeds, not calibrated athletic attributes.

| Formation role | maxSpeed (m/s) | maxForce / acceleration (m/s²) | Response (s) | Fatigue factor | Shape-shift scale | Roam radius (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Goalkeeper | 0.80 | 0.45 | 3.8 | 0.92 | 0.12 | 1.8 |
| Defender | 1.35 | 0.65 | 3.0 | 0.78 | 0.38 | 3.6 |
| Midfielder | 2.10 | 0.95 | 2.2 | 0.68 | 0.72 | 5.8 |
| Winger | 3.00 | 1.40 | 1.5 | 0.60 | 1.05 | 9.5 |
| Forward | 2.70 | 1.20 | 1.7 | 0.64 | 0.95 | 7.0 |

Roster order derives roles from the formations: 4-4-2 has two wide midfielders labelled wingers; 4-3-3 has two wide forwards labelled wingers. Every attribute receives independent seeded ±6% variation. Each player also has seeded steering weights (±10%), a different oscillation phase and period, and persistent velocity. The separate steering RNG leaves all event and frozen ball-guide random draws untouched. Attributes are auditable through player_attributes(seed) in pipeline.py; they do not add fields to events or evidence.

Every five-second sample contains **50 internal 0.1-second substeps**. Seek/Arrive computes desired velocity toward an individual target, decelerating with distance inside the braking radius. Steering acceleration is (desired_velocity - current_velocity) / response, clamped to that player's maxForce (unit mass). Velocity integrates acceleration, is limited by that player's maxSpeed, and then integrates position. Target relaxation takes twice the player's response time. Speeds arise from distance, acceleration and individual attributes; there is no common player step cap. The internal paths curve as persistent velocity turns; the unchanged browser still interpolates the stored five-second endpoints.

The behaviour layer combines:

- **OffsetPursuit / formation anchors:** individual anchors follow slow team-shape movement, with defenders shifting less than attackers. Independent role-sized movement cycles avoid synchronized headings.
- **Pursuit:** only the nearest defending outfield player (two in the relevant pressing phase) predicts the ball 1.5 seconds ahead using its previously observed velocity. Assignments hold through a tactical run; they are nearest at assignment time, not reselected every sample.
- **Interpose:** two different markers aim between their assigned opponent and their own goal (30% toward goal), blended with their formation anchor.
- **Space runs and support:** attacking wingers/forwards and two midfield supporters choose among local candidates using nearest-opponent clearance plus distance away from the ball. Supporters use smaller candidate offsets; this is a simple space proxy, not measured pitch control. Other players hold their zones.
- **Wander:** low-weight coherent seeded drift gives each off-ball player an independent idle heading.
- **Separation / social repulsion:** symmetric repulsion applies to both teams within 4 m, strengthening inside 2 m. A local 1.65 m swept hard-disc contact safeguard prevents penetration after integration and along the straight replay segment from the preceding sample (at least 1.50 m after coordinate rounding). This constraint is distinct from the acceleration-limited steering force.

Goalkeepers stay within 3 m longitudinally and 6 m laterally of their own goal anchor. Other roles also have bounded formation zones, preventing ball-chasing collapse. Defender zones are narrower than midfield/attacking zones. All coordinates remain inside the 105 × 68 m pitch and round to 0.1 m.

Independent event teams are not realistic continuous possession runs. The position-only tactical possession state requires three consecutive matching team observations and at least 30 seconds since assignment before a handover. Assignments otherwise change only at phase boundaries. This debouncing does **not** modify event possession or evidence. Pressing (25–30 minutes) increases anchor/pursuit weights and permits a second presser for the team with more scripted pressure events; flank play (50–55) biases winger steering toward the scripted dominant flank; fatigue (75–80) scales individual speed, acceleration and roaming by each player's fatigue factor. No phase applies one identical target jump to everyone.

The ball's previous continuity fix is **preserved exactly**, including its independent random draw sequence and frozen schematic destination-guide paths in _ball_continuity_samples. Those reference paths are not rendered players and do not drive the new player steering. The ball still moves from its previous position toward a held pass/shot/actor destination, easing to 40% of remaining distance with an 8 m/sample cap and settling within 1 m. Ball coordinates are byte-identical to the preceding fix across all three tested seeds. A reference recipient/actor may differ from the displayed steering player's current location: these are schematic continuous trips, not reconstructed touches or physical ball possession.

During Play, requestAnimationFrame interpolates every player and ball coordinate from the shared current sample to the next over **250 ms**, using the same playback epoch as Live. Repainting controls does not restart motion. Pause shows the exact current sample; Step/Jump/slider seeks glide from the displayed pose for 250 ms, then settle exactly on the selected sample (including rewinds). These short seek transitions are the only paused-state exception. At the end of the match the final sample holds. The ball has an enlarged white emissive body and dark outline for contrast; its simulated x/y position is unchanged.

Movement acceptance checks run on seeds 20261024, 20261025 and 42. Speed means use five-second endpoint displacement / 5 (not internal path length). Ordered means must satisfy goalkeeper < defender < midfielder < forward < winger, with **at least 0.04 m/s between adjacent roles**, and each role must have nonidentical player means. Heading checks exclude steps below 0.2 m as quantization jitter: across eight 45° bins, no timestamp may put more than **75%** of moving players in one bin, the mean dominant share must be below **45%**, and mean circular spread (one minus mean unit-heading magnitude) must exceed **0.45**. The captured old model fails the speed and heading thresholds.

Separation must remain **≥1.50 m** for every pair at every stored sample and throughout linear interpolation between consecutive samples (analytical closest-approach check). Arbitrary long Jump/seek transitions can cross other tokens and still need a browser check. Each team's RMS spread must exceed **16 m**, longitudinal extent **35 m**, and lateral extent **30 m**; centroids remain near formation centers and mean centroid-to-ball distance exceeds **18 m**. Individual zone checks include goalkeepers. Bounds and step limits follow individual maxSpeed rather than the obsolete shared cap. Vehicle tests check acceleration, inertia through turns and arrival settling. Reversal checks permit fewer than **10%** of consecutive significant steps to turn more than 120° (the former 5% ceiling assumed shared slow drift); longitudinal coverage remains >10 m outfield and >4 m for goalkeepers. Hard contact correction is a separate positional constraint. Tests also check stable assignments, nearest pressers, ball hashes, three-seed non-position bundle hashes, and byte-identical full artifact regeneration.

The JS harness checks interpolation endpoints/midpoints, repeated updates, seeks, pause, playback boundaries and actual app handlers. It does not verify actual visual smoothness or visibility in a real browser.

The Pitch view builds its field, lines, goal frames, players and ball from Three.js primitives. It uses the local `vendor/three.module.js` and `vendor/OrbitControls.js` files only; Three.js v0.160.0 is MIT licensed and vendored under `vendor/`. There are no downloaded models, textures, remote scripts or other external assets. Its ES modules require HTTP(S) in browsers that block modules under `file://`; if module loading fails, the Pitch view shows the local-server command while the other views remain available.

Default output contains **783 pass attempts and 27 shots**, broad illustrative football-scale magnitudes across both teams. These are design constraints, not calibration against a real match or empirical dataset. Event ordering, actors and outcomes are generated afresh from the seed. The schedule deliberately introduces more pressure actions in minute 25–30, flank-heavy passes in minute 50–55, and longer recovery observations in minute 75–80. The detectors still require measured window changes; time alone does not produce a claim.

Output files:

- data/events.jsonl: raw event stream.
- data/match.json: events, aggregate metrics, evidence, bilingual templates and the broken test fixture.
- data/match.js: the same bundle as a local classic script, enabling direct file opening.

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

Verification: python3 pipeline.py completed successfully; python3 tests/run.py reported **37 passed, 0 failed, 0 skipped** (25 Python tests and 12 JavaScript engine/UI tests). The three-seed checks include exact preservation of ball coordinates and non-position bundle hashes. Full default regeneration remains byte-identical. The runner computes its total from actual Python and JavaScript results; it has no hardcoded test count. The pre-change measurements and ball hashes are retained in tests/movement_baseline.json; tests/movement_metrics.py defines the same measurements for old and new output.

Measured default-seed movement (speed = endpoint displacement / 5 seconds):

| Role | Before mean speed (m/s) | After mean speed (m/s) |
| --- | ---: | ---: |
| Goalkeeper | 0.068 | 0.111 |
| Defender | 0.136 | 0.262 |
| Midfielder | 0.136 | 0.437 |
| Forward | 0.136 | 0.536 |
| Winger | 0.136 | 0.723 |

| Measurement | Before | After |
| --- | ---: | ---: |
| Mean dominant heading-bin share | 0.864 | 0.303 |
| Maximum dominant heading-bin share | 1.000 | 0.545 |
| Mean circular spread | 0.026 | 0.786 |
| Minimum sample separation (m) | 2.102 | 1.655 |
| Minimum interpolated separation (m) | 2.102 | 1.597 |
| Minimum team RMS spread (m) | 19.832 | 18.540 |
| Mean centroid-to-ball distance (m) | 29.765 | 30.089 |
| Ball mean step (m/5s) | 4.054 | 4.054 |
| Ball maximum step (m/5s) | 7.951 | 7.951 |

These figures describe schematic trajectories, not measured athletic performance. They cover 1,079 consecutive intervals and all 22 players. Normal consecutive-sample replay separation is tested analytically; arbitrary Jump/seek transitions and perceived movement still need real-browser inspection.

The UI interaction tests execute actual app.js handlers in a minimal DOM harness. **No real browser or screenshot verification has been performed in this environment.** Layout, keyboard and direct-file behavior should be checked manually in the intended presentation browser. Native controls, visible focus rings, high-contrast captions, textual evidence and English/Chinese templates are provided; formal accessibility or screen-reader certification is not claimed.

Deliberately omitted: real data and footage, machine learning, cloud, audio, accounts, multiplayer, durable approvals, deployment and submission. The simplified event cadence, proxy possession, scripted changes and linear What-If rules are illustrative. This is not a real match, a calibrated tactical model or a prediction.
