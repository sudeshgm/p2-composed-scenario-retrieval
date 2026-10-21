"""Stage 4: stratified verify_100 + user_sample_20: BEV plots, programs, sheets, agent (non-human) checks."""
import json, random, csv, os, sys, collections, shutil
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0,os.path.dirname(__file__))
import generate as G
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from av2.utils.io import read_city_SE3_ego
from scipy.spatial.transform import Rotation as R
random.seed(2)
OUT=Path('results/e_minus_1'); LOGS=Path('/workspace/data/p2_sm_logs/val'); AV2=Path('/workspace/data/av2_val')
T=json.load(open(OUT/'triplets_1000.json'))
FAMS=['relational','directional','agent_class','state','compositional']
_TR={}
def tracks(log):
    """city-frame centres, yaw, category per track"""
    if log in _TR: return _TR[log]
    df=pd.read_feather(LOGS/log/'sm_annotations.feather')
    poses=read_city_SE3_ego(AV2/log)
    out={}
    for u,g in df.groupby('track_uuid'):
        g=g.sort_values('timestamp_ns'); ts=g.timestamp_ns.values
        P=[];Y=[]
        for t,x,y,z,qw,qz in zip(ts,g.tx_m,g.ty_m,g.tz_m,g.qw,g.qz):
            se3=poses[int(t)]; p=se3.transform_point_cloud(np.array([[x,y,z]]))[0]
            yaw=2*np.arctan2(qz,qw)+R.from_matrix(se3.rotation).as_euler('zyx')[0]
            if u=='ego': p=se3.translation; yaw=R.from_matrix(se3.rotation).as_euler('zyx')[0]
            P.append(p[:2]);Y.append(yaw)
        out[u]=dict(ts=ts.astype(np.int64),xy=np.array(P),yaw=np.array(Y),cat=g.category.iloc[0],L=g.length_m.iloc[0],W=g.width_m.iloc[0])
    _TR[log]=out; return out
def kin(tr):
    ts=tr['ts']/1e9; xy=tr['xy']
    if len(ts)<5: return np.zeros(len(ts)),np.zeros(len(ts))
    k=5; xs=np.vstack([np.convolve(xy[:,i],np.ones(k)/k,mode='same') for i in range(2)]).T
    v=np.gradient(xs,ts,axis=0); sp=np.linalg.norm(v,axis=1)
    a=np.gradient(np.convolve(sp,np.ones(k)/k,mode='same'),ts)
    return sp,a
# ---------- independent (non-RefAV) re-implementation of a subset of predicates ----------
def indep_state(tr,s):
    sp,a=kin(tr)
    if s=='moving': return sp>2
    if s=='stationary': return np.full(len(sp), np.linalg.norm(tr['xy'].max(0)-tr['xy'].min(0))<3)
    if s=='accelerating': return a>1.0
    if s=='braking': return a<-1.0
    return None
def indep_rel(log,u,rel,bgroup,bstates):
    TT=tracks(log); A=TT[u]; cats=set(G.GROUPS[bgroup][0]); hit=np.zeros(len(A['ts']),bool)
    if rel not in ('near','dir_forward','dir_backward','dir_left','dir_right','facing_toward'): return None
    for b,B in TT.items():
        if b==u or B['cat'] not in cats: continue
        bmask=np.ones(len(B['ts']),bool)
        for s in bstates:
            r=indep_state(B,s)
            if r is None: return None
            bmask&=r
        com,ia,ib=np.intersect1d(A['ts'],B['ts'],return_indices=True)
        if not len(com): continue
        d=B['xy'][ib]-A['xy'][ia]; c,sn=np.cos(A['yaw'][ia]),np.sin(A['yaw'][ia])
        lx=c*d[:,0]+sn*d[:,1]; ly=-sn*d[:,0]+c*d[:,1]; dist=np.hypot(lx,ly)
        rad=(np.hypot(A['L'],A['W'])+np.hypot(B['L'],B['W']))/2
        if rel=='near': h=dist-rad<=10
        # same geometric definitions as RefAV (lateral_thresh=inf) but recomputed from raw city-frame boxes
        elif rel=='dir_forward': h=(lx>A['L']/2)&(dist-rad<=25)
        elif rel=='dir_backward': h=(lx<-A['L']/2)&(dist-rad<=25)
        elif rel=='dir_left': h=(ly>A['W']/2)&(dist-rad<=15)
        elif rel=='dir_right': h=(ly<-A['W']/2)&(dist-rad<=15)
        elif rel=='facing_toward': h=(np.abs(np.degrees(np.arctan2(ly,lx)))<=22.5)&(dist-rad<=30)
        h&=bmask[ib]&(dist<=30)
        hit[ia[h]]=True
    return hit
def indep_pred(log,u,p):
    """independent evaluation of program p on track u; returns bool mask or None if any predicate uncheckable"""
    TT=tracks(log); A=TT[u]
    if A['cat'] not in G.GROUPS[p['a']['cat']][0]: return np.zeros(len(A['ts']),bool)
    m=np.ones(len(A['ts']),bool)
    for s in p['a']['states']:
        r=indep_state(A,s)
        if r is None: return None
        m&=r
    if p.get('rel'):
        r=indep_rel(log,u,p['rel'],p['b']['cat'],p['b']['states'])
        if r is None: return None
        m&=r
    return m
def win(m,t0=None,t1=None,ts=None):
    if ts is not None and t0 is not None: m=m[(ts>=t0)&(ts<=t1)]
    return int(m.sum())
def agent_judge(t):
    notes=[]
    # (a) delta differs
    a = t['jacc_track']<1 and t['n_Pp']>0
    ref=t['reference']; r=indep_pred(ref['log'],ref['track'],t['Pp'])
    if r is not None:
        tsr=tracks(ref['log'])[ref['track']]['ts']; n=win(r,ref['t0'],ref['t1'],tsr)
        if n>=10: a=False; notes.append(f'indep: reference satisfies P\' on {n} frames in its window')
    tg=t['target_example']; r=indep_pred(tg['log'],tg['track'],t['Pp'])
    if r is not None and r.sum()==0: notes.append('indep: target example never satisfies P\' (indep impl)'); a=False
    # (c) negative
    ng=t['negative_example']; r=indep_pred(ng['log'],ng['track'],t['Pp'])
    if r is None: c='yes(oracle-only)'; notes.append('c: mutated predicate is map/lane/turn-based; no independent check, RefAV oracle only')
    elif r.sum()>=10: c='no'; notes.append(f'indep: negative satisfies P\' on {int(r.sum())} frames')
    else: c='yes'
    # (b) wording
    b='yes'
    odd_ped={'following','in_same_lane','changing_lanes'}
    for role in ('a','b'):
        q=t['Pp'].get(role)
        if q and q['cat'] in ('PEDESTRIAN','BICYCLIST') and (t['Pp'].get('rel') in ('following','in_same_lane') or 'changing_lanes' in q['states']):
            b='no'; notes.append('b: mutated scenario semantically odd for pedestrians/cyclists (lane-following relation)')
    if t['family']=='relational' and {t['P']['rel'],t['Pp']['rel']}<= {'heading_toward','facing_toward'}:
        b='no'; notes.append('b: heading-toward vs facing-toward distinction is not recognisable from text')
    return ('yes' if a else 'no'), b, c, '; '.join(notes)
def plot(t,path):
    fig,ax=plt.subplots(1,3,figsize=(18,6))
    for k,(name,ex) in enumerate([('reference (matches P, not P\')',t['reference']),('target example (matches P\')',t['target_example']),('negative example (matches P, not P\')',t['negative_example'])]):
        TT=tracks(ex['log']); A=TT[ex['track']]; t0,t1=ex['t0']-2e9,ex['t1']+2e9
        axx=ax[k]
        for u,B in TT.items():
            mm=(B['ts']>=t0)&(B['ts']<=t1)
            if not mm.any(): continue
            col='k' if u=='ego' else ('tab:blue' if u==ex['track'] else ('tab:orange' if u in ex['related'] else '0.8'))
            lw=2.5 if col!='0.8' else 0.8
            axx.plot(B['xy'][mm,0],B['xy'][mm,1],'-',color=col,lw=lw,zorder=3 if col!='0.8' else 1)
            axx.plot(B['xy'][mm,0][-1],B['xy'][mm,1][-1],'o' if col!='k' else 's',color=col,ms=5 if col!='0.8' else 2)
        mm=(A['ts']>=ex['t0'])&(A['ts']<=ex['t1'])
        axx.scatter(A['xy'][mm,0],A['xy'][mm,1],c=np.linspace(0,1,mm.sum()),cmap='viridis',s=12,zorder=5)
        c=A['xy'][mm].mean(0) if mm.any() else A['xy'].mean(0)
        axx.set_xlim(c[0]-45,c[0]+45); axx.set_ylim(c[1]-45,c[1]+45); axx.set_aspect('equal')
        axx.set_title(f"{name}\n{A['cat']} {ex['track'][:8]} @ {ex['log'][:8]}\n{(ex['t1']-ex['t0'])/1e9:.1f}s window (dots: matched frames, dark=early)",fontsize=9)
    fig.suptitle(f"[{t['id']} | {t['family']}]  P: {t['P_text']}\nm: \"{t['m']}\"    P': {t['Pp_text']}\nblue=referred track, orange=related (witness) agents, black=ego, grey=others; circles=end position",fontsize=10)
    fig.tight_layout(); fig.savefig(path,dpi=80); plt.close(fig)
def export(items,root,with_agent):
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    rows=[]
    for t in items:
        d=root/t['id']; d.mkdir()
        plot(t,d/'bev.png')
        keep={k:t[k] for k in ['id','family','m','P_text','Pp_text','P_src','Pp_src','reference','target_example','negative_example','n_P','n_Pp','jacc_track','jacc_ts']}
        keep['n_near_miss']=len(t['near_miss_negatives'])
        json.dump(keep,open(d/'triplet.json','w'),indent=1)
        open(d/'P.py','w').write(t['P_src']); open(d/"P_prime.py",'w').write(t['Pp_src'])
        row=dict(id=t['id'],family=t['family'],P=t['P_text'],m=t['m'],P_prime=t['Pp_text'],
                 ref=f"{t['reference']['log']}/{t['reference']['track']}@{t['reference']['t0']}-{t['reference']['t1']}",
                 target=f"{t['target_example']['log']}/{t['target_example']['track']}@{t['target_example']['t0']}-{t['target_example']['t1']}",
                 negative=f"{t['negative_example']['log']}/{t['negative_example']['track']}@{t['negative_example']['t0']}-{t['negative_example']['t1']}",
                 bev=f"{t['id']}/bev.png", human_a_delta_differs='',human_b_m_recognisable='',human_c_negative_true='',human_notes='')
        if with_agent:
            a,b,c,n=agent_judge(t)
            row.update(AGENT_NOT_HUMAN_a=a,AGENT_NOT_HUMAN_b=b,AGENT_NOT_HUMAN_c=c,AGENT_NOT_HUMAN_notes=n)
        rows.append(row)
    with open(root/('verify_sheet.csv' if with_agent else 'user_sheet.csv'),'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return rows
if __name__=='__main__':
    byf=collections.defaultdict(list)
    for t in T: byf[t['family']].append(t)
    fams=[f for f in FAMS if byf[f]]
    v=[]; u=[]
    per=100//len(fams); extra=100-per*len(fams)
    for i,f in enumerate(fams):
        L=byf[f][:]; random.shuffle(L); n=per+(1 if i<extra else 0)
        v+=L[:n]; u+=L[n:n+20//len(fams)+(1 if i<20%len(fams) else 0)]
    rows=export(v,OUT/'verify_100',True)
    export(u,OUT/'user_sample',False)
    ok=[r for r in rows if r['AGENT_NOT_HUMAN_a']=='yes' and r['AGENT_NOT_HUMAN_b']=='yes' and r['AGENT_NOT_HUMAN_c'].startswith('yes')]
    res=dict(n=len(rows),agent_precision=len(ok)/len(rows),
       by_family={f:dict(n=sum(r['family']==f for r in rows),pass_=sum(r['family']==f for r in ok)) for f in fams},
       a_yes=sum(r['AGENT_NOT_HUMAN_a']=='yes' for r in rows),b_yes=sum(r['AGENT_NOT_HUMAN_b']=='yes' for r in rows),
       c_yes=sum(r['AGENT_NOT_HUMAN_c'].startswith('yes') for r in rows),c_oracle_only=sum(r['AGENT_NOT_HUMAN_c']=='yes(oracle-only)' for r in rows))
    json.dump(res,open(OUT/'agent_verification.json','w'),indent=1); print(res)
