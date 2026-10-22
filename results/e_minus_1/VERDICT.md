# Exp −1 verdict: **KILL**

Agent-judged precision on verify_100 was **87 %**, below the **90 %** stop rule (PLAN.md §4.1). P2 work has stopped.

## Numbers (from SUMMARY.md, commit 7faa538)
- 150/150 AV2 val logs, CPU only, 1,000 triplets kept (from 50,156 mutations).
- Empty-target rate after fixes: 19.5 %.
- Independent AV2 map check vs RefAV: 85 % agreement on targets, 98.7 % on negatives.
- verify_100: a (delta differs) 89/100, b (m recognisable) 100/100, c (negative is true) 98/100, overall 87/100.
- Per family: state 20/20, directional 19/20, relational 17/20, compositional 16/20, agent_class 15/20.

## Failure analysis (13 failing items in verify_100)
- **Target doesn't satisfy P′ under the independent check (9 of 13 failures, criterion a):** agent_class t0353, t1173, t1393, t0208, t0948 (class swap: the oracle's target never satisfies P′ under the independent implementation, so the class-filtered RefAV match and the independent class/track check disagree); compositional t1310, t0080, t0280 (all three are the added "is also changing lanes" conjunct, where RefAV's lane-change call and the map-based one disagree); directional t0142 (behind→in front, target never in front by the independent definition).
- **Reference already satisfies P′, so the delta is not real (2 of 13, criterion a):** relational t0236 (same lane→following), t0996 (pointed at→same lane). Relational predicates overlap heavily, so swapping one for another often doesn't change the scene.
- **Negative is actually a positive (2 of 13, criterion c):** relational t1266 (negative satisfies "following" for 17 frames), compositional t0035 (negative satisfies "also speeding up" for 14 frames).
- In short, the oracle's errors come from RefAV atomic functions disagreeing with independent geometry (lane change, class-filtered relations), and from relational predicates that overlap. Wording (b) is no longer a problem.

## Earlier check
The P2 Idea Agent's independent review of the old, pre-fix 20-item user_sample came out at 14/20 (70 %): relational failed 4/4 and directional 2/5. Fixes 1–13 raised this to 87 % but not to 90 %.

## Caveats
- All grading was **agent-judged, not human**. The user's hand check of the new 20-item user_sample was **not done**; the user decided to kill P2 without it.
- The independent checks use their own definitions (see SUMMARY.md), so some "failures" may be differences in definition rather than oracle errors.

## Artifacts
triplets_1000.json (87 MB) was removed from git and is now a release asset: https://github.com/sudeshgm/p2-composed-scenario-retrieval/releases/tag/e-minus-1-results
