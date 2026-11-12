"""Fit simultaneous shoulder/elbow motion to the actual box clearance."""
from pathlib import Path
root=Path(__file__).resolve().parent
source=root/'author.py';scope={'__file__':str(source)}
exec(compile(source.read_text().split('targets=dict(')[0],str(source),'exec'),scope)
globals().update({k:v for k,v in scope.items() if not k.startswith('__')})
from scipy.optimize import minimize
targets=dict(base=14.,vertical=24.,angled=30.,canted=34.,prism=32.)
result={};previous=json.loads((r/'support_fit.json').read_text())
for family,profile in d['profiles'].items():
    c=d['clips'][idlepath];home=compose(layer(np.array(c['frames']),idlepath,profile,names,c['times']),parents)[0]
    a=home[ua,:3,3];e=home[la,:3,3];target=np.radians(targets[family])
    mount=np.array([0.,3.,0.]) if family in ('vertical','prism') else np.zeros(3)
    pose=lambda x:elbow_pose(home,np.r_[x,mount])
    def score(x):
        w=pose(x);angle=wrist(w);em=np.linalg.norm(w[la,:3,3]-e);sm=np.linalg.norm(w[ua,:3,3]-a)
        return (max(0,angle-target)/np.radians(1.))**2+.04*em**2+.8*sm**2+.001*np.sum(np.degrees(x[:3])**2)
    def constraints(x):
        w=pose(x)
        return np.array([box_clearance(w)-.12,6.-np.linalg.norm(w[ua,:3,3]-a),14.-np.linalg.norm(w[la,:3,3]-e)])
    p=previous[family];old=np.array(p['parameters'][:4])
    starts=[old,np.zeros(4),np.radians([15,15,15,20]),np.radians([-15,-15,-15,-20])]
    fits=[]
    for x in starts:
        fit=minimize(score,x,method='SLSQP',bounds=[(-np.radians(30),np.radians(30))]*3+[(-np.radians(100),np.radians(100))],constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=160,ftol=1e-6,eps=1e-5))
        fits.append((max(0,-constraints(fit.x).min())*1e6+score(fit.x),fit))
    fit=min(fits,key=lambda v:v[0])[1];w=pose(fit.x)
    result[family]=dict(parameters=np.r_[fit.x,mount].tolist(),wrist=float(np.degrees(wrist(w))),clearance_cm=box_clearance(w),shoulder_cm=float(np.linalg.norm(w[ua,:3,3]-a)),elbow_cm=float(np.linalg.norm(w[la,:3,3]-e)),success=bool(fit.success))
    (r/'support_fit_final.json').write_text(json.dumps(result,indent=2));print(family,result[family],flush=True)
