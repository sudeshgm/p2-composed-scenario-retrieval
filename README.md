# P2 — Composed driving-scenario retrieval ("like this, but…")

Composed retrieval for spatio-temporal driving data: query = reference scenario segment + modification text,
target = scenarios matching a mutated program. Ground truth is **executable**: take a RefAV program `P`
(composition of RefAV atomic functions over Argoverse 2 tracks), mutate one predicate to get `P'`, execute both,
so positives and negatives are correct by construction (relative to the atomic-function oracle).

**Contributions (planned)**
1. **CoScenario** benchmark: multi-answer GT, explicit/near-miss negatives, paraphrase sets, difficulty by mutation family
   (relational, directional, agent class, state, context, compositional) and by trajectory-visible vs appearance-only.
2. Method: training-free CLAY-style conditional similarity modulation over a scenario embedding (from P1), vs trained fusion head and MLLM reranker.
3. PinPoint-style measurements: false-positive rate, paraphrase variance, multi-reference queries.

**Baselines / controls:** text-only, reference-only, late fusion; ignore-reference, ignore-modification, random-modification controls.
**Metrics:** Recall@K / mAP over multi-answer sets, FP rate on explicit negatives, paraphrase variance, per-family breakdown.

**Data:** RefAV scenario-mining val annotations (AV2 sensor val, 150 logs) + AV2 val maps/poses (no sensor data).

**Status:** Exp −1 (mutation-oracle reliability, kill rule <90 % precision on 100 hand-checked triplets) — see `results/e_minus_1/` and `PLAN.md`.
Source idea docs: `cvpr2026_ideas/p2_composed_scenario_retrieval/`.
