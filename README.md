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

Positions are **synthetic/schematic, not tracked data**. At each five-second sample, formation targets incorporate the existing pressing, flank and fatigue phases plus slow shared team-shape drift (180/240-second cycles). Targets settle with a 0.12 smoothing factor (about 39 seconds to close 63% of a change); velocity retains 75% of its previous value and position noise is reduced to 0.06 m Gaussian input. This maintains directional runs while allowing players to roam around their formation anchors. Pressing still pushes/compresses the relevant team in minutes 25–30, flank targets shift in minutes 50–55, and fatigue slows movement in minutes 75–80. Player steps are capped at 3.8 m, or 1.35 m during fatigue. A 0.15 m rounding margin ensures those limits hold after rounding coordinates to 0.1 m. All positions stay inside the 105 × 68 m pitch. A separate seeded random stream preserves non-position events, metrics and evidence; default-seed regeneration is byte-identical.

The ball moves from its **previous position**, with a strict **8 m per five-second sample** travel cap, including rounding. A selected pass targets a schematic recipient, a shot targets the attacking goal, and pressure/recovery targets the actor. That destination is held until arrival; later events do not interrupt an in-flight trip. Travel eases to 40% of remaining distance under the cap and settles within 1 m. This deliberately illustrates continuous trips rather than reconstructing every event's touch or timing; events and evidence are unchanged.

During Play, requestAnimationFrame interpolates every player and ball coordinate from the shared current sample to the next over **250 ms**, using the same playback epoch as Live. Repainting controls does not restart motion. Pause shows the exact current sample; Step/Jump/slider seeks glide from the displayed pose for 250 ms, then settle exactly on the selected sample (including rewinds). These short seek transitions are the only paused-state exception. At the end of the match the final sample holds. The ball has an enlarged white emissive body and dark outline for contrast; its simulated x/y position is unchanged.

Continuity regression checks cover the 8 m ball cap, persistent pass/shot targets, player caps, and each player's mean step below 1.5 m across three seeds. A reversal is a turn greater than 120 degrees between consecutive steps of at least 0.2 m (excluding rounding jitter); fewer than 5% may reverse. Coverage checks require outfield players to span more than 10 m along the pitch, and goalkeepers more than 4 m. The JS harness checks interpolation endpoints/midpoints, repeated updates, seeks, pause, playback boundaries and actual app handlers. It does not verify actual visual smoothness or visibility in a real browser.

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

Verification result: **30 tests passed, 0 failed** (18 Python tests and 12 JavaScript engine/UI tests). The runner derives its total from actual results. Default-seed regeneration verifies all three generated data files byte-for-byte. Non-position bundle hashes match the pre-change data across the default seed and two alternate seeds, covering events, metrics, evidence, templates and labels. No real-browser check was performed for this movement fix.

Measured consecutive-sample distances from the default generated data (metres per five-second sample; 1,079 ball steps and 23,738 player steps):

| Token | Before mean | Before max | After mean | After max |
| --- | ---: | ---: | ---: | ---: |
| Ball | 33.363 | 85.346 | 4.054 | 7.951 |
| Players | 2.765 | 3.912 | 0.649 | 1.500 |

Using the reversal definition above, the aggregate player reversal rate fell from 57.34% to 0% on the default seed. These figures describe schematic trajectories, not measured athletic performance.

The UI interaction tests execute actual app.js handlers in a minimal DOM harness. **No real browser or screenshot verification has been performed in this environment.** Layout, keyboard and direct-file behavior should be checked manually in the intended presentation browser. Native controls, visible focus rings, high-contrast captions, textual evidence and English/Chinese templates are provided; formal accessibility or screen-reader certification is not claimed.

Deliberately omitted: real data and footage, machine learning, cloud, audio, accounts, multiplayer, durable approvals, deployment and submission. The simplified event cadence, proxy possession, scripted changes and linear What-If rules are illustrative. This is not a real match, a calibrated tactical model or a prediction.
