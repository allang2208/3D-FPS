"""Fit a joint-only path with actual captured camera offset and fixed palm."""
from pathlib import Path
here=Path(__file__).resolve().parent
exec(compile((here/'fit_visibility_actual.py').read_text().split('payload=json.load')[0],str(here/'fit_visibility_actual.py'),'exec'))
from scipy.interpolate import CubicSpline
payload=json.load(gzip.open(outdir/'prism-before.json.gz','rt'));report={}
for path,c in d['clips'].items():
    if not path.endswith(('A_M249_reload','A_M249_reload_empty')):continue
    times=np.array(c['times']);old=compose(layer(np.array(c['frames']),path,payload,names,times),parents)
    xfs=camera(path,times);empty=path.endswith('_empty')
    anchors=np.unique(np.r_[0,np.arange(.6 if empty else 1.3,5.3 if empty else 6.5,.15),times[-1]])
    indices=np.unique([np.argmin(abs(times-t)) for t in anchors]);solutions=[];last=np.zeros(4);rows=[]
    for k in indices:
        w0=old[k];xf=xfs[k];margin0=clearance(w0,xf).min()
        # Leave endpoints and already-clear poses alone unless continuity needs a lead-in.
        if k in (0,len(times)-1):sol=np.zeros(4);success=True
        else:
            length=np.linalg.norm(w0[la,:3,3]-w0[ua,:3,3])+np.linalg.norm(w0[ha,:3,3]-w0[la,:3,3])
            box0=box_clearance(w0);limit=max(35,np.degrees(wrist(w0)))
            def constraint(x):
                w=elbow_pose(w0,x)
                return np.array([clearance(w,xf).min()-.7,limit-np.degrees(wrist(w)),.975-np.linalg.norm(w[ha,:3,3]-w[ua,:3,3])/length,box_clearance(w)-min(.15,box0)+.005])
            def cost(x):return float(x@x+.2*((x-last)@(x-last)))
            best=None
            for seed in (last,[-.4,.4,0,.7],[-.7,.6,0,.9]):
                fit=minimize(cost,np.array(seed),method='SLSQP',bounds=[(-1.,1.)]*3+[(-1.7,1.7)],constraints=[dict(type='ineq',fun=constraint)],options=dict(maxiter=100,ftol=1e-6,eps=1e-5))
                loss=cost(fit.x)+max(0,-constraint(fit.x).min())*1e5
                if best is None or loss<best[0]:best=(loss,fit)
                if constraint(fit.x).min()>-.005:break
            fit=best[1];sol=fit.x;success=bool(constraint(sol).min()>-.02)
        last=sol;solutions.append(sol)
        rows.append(dict(time=float(times[k]),baseline=float(margin0),parameters=sol.tolist(),success=success,margin=float(clearance(elbow_pose(w0,sol),xf).min()),bend=float(np.degrees(wrist(elbow_pose(w0,sol))))))
        print(path.split('.')[-1],rows[-1],flush=True)
    report[path]=dict(times=times[indices].tolist(),parameters=np.array(solutions).tolist(),rows=rows)
    (outdir/'path_fit.json').write_text(json.dumps(report,indent=2))
