"""Per-log precomputation of RefAV atomic-function results (unary on all agents, relational on gated pairs).
Usage: python src/precompute.py <worker_idx> <n_workers>. Writes /workspace/data/p2_cache/tables/<log>.pkl (resumable)."""
import sys, os, time, pickle, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import dsl
import refAV.atomic_functions as AF
from refAV.utils import unwrap_func
OUT=dsl.Path('/workspace/data/p2_cache/tables'); OUT.mkdir(parents=True,exist_ok=True)
GATE=30.0
AGENT_CATS=['REGULAR_VEHICLE','LARGE_VEHICLE','BUS','BOX_TRUCK','TRUCK','TRUCK_CAB','VEHICULAR_TRAILER','SCHOOL_BUS','ARTICULATED_BUS','MOTORCYCLE','RAILED_VEHICLE','PEDESTRIAN','BICYCLIST','MOTORCYCLIST','EGO_VEHICLE']
UNARY={k:v for k,v in dsl.STATES.items()}
RELS={'in_same_lane':(AF.in_same_lane,{}),'heading_toward':(AF.heading_toward,dict(max_distance=30)),'following':(AF.following,{}),
      'near':(AF.near_objects,dict(distance_thresh=10)),'facing_toward':(AF.facing_toward,dict(max_distance=30)),
      'dir_forward':(AF.has_objects_in_relative_direction,dict(direction='forward',within_distance=25)),
      'dir_backward':(AF.has_objects_in_relative_direction,dict(direction='backward',within_distance=25)),
      'dir_left':(AF.has_objects_in_relative_direction,dict(direction='left',within_distance=15)),
      'dir_right':(AF.has_objects_in_relative_direction,dict(direction='right',within_distance=15))}
_POS={}
def _centers(log_dir):
    k=str(log_dir)
    if k not in _POS:
        df=pd.read_feather(log_dir/'sm_annotations.feather')
        ego=df[df.category=='EGO_VEHICLE']
        d={}
        for u,g in df.groupby('track_uuid'):
            d[u]=(dict(zip(g.timestamp_ns.values, g[['tx_m','ty_m']].values)), float(np.hypot(g.length_m.iloc[0],g.width_m.iloc[0])/2))
        _POS[k]=d
    return _POS[k]
_orig_cd=AF.cuboid_distance  # memoised version from dsl
def fast_cd(a,b,log_dir,timestamp):
    # exact for every threshold <= GATE: returns a lower bound only when that bound already exceeds GATE
    C=_centers(log_dir)
    if a in C and b in C and timestamp in C[a][0] and timestamp in C[b][0] and a!='ego' and b!='ego':
        lb=np.hypot(*(C[a][0][timestamp]-C[b][0][timestamp]))-C[a][1]-C[b][1]
        if lb>GATE: return lb
    return _orig_cd(a,b,log_dir,timestamp)
AF.cuboid_distance=fast_cd
def run_log(log_id):
    L=dsl.LOGROOT/log_id
    df=pd.read_feather(L/'sm_annotations.feather')
    df=df[df.category.isin(AGENT_CATS)]
    cats=df.groupby('track_uuid').category.first().to_dict()
    ego=[u for u,c in cats.items() if c=='EGO_VEHICLE']
    # city-frame centers for gating (sm annotations are ego-frame; use refAV pos in city frame)
    from refAV.utils import get_nth_pos_deriv
    pos={}
    for u in cats:
        p,t=get_nth_pos_deriv(u,0,L); pos[u]=dict(zip([int(x) for x in t],p[:,:2]))
    allts=sorted(set().union(*[set(v) for v in pos.values()]))
    agents=AF.to_scenario_dict(list(cats.keys()),L) if hasattr(AF,'to_scenario_dict') else None
    from refAV.utils import to_scenario_dict, reconstruct_track_dict
    agents=to_scenario_dict(list(cats.keys()),L)
    unary={}
    t0=time.time()
    peds=to_scenario_dict([u for u,c in cats.items() if c in ('PEDESTRIAN','BICYCLIST')],L)
    for s,src in UNARY.items():
        if s=='near_intersection': continue  # dropped: too slow on CPU for 150 logs, not used by the grammar
        x=peds if s in ('at_ped_crossing','on_road') else agents
        out=eval(src.format(x='x'),{**vars(AF),'np':np,'x':x,'log_dir':L})
        unary[s]={u:set(map(int,ts)) for u,ts in reconstruct_track_dict(out).items()}
    tu=time.time()-t0
    # neighbor gate per (a,b): timestamps where center distance <= GATE
    uu=list(cats); gate={}
    for i,a in enumerate(uu):
        for b in uu:
            if a==b or b=='ego' and False: continue
            if a==b: continue
            com=set(pos[a]).intersection(pos[b])
            if not com: continue
            ts=[t for t in com if np.hypot(*(pos[a][t]-pos[b][t]))<=GATE]
            if ts: gate[(a,b)]=set(ts)
    nbrs={a:[] for a in uu}
    for (a,b) in gate: nbrs[a].append(b)
    rel={}
    for r,(f,kw) in RELS.items():
        fn=unwrap_func(f); tab={}
        for a in uu:
            if not nbrs[a]: continue
            res=fn(a, nbrs[a], L, **kw)
            rd=res[1] if isinstance(res,tuple) else {}
            for b,ts in (rd or {}).items():
                if isinstance(ts,dict): continue
                s=set(map(int,ts)) & gate.get((a,b),set())
                if s: tab[(a,b)]=s
        rel[r]=tab
    pickle.dump(dict(log_id=log_id,cats=cats,unary=unary,rel=rel,gate_pairs=len(gate),t_unary=tu,t_total=time.time()-t0),open(OUT/f'{log_id}.pkl','wb'))
    return time.time()-t0
if __name__=='__main__':
    import json
    w,n=int(sys.argv[1]),int(sys.argv[2])
    logs=sorted(json.load(open('/workspace/data/refav_sm/log_prompt_pairs_val.json')))
    for i,l in enumerate(logs):
        if i%n!=w or (OUT/f'{l}.pkl').exists(): continue
        try: print(l, round(run_log(l),1), flush=True)
        except Exception as e: print('FAIL',l,repr(e),flush=True)
        [c.clear() for c in dsl.U.cache_manager.caches.values()]; _POS.clear(); dsl.clear_memos()
