import json, numpy as np, collections
T=json.load(open('results/e_minus_1/triplets_1000.json')); G=json.load(open('results/e_minus_1/gen_stats.json'))
out={'n':len(T),'family_counts':collections.Counter(t['family'] for t in T)}
q=lambda x:{k:round(float(v),3) for k,v in zip(['min','p10','p25','median','p75','p90','max','mean'],list(np.percentile(x,[0,10,25,50,75,90,100]))+[np.mean(x)])}
out['jaccard_track_all']=q([t['jacc_track'] for t in T]); out['jaccard_ts_all']=q([t['jacc_ts'] for t in T])
out['frac_jaccard_track_eq_0']=float(np.mean([t['jacc_track']==0 for t in T]))
out['target_size_tracks']=q([t['n_Pp'] for t in T]); out['negatives_per_query']=q([len(t['negatives']) for t in T]); out['near_miss_per_query']=q([len(t['near_miss_negatives']) for t in T])
out['target_logs']=q([len({l for l,_ in t['target_set']}) for t in T])
fam={}
for f in ['relational','directional','agent_class','state','compositional']:
    S=[t for t in T if t['family']==f]; m=G[f+'_mut']
    fam[f]=dict(mutations_generated=m,empty_target_rate=round(G.get(f+'_empty',0)/m,3),identical_rate=round(G.get(f+'_identical',0)/m,3),
                no_ref_outside_target_rate=round(G.get(f+'_noref',0)/m,3),selected=len(S),jacc_track_median=round(float(np.median([t['jacc_track'] for t in S])),3),
                target_size_median=float(np.median([t['n_Pp'] for t in S])))
out['per_family']=fam
tot=sum(G[f+'_mut'] for f in fam); out['all_mutations']=tot; out['empty_target_rate_all']=round(sum(G.get(f+'_empty',0) for f in fam)/tot,3)
out['context_family']='unsupported: no weather/lighting/time-of-day columns in RefAV/AV2 annotations and no atomic function for them'
json.dump(out,open('results/e_minus_1/auto_checks.json','w'),indent=1); print(json.dumps(out,indent=1))
