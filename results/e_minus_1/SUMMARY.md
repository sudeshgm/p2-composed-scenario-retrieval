# Exp −1: mutation-oracle reliability, post-fix run on 150/150 AV2 val logs (CPU only)

## Fixes applied (vs first 19-log run)
1. Directional relations: `lateral_thresh=2.5` m. This is applied as an exact per-(pair, timestamp) post-filter of RefAV's `has_objects_in_relative_direction` output, and it appears in the program source.
2. The heading_toward ↔ facing_toward swap is dropped.
3. `in_same_lane` and `following` are used only when both agents are vehicles.
4. 'stationary' (RefAV: < 3 m displacement over the whole log) is worded as 'parked' in the m text and descriptions.
5. Compositional mutations add a conjunct only (no drop). Contradictory conjuncts (left+right turn, accel+brake, parked+motion) are filtered out.
6. Reference segments must be ≥ 1.5 s. Candidates skipped for this, per family: {"agent_class": 43, "compositional": 24, "relational": 80, "state": 60, "directional": 45}.
8. Negatives are a different track from the reference, or the same track in a disjoint window.
9. Hard negatives only: same RefAV category as the target, matching everything except the mutated predicate. For agent_class, the negative is of the target class and matches P′ minus one state/relation (no class-only negatives). Skips: {"no_valid_negative": 188, "short_target": 227}.
10. Every same-lane/following relation in P or P′ must agree with the AV2 map lane-polygon check on the reference, target and negative windows; disagreeing items are dropped: {"dropped_lane_disagree": {"state": 33, "relational": 35, "compositional": 23, "agent_class": 19}, "kept": 1000}.
11. The 1.5 s minimum also applies to target and negative windows.
12. Wording: pedestrians/cyclists are 'standing still', not 'parked'; 'speeding up (accelerating)' vs 'just moving at a steady speed'; 'the other X' only when classes match.
13. No same-lane/following relation involving a pedestrian or cyclist.
14. Plain-English wording (user feedback): m texts read like 'The same, but the truck is behind the car now, not in front of it.' (old template kept as `m_old`). user_sample items have plain.txt (old search / new search / why the right one should not fit), and BEV panels are labelled LEFT old match / MIDDLE should fit / RIGHT should not fit, with arrows on the key agents. Agent b-criterion also fails jargon or over-long m.
7. Skipped and declared: `near_intersection` (too slow on CPU), `is_color` (needs camera images and a GPU model). The context family (weather/lighting) is unsupported because the annotations have no tags and there is no atomic function for it.

## Auto-checks on 1000 triplets
| family | mutations | empty-target rate | identical | median track-Jaccard | median target size | selected |
|---|---|---|---|---|---|---|
| relational | 7752 | 5.9 % | 0.1 % | 0.386 | 74.5 | 176 |
| directional | 2395 | 4.7 % | 0.3 % | 0.251 | 84.5 | 236 |
| agent_class | 15057 | 18.7 % | 0.0 % | 0.0 | 40.0 | 218 |
| state | 6799 | 9.7 % | 0.0 % | 0.032 | 65.0 | 197 |
| compositional | 18153 | 31.5 % | 0.4 % | 0.143 | 35.0 | 173 |

All mutations: 50156. **Empty-target rate (post-fix): 19.5 %.**
Track-Jaccard(P, P′): median 0.13, p90 0.536; 23.6 % are disjoint. Target size: median 55.0 tracks, p90 949.7. Negatives per query: median 26.0; near-miss median 1.0.

## Independent AV2 map-API check (lane polygon membership) vs RefAV, over all triplets whose P′ uses a lane, map or turn predicate
- Checked: 307; uncheckable: 25
- Target example satisfies P′ by the map check: **85.0 %**
- Negative example fails P′ by the map check: **98.7 %**
- The map check uses its own definitions: same lane = shared or successor/predecessor lane polygon; turning = |Δyaw| > 45° within ±3 s; lane change = moving to a left/right neighbour lane; crossing = inside a crossing polygon buffered by 1 m. Disagreement therefore mixes oracle errors with definition differences.

## Agent-judged verification of 100 (20 per family). This is NOT the human check
**Agent precision: 87 %** (kill rule < 90 %). a = 89/100, b = 100/100, c = 98/100 (oracle-only c: 11).
**Per-family agent precision (new verify_100):** relational 17/20 (85 %), directional 19/20 (95 %), agent_class 15/20 (75 %), state 20/20 (100 %), compositional 16/20 (80 %)

Agent-flagged items:
- t1266 [relational] A car that is turning right and is moving toward the vehicle | m: The same, but the car is driving right behind the vehicle, following it - not moving toward it. | a=yes b=yes c=no | indep: negative satisfies P' on 17 frames
- t0236 [relational] A vehicle that is parked and is driving in the same lane as the moving car | m: The same, but the vehicle is driving right behind the car, following it - not driving in the same lane as it. | a=no b=yes c=yes | indep: reference satisfies P' on 46 frames in its window
- t0996 [relational] A truck that is driving along and is pointed at the car | m: The same, but the truck is driving in the same lane as the car - not pointed at it. | a=no b=yes c=yes | indep: reference satisfies P' on 56 frames in its window
- t0142 [directional] Our own car that is turning right and has the moving vehicle behind it | m: The same, but the vehicle is in front of our own car now, not behind it. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t0353 [agent_class] A car that is changing lanes and is pointed at the other car | m: The same, but the other road user is a truck, not a car. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t1173 [agent_class] Our own car that is turning left and has the moving truck in front of it | m: The same, but the other road user is a bus, not a truck. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t1393 [agent_class] A bus that is changing lanes and has the standing pedestrian on its left | m: The same situation, but with a car doing it instead of a bus. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t0208 [agent_class] A vehicle that is changing lanes and has the parked truck on its right | m: The same, but the other road user is a car, not a truck. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t0948 [agent_class] A car that is changing lanes and is close to the cyclist | m: The same, but the other road user is a pedestrian, not a cyclist. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t1310 [compositional] A truck that is slowing down and has the parked vehicle in front of it | m: The same, but the truck is also changing lanes. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t0080 [compositional] A vehicle that has the other moving vehicle on its right | m: The same, but the vehicle is also changing lanes. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)
- t0035 [compositional] A bus that is driving along and is close to the moving car | m: The same, but the bus is also speeding up. | a=yes b=yes c=no | indep: negative satisfies P' on 14 frames
- t0280 [compositional] A truck that has the moving car on its left | m: The same, but the truck is also changing lanes. | a=no b=yes c=yes | indep: target example never satisfies P' (indep impl)

The human columns in `verify_100/verify_sheet.csv` and `user_sample/user_sheet.csv` (20 items) are still blank and are needed for the real H1 decision.

## Reproduce
`src/prep_logs.py` → `src/precompute.py w n` → `src/run_stage2.sh` (generate → export → verify → stats → summary → commit)