"""Local surface fitting for the return grip; no weapon or right-hand changes."""
from pathlib import Path
exec(compile((Path(__file__).parent/'support_probe.py').read_text().split('result=[]')[0],__file__,'exec'))
from scipy.optimize import differential_evolution
bindlocal={n:(np.linalg.inv(B[parents[n]])@B[n] if parents[n] else B[n]) for n in hb}
subset={}
for name in hb:
    j=names.index(name);ws=np.array([sum(w for b,w in g['weights'][i] if b==j) for i in handids]);sel=ws>0
    if sel.any():subset[name]=(sel,np.c_[v[handids[sel]],np.ones(sel.sum())]*ws[sel,None])
def posed(x):
    world={};q=p.copy();q[handids]=0.
    for name in hb:
        if name=='hand_l':world[name]=H[name].copy();world[name][:3,3]+=x[:3]
        else:
            local=L[name].copy()
            amount=1. if 'metacarpal' in name else x[6] if name.startswith('thumb') else x[3+int(name.split('_')[1])-1]
            local[:3,:3]=blend(rot(bindlocal[name]),rot(local),amount)*np.linalg.norm(local[:3,:3],axis=0)
            world[name]=world[parents[name]]@local
        if name in subset:
            sel,points=subset[name];q[handids[sel]]+=(points@(world[name]@np.linalg.inv(B[name])).T)[:,:3]
    return q,world
best=[1.e9,None,None]
def objective(x):
    q,w=posed(x);hits=collisions(q);total=sum(hits.values())
    # Keep the grip inside the curled fingers; a detached fist is not a fit.
    center=.35*w['middle_01_l'][:3,3]+.35*w['middle_03_l'][:3,3]+.30*w['hand_l'][:3,3]
    target=np.array([5.1,-28.9,-18.8]);gap=np.maximum(0,np.abs(center-target)-np.array([.65,.65,1.2]))
    loss=total*3+np.dot(x[:3],x[:3])+((x[3:]-1)**2).sum()*12+np.dot(gap,gap)*2500
    if loss<best[0]:
        best[:]=[float(loss),x.tolist(),hits];print('hold_fit',best,flush=True)
    return loss
fit=differential_evolution(objective,[(-2.,2.),(-1.,3.),(-4.,-.5),(.65,1.1),(.3,1.1),(.3,1.1),(.5,1.1)],popsize=6,maxiter=30,polish=False,seed=249,updating='immediate',tol=.02)
q,w=posed(fit.x);out=dict(parameters=fit.x.tolist(),hits=collisions(q),hand_world={n:a.tolist() for n,a in w.items()})
(r/'hold_fit.json').write_text(json.dumps(out,indent=2));print('HOLD_FIT_SAVED',out['parameters'],out['hits'],flush=True)
