"""Stage 2: enumerate base programs P, single-predicate mutations P', execute both from precomputed RefAV tables,
build triplets, auto-checks, balanced sample of 1000."""
import pickle, json, random, itertools, collections, sys
from pathlib import Path
import numpy as np
random.seed(0)
TAB=Path('/workspace/data/p2_cache/tables'); OUT=Path('results/e_minus_1'); OUT.mkdir(parents=True,exist_ok=True)
GROUPS={  # name -> (RefAV categories, noun)
 'VEHICLE':(["EGO_VEHICLE","ARTICULATED_BUS","BOX_TRUCK","BUS","LARGE_VEHICLE","MOTORCYCLE","RAILED_VEHICLE","REGULAR_VEHICLE","SCHOOL_BUS","TRUCK","TRUCK_CAB"],'vehicle'),
 'CAR':(['REGULAR_VEHICLE'],'car'),
 'TRUCK':(['BOX_TRUCK','TRUCK','TRUCK_CAB'],'truck'),
 'BUS':(['BUS','SCHOOL_BUS','ARTICULATED_BUS'],'bus'),
 'PEDESTRIAN':(['PEDESTRIAN'],'pedestrian'),
 'BICYCLIST':(['BICYCLIST'],'cyclist'),
 'EGO':(['EGO_VEHICLE'],'ego vehicle'),
}
STATE_TXT={'moving':'moving','stationary':'parked','accelerating':'speeding up (accelerating)','braking':'braking','turning_left':'turning left',
 'turning_right':'turning right','changing_lanes':'changing lanes','near_intersection':'near an intersection','at_ped_crossing':'on a pedestrian crossing','on_road':'on the road'}
REL_TXT={'in_same_lane':'in the same lane as','heading_toward':'heading toward','following':'following','near':'near',
 'facing_toward':'facing toward','dir_forward':'with {b} ahead of it','dir_backward':'with {b} behind it','dir_left':'with {b} to its left','dir_right':'with {b} to its right'}
PED_OK={'moving','stationary','at_ped_crossing','on_road'}
VEH_STATES=['moving','stationary','accelerating','braking','turning_left','turning_right','changing_lanes']
STATE_SWAP={'moving':['accelerating','braking','stationary'],'accelerating':['braking','moving'],'braking':['accelerating'],'stationary':['moving'],
 'turning_left':['turning_right'],'turning_right':['turning_left'],'changing_lanes':['turning_left','turning_right'],
 'at_ped_crossing':['on_road'],'on_road':['at_ped_crossing']}
NONDIR=['in_same_lane','heading_toward','following','near','facing_toward']
FLIP={'dir_forward':'dir_backward','dir_backward':'dir_forward','dir_left':'dir_right','dir_right':'dir_left'}
CLASS_SWAP={'CAR':['TRUCK','BUS'],'TRUCK':['CAR','BUS'],'BUS':['CAR','TRUCK'],'PEDESTRIAN':['BICYCLIST'],'BICYCLIST':['PEDESTRIAN'],'VEHICLE':['PEDESTRIAN','BICYCLIST']}
LANE_RELS={'in_same_lane','following'}
def is_veh(g): return g in ('VEHICLE','CAR','TRUCK','BUS','EGO')
MOTION={'moving','accelerating','braking','turning_left','turning_right','changing_lanes'}
def compatible(st):
    st=set(st)
    if {'turning_left','turning_right'}<=st or {'accelerating','braking'}<=st: return False
    if 'stationary' in st and st&MOTION: return False
    return True
def valid(p):
    if not compatible(p['a']['states']) or (p.get('b') and not compatible(p['b']['states'])): return False
    return not (p.get('rel') in LANE_RELS and not (is_veh(p['a']['cat']) and is_veh(p['b']['cat'])))
def is_ped(g): return g in ('PEDESTRIAN','BICYCLIST')
def allowed_states(g): return sorted(PED_OK) if g=='PEDESTRIAN' else (['moving','stationary','accelerating','braking','turning_left','turning_right'] if g=='BICYCLIST' else VEH_STATES)
def key(p): return json.dumps(p,sort_keys=True)
def stxt(s,g):  # fix 12: no 'parked pedestrian/cyclist'; accelerating distinct from moving
    if s=='stationary' and is_ped(g): return 'standing still'
    return STATE_TXT[s]
def describe(p):
    a=GROUPS[p['a']['cat']][1]; st=[stxt(s,p['a']['cat']) for s in p['a']['states']]
    s=(' and '.join(st)+' ' if st else '')+a if len(st)==1 else a+(' that is '+' and '.join(st) if st else '')
    if p.get('rel'):
        b=GROUPS[p['b']['cat']][1]; bs=' '.join(stxt(x,p['b']['cat']) for x in p['b']['states'])
        bb=('a '+(bs+' ' if bs else '')+b)
        r=REL_TXT[p['rel']]
        s+=' '+(r.format(b=bb) if '{b}' in r else r+' '+bb)
    return s
# ---------- source in RefAV atomic functions ----------
SRC_STATE={'moving':"has_velocity({x}, log_dir, min_velocity=2)",'stationary':"stationary({x}, log_dir)",'accelerating':"accelerating({x}, log_dir, min_accel=1.0)",
 'braking':"accelerating({x}, log_dir, min_accel=-np.inf, max_accel=-1.0)",'turning_left':"turning({x}, log_dir, direction='left')",'turning_right':"turning({x}, log_dir, direction='right')",
 'changing_lanes':"changing_lanes({x}, log_dir)",'near_intersection':"near_intersection({x}, log_dir)",'at_ped_crossing':"at_pedestrian_crossing({x}, log_dir)",'on_road':"on_road({x}, log_dir)"}
SRC_REL={'in_same_lane':"in_same_lane(a, b, log_dir)",'heading_toward':"heading_toward(a, b, log_dir, max_distance=30)",'following':"following(a, b, log_dir)",
 'near':"near_objects(a, b, log_dir, distance_thresh=10)",'facing_toward':"facing_toward(a, b, log_dir, max_distance=30)",
 'dir_forward':"has_objects_in_relative_direction(a, b, log_dir, direction='forward', within_distance=25, lateral_thresh=2.5)",'dir_backward':"has_objects_in_relative_direction(a, b, log_dir, direction='backward', within_distance=25, lateral_thresh=2.5)",
 'dir_left':"has_objects_in_relative_direction(a, b, log_dir, direction='left', within_distance=15, lateral_thresh=2.5)",'dir_right':"has_objects_in_relative_direction(a, b, log_dir, direction='right', within_distance=15, lateral_thresh=2.5)"}
def src_obj(v,g,states):
    cats=GROUPS[g][0]
    if g=='VEHICLE': l=[f"{v} = get_objects_of_category(log_dir, category='VEHICLE')"]
    elif len(cats)==1: l=[f"{v} = get_objects_of_category(log_dir, category='{cats[0]}')"]
    else: l=[f"{v} = scenario_or([" + ", ".join(f"get_objects_of_category(log_dir, category='{c}')" for c in cats)+"])"]
    return l+[f"{v} = "+SRC_STATE[s].format(x=v) for s in states]
def to_source(p):
    l=src_obj('a',p['a']['cat'],p['a']['states'])
    if p.get('rel'):
        l+=src_obj('b',p['b']['cat'],p['b']['states'])
        l+=["b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'",
            "out = scenario_and([" + SRC_REL[p['rel']] + ", b_gate])"]
    else: l+=["out = a"]
    return "\n".join(l)
# ---------- executor over tables ----------
TABLES={}
LAT=2.5
def cap_dirs(T):
    import pandas as pd
    df=pd.read_feather(f"/workspace/data/p2_sm_logs/val/{T['log_id']}/sm_annotations.feather")
    df=df[df.track_uuid.isin(set(T['cats']))]
    pos={(u,int(t)):(x,y,qw,qz,l,w) for u,t,x,y,qw,qz,l,w in zip(df.track_uuid,df.timestamp_ns,df.tx_m,df.ty_m,df.qw,df.qz,df.length_m,df.width_m)}
    for r in ['dir_forward','dir_backward','dir_left','dir_right']:
        new={}
        for (a,b),tss in T['rel'][r].items():
            keep=set()
            for t in tss:
                A=pos.get((a,t)); B=pos.get((b,t))
                if A is None or B is None: continue
                yaw=2*np.arctan2(A[3],A[2]); dx,dy=B[0]-A[0],B[1]-A[1]
                lx=np.cos(yaw)*dx+np.sin(yaw)*dy; ly=-np.sin(yaw)*dx+np.cos(yaw)*dy
                if a=='ego': hw,hl=1.0,4.877/2+1.422; back=4.877-hl
                else: hw,hl=A[5]/2,A[4]/2; back=-hl
                if r in ('dir_forward','dir_backward'): ok=-hw-LAT<ly<hw+LAT
                else: ok=back-LAT<lx<hl+LAT
                if ok: keep.add(t)
            if keep: new[(a,b)]=keep
        T['rel'][r]=new
def load():
    for f in sorted(TAB.glob('*.pkl')):
        T=pickle.load(open(f,'rb')); cap_dirs(T); TABLES[f.stem]=T
        if not T.get('all_ts'):  # timestamps seen per track (union of unary tables)
            at={}
            for d in T['unary'].values():
                for u,ts in d.items(): at.setdefault(u,set()).update(ts)
            T['all_ts']=at
def obj_set(T,g,states):
    cs=set(GROUPS[g][0]); d={}
    for u,c in T['cats'].items():
        if c not in cs: continue
        ts=None
        for s in states:
            x=T['unary'][s].get(u,set()); ts=x if ts is None else ts & x
            if not ts: break
        if ts is None: ts=None  # all timestamps
        if ts is not None and not ts: continue
        d[u]=ts
    return d
def execute(p,want_w=True):
    """returns {(log,uuid): set(ts)} and witnesses {(log,uuid): {b: set(ts)}}"""
    M={}; W={}
    for log,T in TABLES.items():
        A=obj_set(T,p['a']['cat'],p['a']['states'])
        if not p.get('rel'):
            for u,ts in A.items():
                if ts is None: ts=T['all_ts'].get(u,set())
                if ts: M[(log,u)]=ts
            continue
        B=obj_set(T,p['b']['cat'],p['b']['states'])
        for (a,b),ts in T['rel'][p['rel']].items():
            if a not in A or b not in B: continue
            s=set(ts)
            if A[a] is not None: s&=A[a]
            if B[b] is not None: s&=B[b]
            if s:
                M.setdefault((log,a),set()).update(s)
                if want_w: W.setdefault((log,a),{})[b]=s
    return M,W
def mutations(p):
    out=[]
    a=p['a']; rel=p.get('rel')
    # relational
    if rel in NONDIR:
        for r in NONDIR:
            if r==rel or {r,rel}=={'heading_toward','facing_toward'}: continue   # fix 2
            if r in LANE_RELS and not (is_veh(p['a']['cat']) and is_veh(p['b']['cat'])): continue  # fix 3
            oth='the other' if p['a']['cat']==p['b']['cat'] else 'the'  # fix 12
            out.append(('relational',{**p,'rel':r},f"but {REL_TXT[r]} {oth} {GROUPS[p['b']['cat']][1]} instead of {REL_TXT[rel]} it"))
    if rel in FLIP:
        r=FLIP[rel]; side={'dir_forward':'ahead of','dir_backward':'behind','dir_left':'to the left of','dir_right':'to the right of'}
        out.append(('directional',{**p,'rel':r},f"but with the {GROUPS[p['b']['cat']][1]} {side[r]} it instead of {side[rel]} it"))
    # agent class
    for role in (['a','b'] if rel else ['a']):
        g=p[role]['cat']
        for g2 in CLASS_SWAP.get(g,[]):
            st=p[role]['states']
            if any(s not in allowed_states(g2) for s in st): continue
            q=json.loads(key(p)); q[role]['cat']=g2
            who='the main agent' if role=='a' else 'the other agent'
            out.append(('agent_class',q,f"but with a {GROUPS[g2][1]} instead of a {GROUPS[g][1]}" + (" as the other agent" if role=='b' else "")))
    # state swap (on a)
    for i,s in enumerate(a['states']):
        for s2 in STATE_SWAP.get(s,[]):
            if s2 in a['states'] or s2 not in allowed_states(a['cat']): continue
            q=json.loads(key(p)); q['a']['states'][i]=s2
            g=a['cat']; t1,t0=stxt(s2,g),stxt(s,g)
            if s=='moving' and s2 in ('accelerating','braking'): t0='just moving at a steady speed'
            out.append(('state',q,f"but {t1} instead of {t0}"))
    # compositional add / drop conjunct on a
    if len(a['states'])<2:
        for s2 in allowed_states(a['cat']):
            if s2 in a['states'] or s2 in ('stationary','moving') and a['states']: continue
            if not compatible(a['states']+[s2]): continue
            q=json.loads(key(p)); q['a']['states']=a['states']+[s2]
            out.append(('compositional',q,f"and also {stxt(s2,a['cat'])}"))

    return [o for o in out if valid(o[1])]
def base_programs():
    P=[]
    for g in ['VEHICLE','CAR','TRUCK','BUS','PEDESTRIAN','BICYCLIST']:
        for s in allowed_states(g):
            P.append({'a':{'cat':g,'states':[s]},'b':None,'rel':None})
        for s1,s2 in itertools.combinations(allowed_states(g),2):
            if {s1,s2}&{'moving','stationary'} and len({s1,s2}&{'moving','stationary','accelerating','braking'})>1: continue
            P.append({'a':{'cat':g,'states':[s1,s2]},'b':None,'rel':None})
    for g in ['VEHICLE','CAR','TRUCK','BUS','PEDESTRIAN','BICYCLIST','EGO']:
        for sa in [[]]+[[s] for s in (['moving','stationary','accelerating','braking','turning_left','turning_right','changing_lanes'] if not is_ped(g) else ['moving','stationary'])]:
            for r in NONDIR+list(FLIP):
                for gb in ['VEHICLE','CAR','TRUCK','BUS','PEDESTRIAN','BICYCLIST']:
                    for sb in [[],['moving'],['stationary']]:
                        P.append({'a':{'cat':g,'states':sa},'b':{'cat':gb,'states':sb},'rel':r})
    return P
if __name__=='__main__':
    load(); print('logs',len(TABLES),flush=True)
    
    cache={}
    def ex(p):
        return execute(p,want_w=False)
    base=[p for p in base_programs() if valid(p)]; random.shuffle(base)
    cands=[]; stats=collections.Counter(); jac_all=[]
    for p in base:
        M,W=ex(p)
        if len(M)<2: stats['base_too_few']+=1; continue
        stats['base_ok']+=1
        for fam,q,m in mutations(p):
            M2,W2=ex(q)
            A=set((k,t) for k,v in M.items() for t in v); B=set((k,t) for k,v in M2.items() for t in v)
            j=len(A&B)/max(1,len(A|B))
            rec=dict(family=fam,P=p,Pp=q,m=m,nP=len(M),nPp=len(M2),jacc_ts=j,jacc_track=len(set(M)&set(M2))/max(1,len(set(M)|set(M2))))
            stats[f'{fam}_mut']+=1
            if len(M2)==0: stats[f'{fam}_empty']+=1; rec['status']='empty_target'
            elif set(M)==set(M2) and A==B: stats[f'{fam}_identical']+=1; rec['status']='identical'
            else:
                refs=[k for k in M if k not in M2]
                if not refs: rec['status']='no_reference_outside_target'; stats[f'{fam}_noref']+=1
                else: rec['status']='ok'
            cands.append(rec)
    json.dump(stats,open(OUT/'gen_stats.json','w'),indent=1)
    pickle.dump(dict(cands=cands,cache_keys=[]),open('/workspace/data/p2_cache/cands.pkl','wb'))
    print(stats)
