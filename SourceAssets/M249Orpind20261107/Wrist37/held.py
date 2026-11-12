"""Joint rotations only: fit anatomical elbow plane and restrained pronation."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'Wrist36'))
from rig import *
scope={'__file__':str(ROOT/'fit_left.py')}
exec(compile((ROOT/'fit_left.py').read_text().split('fits={};poses={};report={}')[0],str(ROOT/'fit_left.py'),'exec'),scope)
boxmargin=scope['boxmargin'];margin=scope['margin'];camera=scope['camera']
original=pickle.load(open(ROOT/'candidate.pkl','rb'))
cl,ua,la,ha,arm,hand=indices('l');owned=[cl]+arm+[ha];gun=ix['WPN_root']

def pronation(w,side='l'):
    c,u,e,h,arms,hands=indices(side)
    axis=unit(w[h,:3,3]-w[e,:3,3]);dl=rot(w[e])@rot(B[e]).T;dh=rot(w[h])@rot(B[h]).T
    q=R.from_matrix(dh@dl.T).as_quat()
    return (2*np.arctan2(q[:3]@axis,q[3])+np.pi)%(2*np.pi)-np.pi

def anatomical(w,side='l'):
    c,u,e,h,arms,hands=indices(side);out=w.copy()
    n0=unit(np.cross(B[e,:3,3]-B[u,:3,3],B[h,:3,3]-B[e,:3,3]))
    n=unit(np.cross(w[e,:3,3]-w[u,:3,3],w[h,:3,3]-w[e,:3,3]))
    for root,tip,prefix in [(u,e,'upperarm'),(e,h,'lowerarm')]:
        delta=frame(w[tip,:3,3]-w[root,:3,3],n)@frame(B[tip,:3,3]-B[root,:3,3],n0).T
        for i in arms:
            if names[i].startswith(prefix):
                out[i,:3,:3]=delta@B[i,:3,:3]
                out[i,:3,3]=w[root,:3,3]+delta@(B[i,:3,3]-B[root,:3,3])
    tau=pronation(out,side);fore=unit(w[h,:3,3]-w[e,:3,3]);lower=rot(out[e])@rot(B[e]).T
    for name,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
        i=ix[name+'_'+side];out[i,:3,:3]=R.from_rotvec(fore*tau*share).as_matrix()@lower@B[i,:3,:3]
    return out

def elbow(w):
    return np.degrees(np.arccos(np.clip(unit(w[la,:3,3]-w[ua,:3,3])@unit(w[ha,:3,3]-w[la,:3,3]),-1,1)))

if __name__=='__main__':
    output={};report={};experiments={}
    for family in ['base','vertical','angled','canted','prism']:
        ip=next(p for f,p in original if f==family and p.endswith('_idle'))
        rp=next(p for f,p in original if f==family and p.endswith('_reload'))
        home=original[(family,ip)]['after'][0];a=original[(family,rp)];mid=a['after'][np.argmin(abs(a['times']-3))]
        xf=mid[gun]@np.linalg.inv(home[gun]);cam=camera(family,rp,np.array([3.]))[0]
        def pose(x):return anatomical(solve(home,x))
        def cost(x):
            q=pose(x);roll=np.degrees(pronation(q));angle=bend(q)
            return max(0,abs(roll)-35)**2*3+max(0,angle-7)**2*12+.015*np.sum(np.degrees(x)**2)+.08*np.linalg.norm(q[la,:3,3]-home[la,:3,3])**2
        length=np.linalg.norm(home[la,:3,3]-home[ua,:3,3])+np.linalg.norm(home[ha,:3,3]-home[la,:3,3])
        def constraints(x):
            q=pose(x)
            return np.array([boxmargin(q)-.20,margin(xf@q,cam)-.25,length*.95-np.linalg.norm(q[ha,:3,3]-q[ua,:3,3]),elbow(q)-35])
        best=None
        for seed in [np.zeros(4),[0,.3,0,.6],[0,-.3,0,-.6],[.2,.5,0,1.2],[-.2,0,.3,-1.2]]:
            fit=minimize(cost,seed,method='SLSQP',bounds=[(-1.2,1.2)]*3+[(-2.,2.)],constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=130,ftol=1e-6,eps=1e-5))
            rank=fit.fun+1e7*max(0,-constraints(fit.x).min())
            if best is None or rank<best[0]:best=rank,fit
        fit=best[1];q=pose(fit.x);q=preserve_local(home[None],q[None],owned)[0]
        output[family]=q;report[family]=dict(parameters=fit.x.tolist(),wrist_bend=bend(q),pronation=float(np.degrees(pronation(q))),elbow=elbow(q),constraints=constraints(fit.x).tolist(),palm_change_cm=float(np.linalg.norm(q[ha,:3,3]-home[ha,:3,3])))
        experiments[family]=dict(before=home,after=q)
        print(family,report[family],flush=True)
    pickle.dump(output,open(HERE/'held.pkl','wb'));pickle.dump(experiments,open(HERE/'experiment.pkl','wb'))
    (HERE/'held_report.json').write_text(json.dumps(report,indent=2))
