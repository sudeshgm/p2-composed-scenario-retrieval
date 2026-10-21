# Build per-log sm_annotations.feather (all GT tracks + ego) from RefAV val annotations.
import pyarrow as pa, sys, pandas as pd, pyarrow.feather as pf
from pathlib import Path
sys.path.insert(0,'/workspace/refav')
import refAV.paths as P; P.AV2_DATA_DIR=Path('/workspace/data/av2sensor')
from refAV.dataset_conversion import add_ego_to_annotation
OUT=Path('/workspace/data/p2_sm_logs/val')
t=pf.read_table('/workspace/data/refav_sm/scenario_mining_val_annotations.feather')
import json, pyarrow.compute as pc
lp=json.load(open('/workspace/data/refav_sm/log_prompt_pairs_val.json'))
t=t.filter(pc.is_in(t['prompt'],pa.array(sorted({v[0] for v in lp.values()}))))
for lid,ps in lp.items():
    g=t.filter(pc.and_(pc.equal(t['log_id'],lid),pc.equal(t['prompt'],ps[0]))).to_pandas()
    g=g.drop(columns=['log_id','prompt','mining_category','generation_type'])
    d=OUT/lid; d.mkdir(parents=True,exist_ok=True)
    g.reset_index(drop=True).to_feather(d/'sm_annotations.feather')
    add_ego_to_annotation(d,d)
print('done',len(list(OUT.iterdir())))
