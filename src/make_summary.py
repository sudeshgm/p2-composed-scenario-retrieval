import json, csv, glob, collections
R='results/e_minus_1/'
A=json.load(open(R+'auto_checks.json')); V=json.load(open(R+'agent_verification.json')); M=json.load(open(R+'map_check_agreement.json')); E=json.load(open(R+'export_stats.json'))
nlogs=len(glob.glob('/workspace/data/p2_cache/tables/*.pkl'))
rows=list(csv.DictReader(open(R+'verify_100/verify_sheet.csv')))
fails=[r for r in rows if 'no' in (r['AGENT_NOT_HUMAN_a'],r['AGENT_NOT_HUMAN_b'],r['AGENT_NOT_HUMAN_c'])]
L=[f"# Exp −1: mutation-oracle reliability, post-fix run on {nlogs}/150 AV2 val logs (CPU only)\n",
"## Fixes applied (vs first 19-log run)",
"1. Directional relations: `lateral_thresh=2.5` m. This is applied as an exact per-(pair, timestamp) post-filter of RefAV's `has_objects_in_relative_direction` output, and it appears in the program source.",
"2. The heading_toward ↔ facing_toward swap is dropped.",
"3. `in_same_lane` and `following` are used only when both agents are vehicles.",
"4. 'stationary' (RefAV: < 3 m displacement over the whole log) is worded as 'parked' in the m text and descriptions.",
"5. Compositional mutations add a conjunct only (no drop). Contradictory conjuncts (left+right turn, accel+brake, parked+motion) are filtered out.",
"6. Reference segments must be ≥ 1.5 s. Candidates skipped for this, per family: "+json.dumps(E['skipped_short_reference'])+".",
"8. Negatives are a different track from the reference, or the same track in a disjoint window.",
"9. Hard negatives only: same RefAV category as the target, matching everything except the mutated predicate. For agent_class, the negative is of the target class and matches P′ minus one state/relation (no class-only negatives). Skips: "+json.dumps(E.get('skipped_target_or_negative',{}))+".",
"10. Every same-lane/following relation in P or P′ must agree with the AV2 map lane-polygon check on the reference, target and negative windows; disagreeing items are dropped: "+json.dumps(json.load(open(R+'lane_filter.json')))+".",
"11. The 1.5 s minimum also applies to target and negative windows.",
"12. Wording: pedestrians/cyclists are 'standing still', not 'parked'; 'speeding up (accelerating)' vs 'just moving at a steady speed'; 'the other X' only when classes match.",
"13. No same-lane/following relation involving a pedestrian or cyclist.",
"14. Plain-English wording (user feedback): m texts read like 'The same, but the truck is behind the car now, not in front of it.' (old template kept as `m_old`). user_sample items have plain.txt (old search / new search / why the right one should not fit), and BEV panels are labelled LEFT old match / MIDDLE should fit / RIGHT should not fit, with arrows on the key agents. Agent b-criterion also fails jargon or over-long m.",
"7. Skipped and declared: `near_intersection` (too slow on CPU), `is_color` (needs camera images and a GPU model). The context family (weather/lighting) is unsupported because the annotations have no tags and there is no atomic function for it.\n",
"## Auto-checks on 1000 triplets",
"| family | mutations | empty-target rate | identical | median track-Jaccard | median target size | selected |","|---|---|---|---|---|---|---|"]
for f,d in A['per_family'].items(): L.append(f"| {f} | {d['mutations_generated']} | {100*d['empty_target_rate']:.1f} % | {100*d['identical_rate']:.1f} % | {d['jacc_track_median']} | {d['target_size_median']} | {d['selected']} |")
j=A['jaccard_track_all']; t=A['target_size_tracks']
L+=[f"\nAll mutations: {A['all_mutations']}. **Empty-target rate (post-fix): {100*A['empty_target_rate_all']:.1f} %.**",
f"Track-Jaccard(P, P′): median {j['median']}, p90 {j['p90']}; {100*A['frac_jaccard_track_eq_0']:.1f} % are disjoint. Target size: median {t['median']} tracks, p90 {t['p90']}. Negatives per query: median {A['negatives_per_query']['median']}; near-miss median {A['near_miss_per_query']['median']}.\n",
"## Independent AV2 map-API check (lane polygon membership) vs RefAV, over all triplets whose P′ uses a lane, map or turn predicate",
f"- Checked: {M.get('n',0)}; uncheckable: {M.get('uncheckable',0)}",
f"- Target example satisfies P′ by the map check: **{100*M['target_agreement']:.1f} %**",
f"- Negative example fails P′ by the map check: **{100*M['negative_agreement']:.1f} %**",
"- The map check uses its own definitions: same lane = shared or successor/predecessor lane polygon; turning = |Δyaw| > 45° within ±3 s; lane change = moving to a left/right neighbour lane; crossing = inside a crossing polygon buffered by 1 m. Disagreement therefore mixes oracle errors with definition differences.\n",
"## Agent-judged verification of 100 (20 per family). This is NOT the human check",
f"**Agent precision: {100*V['agent_precision']:.0f} %** (kill rule < 90 %). a = {V['a_yes']}/100, b = {V['b_yes']}/100, c = {V['c_yes']}/100 (oracle-only c: {V['c_oracle_only']}).",
"**Per-family agent precision (new verify_100):** "+", ".join(f"{f} {d['pass_']}/{d['n']} ({100*d['pass_']/max(1,d['n']):.0f} %)" for f,d in V['by_family'].items()),
"\nAgent-flagged items:"]+[f"- {r['id']} [{r['family']}] {r['P']} | m: {r['m']} | a={r['AGENT_NOT_HUMAN_a']} b={r['AGENT_NOT_HUMAN_b']} c={r['AGENT_NOT_HUMAN_c']} | {r['AGENT_NOT_HUMAN_notes']}" for r in fails]+[
"\nThe human columns in `verify_100/verify_sheet.csv` and `user_sample/user_sheet.csv` (20 items) are still blank and are needed for the real H1 decision.",
"\n## Reproduce\n`src/prep_logs.py` → `src/precompute.py w n` → `src/run_stage2.sh` (generate → export → verify → stats → summary → commit)"]
open(R+'SUMMARY.md','w').write("\n".join(L)); print('summary written')
