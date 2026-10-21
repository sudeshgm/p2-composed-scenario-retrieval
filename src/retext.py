"""Re-word an existing triplets_1000.json in plain English (m, P_text, Pp_text) without re-running generation."""
import json,sys,os
sys.path.insert(0,os.path.dirname(__file__)); import plain as L
f='results/e_minus_1/triplets_1000.json'; T=json.load(open(f))
for t in T:
    t.setdefault('m_old',t['m']); t['m']=L.m_text(t['family'],t['P'],t['Pp']); t['P_text']=L.desc(t['P']); t['Pp_text']=L.desc(t['Pp'])
json.dump(T,open(f,'w')); print('reworded',len(T))
