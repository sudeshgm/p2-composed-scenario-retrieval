# Exp −1: mutation-oracle reliability (CPU only)

**Status:** pipeline done. Results are from **19 of 150 AV2 val logs** (the RefAV precompute is slow on a shared 8-core CPU, about 7 min per log per worker). Precompute continues in the background, and the stage-2 driver (`src/run_stage2.sh`) regenerates everything when all 150 are done.

## Setup
- Data: RefAV scenario-mining val annotations (1.1 GB). Ground-truth tracks for all objects are used, not detections. AV2 sensor-val maps and poses come to 343 MB; no images or LiDAR.
- Oracle: RefAV atomic functions (`refAV/atomic_functions.py`), called unmodified. We patched only caching and speed: a serial pool, memoisation, an STRtree lane lookup, and a cuboid-distance lower bound that is exact for thresholds ≤ 30 m.
- Unary results are computed for every agent. Relational results are computed per (a, b) pair, with a 30 m centre-distance neighbour gate. The gate is identical in P and P′ and appears in the program source.
- Composition matches RefAV's `@composable_relational` semantics: a matches at t iff ∃b with rel(a,b,t), a∈A(t) and b∈B(t). We checked this against RefAV's own composed execution on a log: the results are identical up to the gate (1 frame out of 1,576).
- Grammar: agent group {vehicle, car, truck, bus, pedestrian, cyclist, ego}, plus 0–2 states, plus an optional relation to a second group with states. Every mutation changes exactly **one** predicate.
- Sources for P and P′ are emitted as RefAV programs (`P.py` / `P_prime.py`).
- `near_intersection` was dropped (too slow on CPU). `is_color` was not used because it needs camera images and a GPU model.

## Families (1000 triplets, balanced)
| family | mutations generated | empty-target rate | identical P/P′ | no reference outside target | selected | median track-Jaccard(P,P′) | median target size (tracks) |
|---|---|---|---|---|---|---|---|
| relational (rel swap among same_lane/heading/following/near/facing) | 7108 | 15.9 % | 0.7 % | 21 % | 200 | 0.33 | 12 |
| directional (ahead↔behind, left↔right) | 1845 | 3.5 % | 1.7 % | 16 % | 200 | 0.50 | 20.5 |
| agent class (car/truck/bus, ped↔cyclist, vehicle→ped/cyclist) | 11493 | 36.8 % | 0.1 % | 4 % | 200 | 0.00 | 5 |
| state (moving→accel/braking/parked, accel↔braking, left↔right turn, …) | 4940 | 15.2 % | 0.0 % | 7 % | 200 | 0.00 | 10 |
| compositional (add a conjunct; drop a conjunct) | 20075 | 46.0 % | 1.2 % | 15 % | 200 | 0.17 | 4 |
| context (weather/lighting) | — | — | — | — | 0 | — | — |

The **context** family is **unsupported**. Neither the annotations nor AV2 have weather, lighting or time-of-day tags, and RefAV has no atomic function for them, even though some RefAV prompts mention snow.

All 45,461 mutations together: empty-target rate **33.9 %**. Over the 1000 selected triplets:
- Track-level Jaccard(P, P′): median 0.15, p90 0.66, max 0.97. 25.9 % have Jaccard = 0 (disjoint).
- Timestamp-level Jaccard: median 0.03.
- Target size: median 9 tracks, p90 159. Answers are spread over a median of 5 logs.
- Explicit negatives per query: median 12. Near-miss negatives (matches of sibling mutations not in P′): median 4.
- Full numbers are in `auto_checks.json` and `gen_stats.json`.

Triplet definition:
- reference = a P-match track and segment that is **not** in P′
- target set = all P′ matches
- negatives = P-matches not in P′
- near-miss = tracks matched by sibling mutations of the same P but not by P′

## Verification
`verify_100/` holds 20 items per family. Each item has `P.py`, `P_prime.py`, `triplet.json` (reference, target and negative track IDs and timestamps) and `bev.png`. `verify_sheet.csv` has blank human columns a/b/c and separate `AGENT_NOT_HUMAN_*` columns.

**Agent-judged precision: 96/100** (a 100/100, b 99/100, c 97/100). This passes the 90 % kill rule, but **this is not the human check**. The agent judge is:
- (a) P′ ≠ P, and an independent numpy re-implementation (raw city-frame boxes) does not say the reference satisfies P′ or that the target fails it.
- (b) A rule-based wording check.
- (c) The independent re-check says the negative does not satisfy P′. For **48/100** the mutated predicate is lane-, map- or turn-based (in_same_lane, following, turning, changing_lanes, ped crossing). Those cannot be independently re-checked, so they rely on the RefAV oracle only.

Failures: 3 directional (the negative does satisfy the flipped direction on 12–16 frames), and 1 agent-class with odd wording ("car in the same lane as a cyclist").

`user_sample/` holds 20 different items (4 per family) with `user_sheet.csv` for the user's hand check.

## Broken or weak mutation types
1. **Directional (ahead↔behind, left↔right).** RefAV `has_objects_in_relative_direction` defaults to `lateral_thresh=inf`, so "ahead" includes diagonally ahead in any lane. Negatives can hold the flipped relation with *another* agent of the same class, and 3/20 failed. Fix: set lateral_thresh (for example 2–3 m), or define the negative as "the same witness b is no longer in that direction".
2. **heading_toward vs facing_toward.** These are hard to tell apart in text. In an earlier 9-log run, 2/20 relational items failed the wording check. Exclude this pair.
3. **Lane relations (in_same_lane / following) with pedestrians or cyclists** read oddly. Restrict them to vehicles.
4. **"stationary" is RefAV's whole-log < 3 m displacement**, so it means "parked", not "stopped now". It is worded as "parked".
5. **Compositional drop** produces P′ ⊇ P, so no reference exists outside the target. Effectively only "add conjunct" is used.
6. Many reference windows are short (< 1 s), especially for accelerating and braking. Add a minimum-duration filter (≥ 1.5 s) before the human check.
7. Appearance and context modifications (colour, weather) are out of scope for this CPU and trajectory-only build.

## Reproduce
`src/prep_logs.py` → `src/precompute.py w n` (shards) → `src/generate.py` → `src/export.py` → `src/verify.py` → `src/stats.py`
