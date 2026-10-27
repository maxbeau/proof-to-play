# Pitch panel valuation verification — 2026-10-27

Local implementation against HEAD `0c15bf3`. Panel-only upgrade; no video work, commit, push, upload, submission-page change, external data, new dependency, backend or application build step. No credential files were read or copied.

## Scope and files

Modified:

- `pitch-identification.js`: adds the five-feature value panel, active mode set/reason, exact contribution sum, focus badge and honest missing-data state.
- `style.css`: adds only identification-score styles; keeps existing responsive panel placement/scrolling.
- `index.html`: adds two local classic-script references for panel valuation; no other markup change.
- `README.md`: precise formulas, weights, generation instructions, caveats and sample values; preserves the pre-existing local Related work section exactly once, updating its future-tense valuation paragraph.
- `tests/browser.test.js`: loads the new panel dependencies and adds the new test module; none of the existing assertions or expectations change.
- `tests/unified_movement_after.json`: automatically refreshed acceptance count only; movement metrics remain identical.

Added:

- `pitch-valuation.js`: pure geometric score/decomposition functions plus a CLI that writes only the new sidecars.
- `data/player-values.json`: all 1,080 samples × 22 players × five features and nearest-opponent indices.
- `data/player-values.js`: identical payload in the local classic-script format.
- `tests/player-valuation.test.js`: eight additional JavaScript checks.
- `tests/test_valuation.py`: four additional Python checks using the existing three-seed bundles.
- `tests/panel-valuation-verification.md`: this report.

Protected source files (`pipeline.py`, `app.js`, `engine.js`, `pitch.js`, `pitch-motion.js`) and legacy expectation files (`tests/test_pipeline.py`, `tests/player-identification.test.js`, `tests/run.py`) remain byte-identical to HEAD.

## Formulas

`C(z)=max(0,min(1,z))`; `d` is Euclidean distance in metres; `p` is the player, `b` the ball, `O` opponents, `T` teammates excluding self, `g` attacking goal centre, and `s=+1` for AQ / `-1` for ML.

- Space: `C(min(o∈O) d(p,o)/10)`.
- Pass: mean of the best three teammate lanes, with `L(p,t)=C(1-d(p,t)/45) × C(min(o∈O) d(o,closed segment[p,t])/4) × C(min(o∈O) d(t,o)/10)`.
- Shot: `C(1-d(p,g)/35)^2 × C(s×(g.x-p.x)/d(p,g))`, using angle factor 1 at the goal centre.
- Marking: `C(1-d(p,o*)/12) × (0.5+0.5×C(1-d(o*,b)/25))`, with `o*` the nearest opponent, ties by roster order.
- Ball accessibility: `C(1-d(p,b)/30)`.
- Value: `Σ score_k × weight_k`; scores are rounded once to six decimals, and integer millionths × integer weight percentages produce exact eight-decimal contributions and total.

Weights in **space, pass, shot, marking, ball** order:

| Mode | Weights | Focus |
| --- | --- | --- |
| holder | .15, .45, .20, .05, .15 | Pass |
| presser | .10, .10, .05, .25, .50 | Ball |
| runner | .40, .20, .25, .05, .10 | Space |
| supporter | .40, .30, .10, .05, .15 | Space |
| marker | .10, .10, .05, .60, .15 | Marking |

These are fixed explanatory display weights, not the movement model's seeded steering weights. Every weight set sums to 1. The current mode and its rationale appear alongside all five feature contributions.

## Sample 360 / 30:00 / event E0360

| Feature | AQ-07 presser score | Contribution | AQ-03 marker score | Contribution | ML-10 runner score | Contribution |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Space | 0.821340 | 0.08213400 | 0.832586 | 0.08325860 | 0.821340 | 0.32853600 |
| Pass | 0.638793 | 0.06387930 | 0.659073 | 0.06590730 | 0.482263 | 0.09645260 |
| Shot | 0.000000 | 0.00000000 | 0.000000 | 0.00000000 | 0.031610 | 0.00790250 |
| Marking | 0.194410 | 0.04860250 | 0.306178 | 0.18370680 | 0.235400 | 0.01177000 |
| Ball | 0.576667 | 0.28833350 | 0.722471 | 0.10837065 | 0.360165 | 0.03601650 |
| **Value** | | **0.48294930** | | **0.44124335** | | **0.48067760** |

Nearest-opponent proxies: AQ-07 → ML-10; AQ-03 → ML-07; ML-10 → AQ-07.

Sanity checks:

- AQ-03 is 8.325863 m from ML-07, who is on the sampled ball; its marking pressure 0.306178 exceeds distant attacker AQ-10's 0.
- AQ-03 is 91.981411 m from its attacking goal. Its shot score is 0, as are the AQ goalkeeper and all four AQ defenders at this sample.
- ML-10 is 28.7 m from its attacking goal; its shot score is a small nonzero 0.031610.
- AQ-07 is 12.7 m from the ball: `1−12.7/30 = 0.576667` after rounding.
- AQ-02 is labelled marker but has pressure 0 because its nearest opponent is outside 12 m. Mode emphasis does not manufacture pressure.

## Honesty and limitations

Visible in both panel and README:

> rule-computed schematic scores over synthetic positions — NOT learned Q-values, NOT the paper's trained model, NOT an equilibrium computation

The available sidecar does not contain persistent assigned marking targets. Pressure on the actual assignment cannot be recovered honestly from the stored samples; that claim is omitted. The displayed score is explicitly labelled as a nearest-opponent geometry proxy, with the opponent ID shown. Pass/shot opportunities are hypothetical regardless of possession. Ball reach is proximity only, not interception probability. No score is a calibrated football probability or trained EDMS implementation.

Real-browser/WebGL, desktop/narrow visual layout, physical ray hits and manual scroll/accessibility checks were not performed. Node DOM tests execute the actual renderer and existing app handlers; they do not establish a screenshot or real-browser result.

## Verification results

`python3 tests/run.py`: **63 passed, 0 failed, 0 skipped** (36 Python + 27 JavaScript). Pre-extension suite: **51 passed, 0 failed, 0 skipped** (32 Python + 19 JavaScript). The existing 51 expectations remain unchanged; 12 checks were added. Python's full run took 165.164 seconds.

Two actual `node pitch-valuation.js` regenerations produced byte-identical new JSON and JS sidecars. New checks also compare two separate Node processes for each of seeds **20261024, 20261025 and 42**: each seed must reproduce itself exactly, while different seeds must produce distinct hashes. Range/decomposition coverage is 356,400 feature scores across the three seeds.

`node --check` passed for the new generator, modified panel and added JavaScript tests. `git diff --check` passed.

Existing generated artifacts match HEAD byte-for-byte (SHA-256):

| File | SHA-256 |
| --- | --- |
| data/match.json | f7bb1e77d69119d87e360c0e696a8a17439388d0af40402e0d6155ec4379e042 |
| data/match.js | 03a5faab76624e9ab6bd499bdf28d2c7fe7e16f850ff624ba31d3d4cd7dd4c2c |
| data/events.jsonl | 03d81a8d4d6ebfdb6ced2202662bf403334b87c26a29ddc934134c20bb617424 |
| data/ball-flights.json | 656da64ea65d9a1c90adf26bd14440ec1bde5d4a9083ee5af0192579fa851701 |
| data/ball-flights.js | 8dcf4a6e799a537469c9269bdab71c4d7630609c134369483998b2a9973f6988 |
| data/player-modes.json | e61a176c26a1e560e47ef65523d70353d4dfbbe69a827b02b9945457e51a55c6 |
| data/player-modes.js | 0f357cc1c576130ea66a45545192df21adb9cc8802963a61cd88a82826e8dd90 |

New sidecar hashes:

- `data/player-values.json`: e9c98bc317c14649ef2bb5cb9c260bfe0d19824e2a958ec30670927b8c5f0a16
- `data/player-values.js`: f5cdee78cd15165a42433b6bd9cb9ee15b155bb159d8d8353cdd38614febd3fe
