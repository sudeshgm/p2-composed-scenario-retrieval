"""Stage 3: balanced 1000 triplets, auto-check stats, verify_100 + user_sample(20) with BEV plots and sheets."""
import pickle, json, random, collections, csv, sys, os
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
import generate as G
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
random.seed(1)
OUT=Path('results/e_minus_1')
G.load()
C=pickle.load(open('/workspace/data/p2_cache/cands.pkl','rb'))['cands']
FAMS=['relational','directional','agent_class','state','compositional']
ok=[c for c in C if c['status']=='ok']
seen=set(); byf=collections.defaultdict(list)
for c in ok:
    k=G.key(c['P'])+G.key(c['Pp'])
    if k in seen: continue
    seen.add(k); byf[c['family']].append(c)
for f in byf: random.shuffle(byf[f])
# balanced 1000: round robin
sel=[]; quota={f:0 for f in FAMS}
while len(sel)<1000 and any(quota[f]<len(byf[f]) for f in FAMS):
    for f in FAMS:
        if len(sel)<1000 and quota[f]<len(byf[f]): sel.append(byf[f][quota[f]]); quota[f]+=1
def segs(ts):
    ts=sorted(ts); out=[[ts[0],ts[0]]]
    for t in ts[1:]:
        if t-out[-1][1] <= 2e8: out[-1][1]=t
        else: out.append([t,t])
    return out
trip=[]
for i,c in enumerate(sel):
    M,W=G.execute(c['P']); M2,W2=G.execute(c['Pp'])
    refs=[k for k in M if k not in M2]; rk=random.choice(refs)
    rs=max(segs(M[rk]),key=lambda s:s[1]-s[0])
    tk=random.choice(sorted(M2)); ts_=max(segs(M2[tk]),key=lambda s:s[1]-s[0])
    negs=[k for k in M if k not in M2]
    nk=random.choice([k for k in negs if k!=rk] or negs)
    # near-miss: other mutations of same P (same family), minus P' matches
    sib=[x for x in ok if G.key(x['P'])==G.key(c['P']) and x['family']==c['family'] and G.key(x['Pp'])!=G.key(c['Pp'])]
    near=set()
    for x in sib[:3]:
        M3,_=G.execute(x['Pp']); near|={k for k in M3 if k not in M2}
    wit=lambda W,k,seg: sorted({b for b,s in W.get(k,{}).items() if any(seg[0]<=t<=seg[1] for t in s)})
    trip.append(dict(id=f't{i:04d}',family=c['family'],m=c['m'],P=c['P'],Pp=c['Pp'],P_text=G.describe(c['P']),Pp_text=G.describe(c['Pp']),
        P_src=G.to_source(c['P']),Pp_src=G.to_source(c['Pp']),
        reference=dict(log=rk[0],track=rk[1],t0=int(rs[0]),t1=int(rs[1]),related=wit(W,rk,rs)),
        target_set=[[l,u] for l,u in sorted(M2)], target_example=dict(log=tk[0],track=tk[1],t0=int(ts_[0]),t1=int(ts_[1]),related=wit(W2,tk,ts_)),
        negatives=[[l,u] for l,u in sorted(negs)], negative_example=dict(log=nk[0],track=nk[1],t0=int(min(M[nk])),t1=int(max(M[nk])),related=sorted(W.get(nk,{}))),
        near_miss_negatives=[[l,u] for l,u in sorted(near)],
        n_P=len(M),n_Pp=len(M2),jacc_track=c['jacc_track'],jacc_ts=c['jacc_ts'],P_and_Pp_overlap=len(set(M)&set(M2))))
json.dump(trip,open(OUT/'triplets_1000.json','w'))
print('selected',len(trip),collections.Counter(t['family'] for t in trip))
