"""Re-fit the rejected held wrist using the actual grasp axis and full arm chain."""
from pathlib import Path
import os,sys,json,gzip,pickle
os.environ['OPENBLAS_NUM_THREADS']='1'
root=Path(__file__).resolve().parent;src=root.parent/'Wrist33';sys.path.insert(0,str(src))
scope={'__file__':str(src/'author.py')}
exec(compile((src/'author.py').read_text().split('targets=dict(')[0],str(src/'author.py'),'exec'),scope)
globals().update({k:v for k,v in scope.items() if not k.startswith('__')})
from scipy.optimize import minimize

def profile(f):
    p=src/'Followup'/(f+'.json.gz');return json.load(gzip.open(p if p.exists() else src/(f+'.json.gz'),'rt'))

def solve(w,x,pivot,axis,station_weight=1.):
    out=w.copy();turn=R.from_rotvec(axis*x[4]).as_matrix()
    for i in hand:
        out[i,:3,:3]=turn@w[i,:3,:3];out[i,:3,3]=pivot+turn@(w[i,:3,3]-pivot)
    delta=R.from_rotvec(x[:3]).as_matrix();c=w[cl,:3,3]
    a0,e0,h0=[w[i,:3,3] for i in (ua,la,ha)];a=c+delta@(a0-c);h=out[ha,:3,3]
    out[cl,:3,:3]=delta@w[cl,:3,:3]
    lu=np.linalg.norm(e0-a0);ll=np.linalg.norm(h0-e0);direction=unit(h-a);distance=np.linalg.norm(h-a)
    along=(lu*lu-ll*ll+distance*distance)/(2*distance);radius=np.sqrt(max(0,lu*lu-along*along));center=a+direction*along
    pole=unit(e0-center-direction*((e0-center)@direction));e=center+R.from_rotvec(direction*x[3]).as_matrix()@pole*radius
    normal0=unit(np.cross(e0-a0,h0-e0));normal=unit(np.cross(e-a,h-e))
    du=frame(e-a,normal)@frame(e0-a0,normal0).T;dl=frame(h-e,normal)@frame(h0-e0,normal0).T
    for i in arm:
        up=names[i].startswith('upperarm');q=du if up else dl;origin=a if up else e;old=a0 if up else e0
        out[i,:3,:3]=q@w[i,:3,:3];out[i,:3,3]=origin+q@(w[i,:3,3]-old)
    fore=unit(h-e);lower_def=rot(out[la])@rot(B[la]).T;hand_def=rot(out[ha])@rot(B[ha]).T
    q=R.from_matrix(hand_def@lower_def.T).as_quat();tau=(2*np.arctan2(q[:3]@fore,q[3])+np.pi)%(2*np.pi)-np.pi
    for n,weight in [('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',1.)]:
        i=ix[n];roll=R.from_rotvec(fore*tau*weight).as_matrix()
        target=roll@lower_def@rot(B[i]);prior=rot(out[i])
        delta=(R.from_matrix(target)*R.from_matrix(prior).inv()).as_rotvec()
        out[i,:3,:3]=(R.from_rotvec(delta*station_weight).as_matrix()@prior)*np.linalg.norm(out[i,:3,:3],axis=0)
    return out

if __name__=='__main__':
    result=json.loads((root/'fit.json').read_text()) if (root/'fit.json').exists() else {}
    poses=pickle.load(open(root/'hold_poses.pkl','rb')) if (root/'hold_poses.pkl').exists() else {}
    c=d['clips'][idlepath]
    for family in (sys.argv[1:] or ['base','vertical','angled','canted','prism']):
        home=compose(layer(np.array(c['frames']),idlepath,profile(family),names,c['times']),parents)[0]
        pivot=np.array([5.1,-32.63,-19.]);axis=unit(np.array([.08,0,1.]))
        if family=='base':pivot=np.array([5.01,-28.95,-19.09])
        if family=='canted':pivot=np.array([1.,-29.63,-18.]);axis=unit(np.array([.707,0,.707]))
        if family=='prism':pivot=np.array([5.2,-33.1,-18.])
        yaw=(0,0) if family=='angled' else (np.radians(-10),np.radians(60))
        def score(x):
            w=solve(home,x,pivot,axis);bend=np.degrees(wrist(w));hmove=np.linalg.norm(w[ha,:3,3]-home[ha,:3,3]);emove=np.linalg.norm(w[la,:3,3]-home[la,:3,3]);smove=np.linalg.norm(w[ua,:3,3]-home[ua,:3,3])
            return max(0,bend-10)**2*4+.16*emove**2+.35*smove**2+.10*np.degrees(x[4])**2+.1*hmove**2
        def constraints(x):
            w=solve(home,x,pivot,axis);reach=np.linalg.norm(w[ha,:3,3]-w[ua,:3,3]);length=np.linalg.norm(home[la,:3,3]-home[ua,:3,3])+np.linalg.norm(home[ha,:3,3]-home[la,:3,3])
            return np.array([box_clearance(w)-.20,length*.94-reach])
        bounds=[(-.8,.8)]*3+[(-1.5,1.5),yaw]
        best=None
        for degrees in ([0] if family=='angled' else [15,30,45]):
            x=np.zeros(5);x[4]=np.radians(degrees)
            fit=minimize(score,x,method='SLSQP',bounds=bounds,constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=140,ftol=1e-6,eps=1e-5))
            rank=score(fit.x)+max(0,-constraints(fit.x).min())*1e6
            if best is None or rank<best[0]:best=(rank,fit)
        fit=best[1];w=solve(home,fit.x,pivot,axis)
        result[family]=dict(parameters=fit.x.tolist(),pivot=pivot.tolist(),axis=axis.tolist(),before_bend=float(np.degrees(wrist(home))),after_bend=float(np.degrees(wrist(w))),yaw_degrees=float(np.degrees(fit.x[4])),box_margin_cm=box_clearance(w),shoulder_shift_cm=float(np.linalg.norm(w[ua,:3,3]-home[ua,:3,3])),hand_shift_cm=float(np.linalg.norm(w[ha,:3,3]-home[ha,:3,3])),constraints=constraints(fit.x).tolist(),optimizer_success=bool(fit.success))
        poses[family+'_before']=home;poses[family+'_candidate']=w
        print(family,result[family],flush=True)
        (root/'fit.json').write_text(json.dumps(result,indent=2));pickle.dump(poses,open(root/'hold_poses.pkl','wb'))
