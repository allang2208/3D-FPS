"""Choose small elbow-circle clearances without moving the hand contact."""
from pathlib import Path
exec(compile((Path(__file__).parent/'author_motion.py').read_text().split('for empty in (False,True):')[0],__file__,'exec'))
cache=pickle.load(open(r/'candidate_world.pkl','rb'));trials=[];role='reload';twists=json.loads((r/'twist_log.json').read_text())
for family in holds:
    data=cache['reload_'+family]
    for phase,ts in [('approach',[.2833333333]),('return',[3.3666666667,3.3833333333])]:
        for degrees in [0,*[v for x in range(5,41,5) for v in (x,-x)]]:
            for t in ts:
                k=round(t*120);t=k/120;w={n:data['world'][k,i].copy() for i,n in enumerate(names)};target=w['hand_l'].copy();fingers={n:np.linalg.inv(w[parents[n]])@w[n] for n in digits['l']}
                for n in selected:w[n]=holdworlds[family][n].copy()
                axis=unit(target[:3,3]-w['upperarm_l'][:3,3]);key='reload_'+family;original=pole_plan[key][k].copy();pole_plan[key][k]=turn(axis,np.radians(degrees))@original
                twist_state.clear();twist_state[family]=twists[family][k][1];pole_state.clear();out=solve(w,idle_local,'l',target[:3,3],rot(target),fingers,source_time=t,family=family);pole_plan[key][k]=original
                trials.append(dict(family=family,phase=phase,time=t,degrees=degrees,world=np.array([out[n] for n in names])))
with (r/'elbow_trials.pkl').open('wb') as f:pickle.dump(trials,f)
print('ELBOW_CLEARANCE_TRIALS',len(trials))
