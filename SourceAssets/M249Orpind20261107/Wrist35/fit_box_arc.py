"""Keep the moving box clear while correcting the support shoulder."""
from pathlib import Path
here=Path(__file__).resolve().parent
exec(compile((here/'fit_visibility_actual.py').read_text().split('payload=json.load')[0],str(here/'fit_visibility_actual.py'),'exec'))
payload=json.load(gzip.open(outdir/'prism-before.json.gz','rt'));fits=json.loads((outdir/'visibility_fit.json').read_text())
target=np.array(next(v for k,v in fits.items() if k.endswith('_empty'))['parameters']);result={}
for path,c in d['clips'].items():
    if not path.endswith(('A_M249_reload','A_M249_reload_empty')):continue
    t=np.array(c['times']);old=compose(layer(np.array(c['frames']),path,payload,names,t),parents);cam=camera(path,t);empty=path.endswith('_empty')
    anchors=np.arange(1.733333333 if empty else 2.633333333,2.31 if empty else 3.21,1/60)
    rows=[dict(time=1.65 if empty else 2.55,parameters=target.tolist(),constraints=[0,0,0,0])];last=target
    for a in anchors:
        k=np.argmin(abs(t-a));w0=old[k];xf=cam[k];length=np.linalg.norm(w0[la,:3,3]-w0[ua,:3,3])+np.linalg.norm(w0[ha,:3,3]-w0[la,:3,3]);box0=box_clearance(w0)
        def constraint(x):
            w=elbow_pose(w0,x)
            return np.array([clearance(w,xf).min()-.7,max(40,np.degrees(wrist(w0)))-np.degrees(wrist(w)),.975-np.linalg.norm(w[ha,:3,3]-w[ua,:3,3])/length,box_clearance(w)-.4])
        def cost(x):return float((x-target)@(x-target)+.2*((x-last)@(x-last)))
        best=None
        for seed in [last,target,[-.4,.6,0,.8]]:
            fit=minimize(cost,seed,method='SLSQP',bounds=[(-1,1)]*3+[(-1.7,1.7)],constraints=[dict(type='ineq',fun=constraint)],options=dict(maxiter=65,ftol=1e-6,eps=1e-5))
            rank=cost(fit.x)+max(0,-constraint(fit.x).min())*1e5
            if best is None or rank<best[0]:best=(rank,fit.x)
            if constraint(fit.x).min()>-.003:break
        last=best[1];row=dict(time=float(t[k]),parameters=last.tolist(),constraints=constraint(last).tolist());rows.append(row);print(path.split('.')[-1],row,flush=True)
    result[path]=rows;(outdir/'box_arc.json').write_text(json.dumps(result,indent=2))
