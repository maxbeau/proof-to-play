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

At each five-second step, seeded movement nudges each player toward a compact event-context shape, with a 3.8 m maximum step (45.6 km/h, below the required 10 m/s ceiling); coordinates are clamped to the 105 × 68 m pitch. The generated steps are typically much smaller. In minutes 25–30, the team with more scripted pressure events is pushed forward and its block compresses. In minutes 50–55, player targets shift toward the flank selected by that window's synthetic pass-zone mix. In minutes 75–80, movement is scaled down and capped at 1.35 m for slower recovery movement. A separate seeded random stream keeps position generation deterministic without changing the event stream. The ball sits with the current event's actor for pressure/recovery events, travels partway toward a schematic teammate on a pass, and moves toward that team's attacking goal on a shot. All ball coordinates are clamped to the pitch.

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

Verification result: **19 tests passed, 0 failed** (12 Python tests and 7 JavaScript engine/UI tests, Node v24.22.1). A separate regeneration check confirmed all three data files are byte-identical. The local HTTP smoke check was **blocked** by the sandbox denying socket creation (PermissionError); HTTP delivery is not claimed as verified.

The UI interaction tests execute actual app.js handlers in a minimal DOM harness. **No real browser or screenshot verification has been performed in this environment.** Layout, keyboard and direct-file behavior should be checked manually in the intended presentation browser. Native controls, visible focus rings, high-contrast captions, textual evidence and English/Chinese templates are provided; formal accessibility or screen-reader certification is not claimed.

Deliberately omitted: real data and footage, machine learning, cloud, audio, accounts, multiplayer, durable approvals, 3D graphics, deployment and submission. The simplified event cadence, proxy possession, scripted changes and linear What-If rules are illustrative. This is not a real match, a calibrated tactical model or a prediction.
