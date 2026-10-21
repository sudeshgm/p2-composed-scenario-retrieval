"""Tiny program spec -> RefAV atomic-function program (source + executor)."""
import sys, warnings; warnings.filterwarnings('ignore')
from pathlib import Path
sys.path.insert(0,'/workspace/refav')
import refAV.paths as P; P.AV2_DATA_DIR=Path('/workspace/data/av2sensor')
import refAV.utils as U
def _serial(func, all_uuids, *args, **kwargs):
    func=U.unwrap_func(func); ud={}; rd={}
    for u in all_uuids:
        r=func(u,*args,**kwargs)
        if not isinstance(r,tuple): r=(r,None)
        if r[0] is not None: ud[u]=r[0]; rd[u]=r[1]
    return ud, rd
U.parallelize_uuids=_serial
_RF={}
_orig_rf=U.read_feather
def _cached_rf(path,*a,**k):
    p=str(path)
    if p not in _RF:
        if len(_RF)>8: _RF.clear()
        _RF[p]=_orig_rf(path,*a,**k)
    return _RF[p]
U.read_feather=_cached_rf
import shapely, numpy as _np
_TREES={}
def _fast_lane_segments(avm, position):
    k=id(avm)
    if k not in _TREES:
        lss=list(avm.vector_lane_segments.values())
        polys=[shapely.Polygon(ls.polygon_boundary[:,:2]) for ls in lss]
        _TREES[k]=(lss, shapely.STRtree(polys), polys)
    lss,tree,polys=_TREES[k]
    idx=tree.query(shapely.Point(float(position[0]),float(position[1])), predicate='intersects')
    return [lss[i] for i in idx]
U.get_lane_segments=_fast_lane_segments
P.GLOBAL_CACHE_PATH=Path('/workspace/data/p2_cache')
import refAV.atomic_functions as _AF
from av2.structures.cuboid import CuboidList as _CL
_CUB={}
def _fast_cuboid(track_uuid, log_dir, timestamp=None):
    k=str(log_dir)
    if k not in _CUB:
        _CUB.clear(); df=U.read_feather(Path(log_dir)/'sm_annotations.feather')
        _CUB[k]=({u:g for u,g in df.groupby('track_uuid')},{})
    groups,memo=_CUB[k]
    mk=(track_uuid,timestamp)
    if mk not in memo:
        g=groups.get(track_uuid)
        if g is None: memo[mk]=None
        else:
            if timestamp:
                g=g[g.timestamp_ns==timestamp]
                if g.empty: memo[mk]=None; return None
            memo[mk]=_CL.from_dataframe(g.iloc[:1] if timestamp else g)[0]
    return memo[mk]
U.get_cuboid_from_uuid=_fast_cuboid; _AF.get_cuboid_from_uuid=_fast_cuboid
_MEMO={}
def _memo(name, f):
    def w(*a, **k):
        key=(name, tuple(str(x) if not isinstance(x,(int,float,str,type(None))) else x for x in a), tuple(sorted((kk,str(v)) for kk,v in k.items())))
        if key not in _MEMO: _MEMO[key]=f(*a,**k)
        return _MEMO[key]
    return w
for _n in ['get_nth_pos_deriv','get_nth_yaw_deriv','get_nth_radial_deriv','get_scenario_lanes','cuboid_distance','get_timestamps','get_ego_SE3','read_city_SE3_ego']:
    _f=_memo(_n, getattr(U,_n)); setattr(U,_n,_f)
    if hasattr(_AF,_n): setattr(_AF,_n,_f)
def clear_memos(): _MEMO.clear(); _CUB.clear()
from refAV.atomic_functions import *
from refAV.utils import reconstruct_track_dict, reconstruct_relationship_dict
LOGROOT=Path('/workspace/data/p2_sm_logs/val')

# unary states: name -> (source template using X)
STATES={
 'moving':        "has_velocity({x}, log_dir, min_velocity=2)",
 'stationary':    "stationary({x}, log_dir)",
 'accelerating':  "accelerating({x}, log_dir, min_accel=1.0)",
 'braking':       "accelerating({x}, log_dir, min_accel=-np.inf, max_accel=-1.0)",
 'turning_left':  "turning({x}, log_dir, direction='left')",
 'turning_right': "turning({x}, log_dir, direction='right')",
 'changing_lanes':"changing_lanes({x}, log_dir)",
 'near_intersection':"near_intersection({x}, log_dir)",
 'at_ped_crossing':"at_pedestrian_crossing({x}, log_dir)",
 'on_road':       "on_road({x}, log_dir)",
}
RELS={
 'in_same_lane':  "in_same_lane({a}, {b}, log_dir)",
 'heading_toward':"heading_toward({a}, {b}, log_dir, max_distance=30)",
 'following':     "following({a}, {b}, log_dir)",
 'near':          "near_objects({a}, {b}, log_dir, distance_thresh=10)",
 'facing_toward': "facing_toward({a}, {b}, log_dir, max_distance=30)",
 'dir_forward':   "has_objects_in_relative_direction({a}, {b}, log_dir, direction='forward', within_distance=25)",
 'dir_backward':  "has_objects_in_relative_direction({a}, {b}, log_dir, direction='backward', within_distance=25)",
 'dir_left':      "has_objects_in_relative_direction({a}, {b}, log_dir, direction='left', within_distance=15)",
 'dir_right':     "has_objects_in_relative_direction({a}, {b}, log_dir, direction='right', within_distance=15)",
}
def _obj(src, var, cat, states):
    src.append(f"{var} = get_objects_of_category(log_dir, category='{cat}')")
    for s in states:
        src.append(f"{var} = "+STATES[s].format(x=var))
def to_source(spec):
    src=[]
    _obj(src,'a',spec['a']['cat'],spec['a']['states'])
    if spec.get('rel'):
        _obj(src,'b',spec['b']['cat'],spec['b']['states'])
        src.append("out = "+RELS[spec['rel']].format(a='a',b='b'))
    else: src.append("out = a")
    return "\n".join(src)
def run(spec, log_id):
    ns=dict(globals()); ns['log_dir']=LOGROOT/log_id
    exec(to_source(spec), ns)
    out=ns['out']
    tracks=reconstruct_track_dict(out)
    rel={}
    if spec.get('rel'):
        try: rel={k:{r:sorted(map(int,t)) for r,t in v.items()} for k,v in reconstruct_relationship_dict(out).items() if v}
        except Exception: rel={}
    return {k:sorted(map(int,v)) for k,v in tracks.items()}, rel
