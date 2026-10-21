# CPU-first execution plan

Box: 8 CPU, 15 GB RAM, no GPU, ~20 GB free disk (shared with other jobs).

## Data (all CPU, small)
| Item | Source | Size | Status |
|---|---|---|---|
| RefAV scenario-mining val annotations (all GT tracks, 150 logs, 403 prompts) | s3://argoverse/tasks/scenario_mining/scenario_mining_val_annotations.feather | 1.1 GB | downloaded → /workspace/data/refav_sm |
| log_prompt_pairs_val.json | same bucket | 89 KB | downloaded |
| AV2 sensor **val** non-sensor files (annotations, city_SE3_egovehicle, calibration, map) for the 150 logs | s3://argoverse/datasets/av2/sensor/val/<log>/ (excluding sensors/) | 343 MB | downloaded → /workspace/data/av2_val |
| Per-log sm_annotations (+ego) for RefAV | built by src/prep_logs.py | 90 MB | /workspace/data/p2_sm_logs |
| (later, optional) train annotations for training fusion head | scenario_mining_train_annotations.feather | 5.3 GB | not downloaded |
| (not needed) AV2 sensor images/lidar | ~1 TB | — | skip; only needed for appearance branch / is_color |

## Steps
1. **Exp −1 (CPU):** generate ~1000 single-predicate mutation triplets with RefAV atomic functions; execute P, P′ on all 150 val logs; auto-checks; 100 stratified for verification; 20 for user hand check. Kill rule: precision <90 %.
2. **Exp 0 (CPU):** multi-answer stats, near-miss negatives, paraphrases (templates ×3 specificity; LLM paraphrase via API or small local model — CPU OK for 1–3B, slow), stratification.
3. **Exp 1:** baseline encoder = motion statistics + frozen text encoder (MiniLM, CPU OK). CLAY-style modulation is training-free (CPU). Trained fusion head is small MLP (CPU OK). **GPU only for**: P1 learned encoder at scale, MLLM reranker, appearance branch.
4. **Exp 2:** FP rate, paraphrase variance, multi-reference (CPU).
