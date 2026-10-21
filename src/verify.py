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
# ---------- independent map checks via AV2 map API (lane polygon membership) ----------
from av2.map.map_api import ArgoverseStaticMap
import shapely
_MAP={}
def amap(log):
    if log not in _MAP:
        avm=ArgoverseStaticMap.from_json(next((AV2/log/'map').glob('log_map_archive_*.json')))
        lanes=avm.vector_lane_segments; ids=list(lanes)
        polys=[shapely.Polygon(lanes[i].polygon_boundary[:,:2]) for i in ids]
        pcs=[shapely.Polygon(pc.polygon[:,:2]).buffer(1.0) for pc in avm.vector_pedestrian_crossings.values()]
        _MAP[log]=dict(lanes=lanes,ids=ids,tree=shapely.STRtree(polys),pcs=shapely.STRtree(pcs) if pcs else None)
    return _MAP[log]
_LC={}
def lanes_track(log,u):
    if (log,u) not in _LC: _LC[(log,u)]=lanes_at(log,tracks(log)[u]['xy'])
    return _LC[(log,u)]
def lanes_at(log,xy):
    m=amap(log); return [set(m['ids'][j] for j in m['tree'].query(shapely.Point(*p),predicate='intersects')) for p in xy]
def connected(log,ls):
    m=amap(log); out=set(ls)
    for l in ls:
        L=m['lanes'][l]; out|=set(L.successors)|set(L.predecessors)
    return out
def map_state(log,u,s):
    A=tracks(log)[u]
    if s=='at_ped_crossing':
        m=amap(log)
        if m['pcs'] is None: return np.zeros(len(A['ts']),bool)
        return np.array([len(m['pcs'].query(shapely.Point(*p),predicate='intersects'))>0 for p in A['xy']])
    if s in ('turning_left','turning_right'):
        y=np.unwrap(A['yaw']); ts=A['ts']/1e9; out=np.zeros(len(y),bool)
        for i in range(len(y)):
            j=np.searchsorted(ts,ts[i]+3.0); j=min(j,len(y)-1); k=np.searchsorted(ts,ts[i]-3.0)
            d=y[j]-y[k]
            out[i]= d>np.radians(45) if s=='turning_left' else d<-np.radians(45)
        return out
    if s=='changing_lanes':
        L=lanes_track(log,u); out=np.zeros(len(L),bool); m=amap(log)
        for i in range(1,len(L)):
            for j in range(max(0,i-10),i):
                for la in L[j]:
                    ln=m['lanes'][la]
                    if (ln.left_neighbor_id in L[i] or ln.right_neighbor_id in L[i]) and not (L[i]&connected(log,L[j])): out[i]=True
        return out
    return None
def map_rel(log,u,rel,bgroup,bstates):
    if rel not in ('in_same_lane','following'): return None
    TT=tracks(log); A=TT[u]; cats=set(G.GROUPS[bgroup][0]); hit=np.zeros(len(A['ts']),bool)
    LA=lanes_track(log,u)
    for b,B in TT.items():
        if b==u or B['cat'] not in cats: continue
        bmask=np.ones(len(B['ts']),bool)
        for s in bstates:
            r=indep_state(B,s)
            if r is None: return None
            bmask&=r
        com,ia,ib=np.intersect1d(A['ts'],B['ts'],return_indices=True)
        if not len(com): continue
        d=B['xy'][ib]-A['xy'][ia]
        if (np.hypot(d[:,0],d[:,1])>30).all(): continue
        LBall=lanes_track(log,b); LB=[LBall[j] for j in ib]
        c,sn=np.cos(A['yaw'][ia]),np.sin(A['yaw'][ia]); lx=c*d[:,0]+sn*d[:,1]
        for k,(i,j) in enumerate(zip(ia,ib)):
            if not bmask[j] or np.hypot(*d[k])>30: continue
            same=bool(LB[k] & connected(log,LA[i])) if LA[i] else False
            if rel=='following': same = same and 0<lx[k]<=25+A['L']/2
            if same: hit[i]=True
    return hit
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
        elif rel=='dir_forward': h=(lx>A['L']/2)&(np.abs(ly)<A['W']/2+2.5)&(dist-rad<=25)
        elif rel=='dir_backward': h=(lx<-A['L']/2)&(np.abs(ly)<A['W']/2+2.5)&(dist-rad<=25)
        elif rel=='dir_left': h=(ly>A['W']/2)&(np.abs(lx)<A['L']/2+2.5)&(dist-rad<=15)
        elif rel=='dir_right': h=(ly<-A['W']/2)&(np.abs(lx)<A['L']/2+2.5)&(dist-rad<=15)
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
        if r is None: r=map_state(log,u,s)
        if r is None: return None
        m&=r
    if p.get('rel'):
        r=indep_rel(log,u,p['rel'],p['b']['cat'],p['b']['states'])
        if r is None: r=map_rel(log,u,p['rel'],p['b']['cat'],p['b']['states'])
        if r is None: return None
        m&=r
    return m
MAPPRED={'in_same_lane','following','at_ped_crossing','changing_lanes','turning_left','turning_right','on_road'}
def uses_map(p): return bool((set(p['a']['states'])|{p.get('rel')})&MAPPRED)
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
    if r is None: c='yes(oracle-only)'; notes.append('c: no independent check for this predicate (on_road), RefAV oracle only')
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
    import plain as L
    if any(j in t['m'] for j in L.JARGON) or len(t['m'].split())>30:
        b='no'; notes.append('b: wording still jargon-heavy or too long')
    return ('yes' if a else 'no'), b, c, '; '.join(notes)
def plot(t,path):
    """LEFT old match / MIDDLE should fit / RIGHT should not fit, arrows + labels on the key agents."""
    import plain as L
    fig,ax=plt.subplots(1,3,figsize=(19,7.2))
    panels=[('LEFT: old match\n(fits the old search)',t['reference'],'tab:blue'),('MIDDLE: should fit\n(fits the new search)',t['target_example'],'tab:green'),('RIGHT: should NOT fit\n(fits old, not new)',t['negative_example'],'tab:red')]
    for k,(name,ex,mc) in enumerate(panels):
        TT=tracks(ex['log']); A=TT[ex['track']]; t0,t1=ex['t0']-2e9,ex['t1']+2e9; axx=ax[k]
        for u,B in TT.items():
            mm=(B['ts']>=t0)&(B['ts']<=t1)
            if not mm.any(): continue
            key=u==ex['track'] or u in ex['related']
            col=mc if u==ex['track'] else ('tab:orange' if u in ex['related'] else ('k' if u=='ego' else '0.82'))
            axx.plot(B['xy'][mm,0],B['xy'][mm,1],'-',color=col,lw=2.5 if key or u=='ego' else 0.8,zorder=3 if key else 1)
            if key or u=='ego':
                xy=B['xy'][mm]; e=xy[-1]; d=xy[-1]-xy[max(0,len(xy)-6)]
                if np.hypot(*d)<0.3: yaw=B['yaw'][mm][-1]; d=np.array([np.cos(yaw),np.sin(yaw)])
                d=d/max(1e-6,np.hypot(*d))*4
                axx.annotate('',xy=e+d,xytext=e,arrowprops=dict(arrowstyle='-|>',color=col,lw=2.5,mutation_scale=22),zorder=6)
                lab=('THIS ONE: ' if u==ex['track'] else ('our car' if u=='ego' else 'other: '))+(L.NOUN.get({'REGULAR_VEHICLE':'CAR','PEDESTRIAN':'PEDESTRIAN','BICYCLIST':'BICYCLIST','BUS':'BUS','BOX_TRUCK':'TRUCK','TRUCK':'TRUCK'}.get(B['cat'],'VEHICLE'),'vehicle') if u!='ego' or u==ex['track'] else '')
                axx.annotate(lab,xy=e,xytext=e+np.array([3,3]),fontsize=9,color=col,weight='bold',zorder=7,bbox=dict(boxstyle='round,pad=0.2',fc='white',ec=col,alpha=.85))
        mm=(A['ts']>=ex['t0'])&(A['ts']<=ex['t1'])
        c=A['xy'][mm].mean(0) if mm.any() else A['xy'].mean(0)
        axx.set_xlim(c[0]-40,c[0]+40); axx.set_ylim(c[1]-40,c[1]+40); axx.set_aspect('equal')
        axx.set_title(f"{name}\n{(ex['t1']-ex['t0'])/1e9:.1f} s clip  ({ex['track'][:8]} @ {ex['log'][:8]})",fontsize=11,color=mc,weight='bold')
    fig.suptitle(f"[{t['id']} | {t['family']}]  Old search: {t['P_text']}\nChange: \"{t['m']}\"\nArrows show where each key road user is going at the end of the clip; grey = other traffic, black = our car.",fontsize=11)
    fig.tight_layout(rect=[0,0,1,0.84]); fig.savefig(path,dpi=80); plt.close(fig)
def export(items,root,with_agent):
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    rows=[]
    for t in items:
        d=root/t['id']; d.mkdir()
        plot(t,d/'bev.png')
        keep={k:t.get(k) for k in ['id','family','m','m_old','P_text','Pp_text','P_src','Pp_src','reference','target_example','negative_example','n_P','n_Pp','jacc_track','jacc_ts']}
        keep['n_near_miss']=len(t['near_miss_negatives'])
        json.dump(keep,open(d/'triplet.json','w'),indent=1)
        import plain as L
        open(d/'plain.txt','w').write(f"Old search: {t['P_text']}.\nNew search: {t['Pp_text']}.\nWhy the right one should not fit: {L.why_not(t)}\n")
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
def lane_ok(t):
    """fix 10: every same-lane relation must agree with the AV2 map lane-polygon check, else drop."""
    def hold(ex,p):
        if p.get('rel') not in G.LANE_RELS: return None
        h=map_rel(ex['log'],ex['track'],p['rel'],p['b']['cat'],p['b']['states'])
        if h is None: return 'unk'
        ts=tracks(ex['log'])[ex['track']]['ts']; w=(ts>=ex['t0'])&(ts<=ex['t1'])
        return bool(h[w].any())
    chk=[(t['reference'],t['P'],True),(t['target_example'],t['Pp'],True),(t['negative_example'],t['P'],True),(t['negative_example'],t['Pp'],False)]
    for ex,p,want in chk:
        if t['family']=='agent_class' and ex is t['negative_example'] and p is t['P']: continue
        r=hold(ex,p)
        if r is None: continue
        if r=='unk' or r!=want: return False
    return True
if __name__=='__main__':
    n0=len(T); keep=[]; dropped=collections.Counter()
    for t in T:
        if len(keep)>=1000: break
        if lane_ok(t): keep.append(t)
        else: dropped[t['family']]+=1
    T[:]=keep; json.dump(T,open(OUT/'triplets_1000.json','w'))
    json.dump(dict(dropped_lane_disagree=dropped,kept=len(T)),open(OUT/'lane_filter.json','w'),indent=1); print('lane filter',dropped,len(T),flush=True)
    byf=collections.defaultdict(list)
    for t in T: byf[t['family']].append(t)
    fams=[f for f in FAMS if byf[f]]
    v=[]; u=[]
    per=100//len(fams); extra=100-per*len(fams)
    for i,f in enumerate(fams):
        L=byf[f][:]; random.shuffle(L); n=per+(1 if i<extra else 0)
        v+=L[:n]; u+=L[n:n+20//len(fams)+(1 if i<20%len(fams) else 0)]
    # map-check agreement with RefAV over all triplets whose P' uses a lane/map predicate
    ag=collections.Counter()
    for t in T:
        if not uses_map(t['Pp']): continue
        tg=t['target_example']; r=indep_pred(tg['log'],tg['track'],t['Pp'])
        if r is None: ag['uncheckable']+=1; continue
        ag['n']+=1; ag['target_agree']+= int(r.sum()>0)
        ng=t['negative_example']; r=indep_pred(ng['log'],ng['track'],t['Pp'])
        ag['negative_agree']+= int(r.sum()<10)
    ag=dict(ag); ag['target_agreement']=ag.get('target_agree',0)/max(1,ag.get('n',0)); ag['negative_agreement']=ag.get('negative_agree',0)/max(1,ag.get('n',0))
    json.dump(ag,open(OUT/'map_check_agreement.json','w'),indent=1); print('map agreement',ag,flush=True)
    rows=export(v,OUT/'verify_100',True)
    export(u,OUT/'user_sample',False)
    ok=[r for r in rows if r['AGENT_NOT_HUMAN_a']=='yes' and r['AGENT_NOT_HUMAN_b']=='yes' and r['AGENT_NOT_HUMAN_c'].startswith('yes')]
    res=dict(n=len(rows),agent_precision=len(ok)/len(rows),
       by_family={f:dict(n=sum(r['family']==f for r in rows),pass_=sum(r['family']==f for r in ok)) for f in fams},
       a_yes=sum(r['AGENT_NOT_HUMAN_a']=='yes' for r in rows),b_yes=sum(r['AGENT_NOT_HUMAN_b']=='yes' for r in rows),
       c_yes=sum(r['AGENT_NOT_HUMAN_c'].startswith('yes') for r in rows),c_oracle_only=sum(r['AGENT_NOT_HUMAN_c']=='yes(oracle-only)' for r in rows))
    json.dump(res,open(OUT/'agent_verification.json','w'),indent=1); print(res)
