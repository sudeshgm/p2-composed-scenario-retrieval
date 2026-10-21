"""Stage 3: balanced 1000 triplets, auto-check stats, verify_100 + user_sample(20) with BEV plots and sheets."""
import pickle, json, random, collections, csv, sys, os
from pathlib import Path
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
import generate as G, plain as L
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
def segs(ts):
    ts=sorted(ts); out=[[ts[0],ts[0]]]
    for t in ts[1:]:
        if t-out[-1][1] <= 2e8: out[-1][1]=t
        else: out.append([t,t])
    return out
MINREF=1.5e9  # fix 6: reference segment >= 1.5 s
def longest(ts): return max(segs(ts),key=lambda s:s[1]-s[0])
trip=[]; skipped=collections.Counter(); ptr={f:0 for f in FAMS}; nsel={f:0 for f in FAMS}
def nxt(f):
    while ptr[f]<len(byf[f]):
        c=byf[f][ptr[f]]; ptr[f]+=1
        M,W=G.execute(c['P']); M2,W2=G.execute(c['Pp'])
        refs=[k for k in M if k not in M2 and (lambda s:s[1]-s[0])(longest(M[k]))>=MINREF]
        if not refs: skipped[f]+=1; continue
        return c,M,W,M2,W2,refs
    return None
i=0
NWANT=1300  # oversample; verify.py drops lane-check disagreements (fix 10) and keeps 1000
skipneg=collections.Counter()
while len(trip)<NWANT:
    prog=False
    for f in FAMS:
        if len(trip)>=NWANT: break
        r=nxt(f)
        if r is None: continue
        prog=True
        c,M,W,M2,W2,refs=r; i+=1
        rk=random.choice(refs); rs=longest(M[rk])
        T2=[k for k in sorted(M2) if (lambda s:s[1]-s[0])(longest(M2[k]))>=MINREF]  # fix 11
        if not T2: skipneg['short_target']+=1; continue
        tk=random.choice(T2); ts_=longest(M2[tk])
        tcat=G.TABLES[tk[0]]['cats'][tk[1]]
        if c['family']=='agent_class':
            # fix 9: hard negative of the TARGET class that matches P' minus one non-class predicate (no class-only negatives)
            q=json.loads(G.key(c['Pp']))
            if q['a']['states']: q['a']['states']=q['a']['states'][:-1]
            elif q.get('rel'): q={'a':q['a'],'b':None,'rel':None}
            else: skipneg['no_hard_neg']+=1; continue
            Mr,Wr=G.execute(q); pool,Wn=Mr,Wr
        else: pool,Wn=M,W
        # fix 8/9/11: different track from reference (or same track, disjoint window), same RefAV category as target, >=1.5 s
        negs=[k for k in pool if k not in M2 and G.TABLES[k[0]]['cats'][k[1]]==tcat and (lambda s:s[1]-s[0])(longest(pool[k]))>=MINREF
              and (k!=rk or longest(pool[k])[0]>rs[1] or longest(pool[k])[1]<rs[0])]
        if not negs: skipneg['no_valid_negative']+=1; continue
        nk=random.choice(negs); ns=longest(pool[nk])
        # near-miss: other mutations of same P (same family), minus P' matches
        sib=[x for x in ok if G.key(x['P'])==G.key(c['P']) and x['family']==c['family'] and G.key(x['Pp'])!=G.key(c['Pp'])]
        near=set()
        for x in sib[:3]:
            M3,_=G.execute(x['Pp']); near|={k for k in M3 if k not in M2 and G.TABLES[k[0]]['cats'][k[1]]==tcat}
        wit=lambda W,k,seg: sorted({b for b,s in W.get(k,{}).items() if any(seg[0]<=t<=seg[1] for t in s)})
        trip.append(dict(id=f't{i:04d}',family=c['family'],m=L.m_text(c['family'],c['P'],c['Pp']),m_old=c['m'],P=c['P'],Pp=c['Pp'],P_text=L.desc(c['P']),Pp_text=L.desc(c['Pp']),
            P_src=G.to_source(c['P']),Pp_src=G.to_source(c['Pp']),
            reference=dict(log=rk[0],track=rk[1],t0=int(rs[0]),t1=int(rs[1]),related=wit(W,rk,rs)),
            target_set=[[l,u] for l,u in sorted(M2)], target_example=dict(log=tk[0],track=tk[1],t0=int(ts_[0]),t1=int(ts_[1]),related=wit(W2,tk,ts_)),
            negatives=[[l,u] for l,u in sorted(negs)], negative_example=dict(log=nk[0],track=nk[1],t0=int(ns[0]),t1=int(ns[1]),related=wit(Wn,nk,ns)),
            near_miss_negatives=[[l,u] for l,u in sorted(near)],
            n_P=len(M),n_Pp=len(M2),jacc_track=c['jacc_track'],jacc_ts=c['jacc_ts'],P_and_Pp_overlap=len(set(M)&set(M2))))
    if not prog: break
json.dump(dict(skipped_short_reference=skipped,skipped_target_or_negative=skipneg),open(OUT/'export_stats.json','w'))
json.dump(trip,open(OUT/'triplets_1000.json','w'))
print('selected',len(trip),collections.Counter(t['family'] for t in trip))
