"""Repair local finger contacts after return timing, with the palm path locked."""
from pathlib import Path
import pickle, numpy as np, json, sys
r=Path(__file__).resolve().parent
scope={'__file__':str(r/'fit_returns.py')}
exec(compile((r/'fit_returns.py').read_text().split('for (family,path),row')[0],str(r/'fit_returns.py'),'exec'),scope)
s=scope['s'];ReturnFit=scope['ReturnFit'];family=sys.argv[sys.argv.index('--')+1]
data=pickle.load(open(r/'post_world.pkl','rb'))
report_path=r/('post_contacts_'+family+'.json');result_path=r/('post_contacts_'+family+'.pkl');checkpoint=r/('post_contacts_'+family+'_checkpoint.pkl')
report=json.loads(report_path.read_text()) if report_path.exists() else {};result=pickle.load(open(result_path,'rb')) if result_path.exists() else {};cache=pickle.load(open(checkpoint,'rb')) if checkpoint.exists() else {}

def reset(fit,w):
    fit.original=w.copy();fit.root=s['rigid'](w[s['ix']['WPN_root']]);fit.w=np.linalg.inv(fit.root)@w;fit.local=fit.w.copy()
    for i,p in enumerate(s['parents']):
        if p>=0:fit.local[i]=np.linalg.inv(fit.w[p])@fit.w[i]

for key,row in data.items():
    fam,path=key
    if fam!=family or '/SideMagazine' not in path:continue
    if key in result and report.get(path,{}).get('max_depth_cm',999)<=.18:
        print('SETTLE_RETAIN_COMPLETE',fam,path,flush=True);continue
    ts=row['times'];world=row['world'];end=3.14 if '_empty' in path else 3.5
    ids=np.flatnonzero((ts>2.77)&(ts<end-.003));fit=ReturnFit(world[ids[0]],fam,stride=1);fit.fixed_wrist=np.zeros(6)
    keys=np.array([2.76,end]);values=np.zeros((2,len(s['limits'])))
    if key in cache:keys,values=cache[key]
    for iteration in range(10):
        allx=np.array([np.interp(ts,keys,values[:,j]) for j in range(values.shape[1])]).T
        failures=[];peak=0.;pt=0.
        for k in ids:
            reset(fit,world[k]);info=fit.score(allx[k],True);depth=info['max_depth_cm']
            if depth>peak:peak=depth;pt=float(ts[k])
            if depth>.16:failures.append((depth,k))
        print('SETTLE_CONTACT',fam,path.split('/')[-1],iteration,round(peak,4),round(pt,5),'failed',len(failures),flush=True)
        if not failures or iteration==9:break
        picked=[]
        for depth,k in sorted(failures,reverse=True):
            if any(abs(ts[k]-ts[j])<.012 for j in picked):continue
            picked.append(k);reset(fit,world[k]);near=abs(keys-ts[k])<.025
            seeds=[allx[k],np.zeros(len(s['limits']))]+list(values[near]);start=min(seeds,key=fit.score)
            x,before,after=fit.optimize(start,[(.08,2),(.04,1)])
            # A local taper keeps the correction out of neighbouring contact
            # phases; subsequent passes inspect the whole interpolated span.
            if not np.any(abs(keys-ts[k])<1e-6):
                j=np.searchsorted(keys,ts[k]);keys=np.insert(keys,j,ts[k]);values=np.insert(values,j,x,axis=0)
            else:values[np.argmin(abs(keys-ts[k]))]=x
            cache[key]=(keys,values);pickle.dump(cache,open(checkpoint,'wb'))
            if len(picked)>=16:break
    output=world.copy();allx=np.array([np.interp(ts,keys,values[:,j]) for j in range(values.shape[1])]).T
    for k in ids:
        reset(fit,world[k]);edited=fit.root@fit.pose(allx[k]);moving=[s['ix']['hand_l']]+s['finger_ids']+[s['ix']['ik_hand_l']];output[k,moving]=edited[moving]
    result[key]=dict(times=ts,world=output)
    report[path]=dict(max_depth_cm=peak,source=pt,remaining_over_1_6mm=len(failures),key_times=keys.tolist(),joint_max_deg=float(abs(values[:,6:]).max()))
    pickle.dump(result,open(result_path,'wb'));report_path.write_text(json.dumps(report,indent=2))
