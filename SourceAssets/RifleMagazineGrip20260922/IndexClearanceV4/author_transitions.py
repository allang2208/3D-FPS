"""Keep the corrected index plane through approach and release."""
from pathlib import Path
import json,numpy as np,math
from scipy.spatial.transform import Rotation,Slerp
from scipy.optimize import minimize
O=Path(__file__).parent
exec(compile((O/'author_index.py').read_text().split('result={};report={}')[0],str(O/'author_index.py'),'exec'))
input_path=O/'transition_input_poses.json'
rows_all=json.loads((input_path if input_path.exists() else O/'source_pose_samples.json').read_text())
newfits=json.loads((O/'selected_grasp.json').read_text())
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def mix(a,b,t):
    if t<=0:return a
    if t>=1:return b
    return Slerp([0,1],Rotation.from_matrix(np.stack([a,b])))(t).as_matrix()
def basis_from(p,n):return (np.linalg.inv(local[n])@np.linalg.inv(p[parents[n]])@p[n])[:3,:3]
results={}
for gun,fit in newfits.items():
    rows=rows_all[gun+'/standard/base/reload']
    ps={float(f):{n:np.array(m) for n,m in row.items()} for f,row in rows.items()}
    old_hold={n:basis_from(ps[148.],n) for n in bones}
    old_delta={n:rot(prior[gun]['finger_basis'][n]).T@old_hold[n] for n in bones}
    original={}
    for f,p in ps.items():
        wt=smooth((f-21.5)/24)*(1-smooth((f-237)/13))
        original[f]={n:basis_from(p,n)@mix(np.eye(3),old_delta[n],wt).T for n in bones}
    hold={n:rot(fit['finger_basis'][n]) for n in bones}
    pH={'hand_l':np.array(fit['hand_in_mag'])}
    for n in names[1:]:
        b=np.eye(4);b[:3,:3]=rot(fit['finger_basis'][n]);pH[n]=pH[parents[n]]@local[n]@b
    curl=unit(np.cross(pH[bones[1]][:3,3]-pH[bones[0]][:3,3],pH[bones[2]][:3,3]-pH[bones[1]][:3,3]))
    axes={n:pH[n][:3,:3].T@curl for n in bones}
    shells=[Shell(data['magazines'][k]) for k in (gun,gun+'_extended')]
    def opens(x):return {n:hold[n]@Rotation.from_rotvec(axes[n]*math.radians(x[j])).as_matrix() for j,n in enumerate(bones)}
    def posed(f,opened):
        p=dict(ps[f])
        for n in bones:
            q=mix(original[f][n],opened[n],smooth((f-20)/12))
            q=mix(q,hold[n],smooth((f-38)/8))
            q=mix(q,opened[n],smooth((f-237)/8))
            q=mix(q,original[f][n],smooth((f-244)/10))
            b=np.eye(4);b[:3,:3]=q;p[n]=p[parents[n]]@local[n]@b
        skin=sum((bound[n]@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
        return skin
    release_frames=[34.,40.,44.,238.,240.,242.,244.,246.,248.,250.,254.]
    def constraint(x):
        opened=opens(x);return np.concatenate([shell.clearance(samples(posed(f,opened)))-.3 for f in release_frames for shell in shells])
    solved=minimize(lambda x:np.sum((x-np.array([-18.,-5.,-10.]))**2),np.array([-18.,-5.,-10.]),method='SLSQP',
                    bounds=[(-45,0),(-10,0),(-35,0)],constraints=[{'type':'ineq','fun':constraint}],options={'maxiter':100,'ftol':.0001})
    opened=opens(solved.x)
    distances={str(f):min(float(shell.clearance(samples(posed(f,opened))).min()) for shell in shells) for f in ps}
    results[gun]={'open_basis':{n:wxyz(m) for n,m in opened.items()},'open_delta_degrees':solved.x.tolist(),
                  'prepare_frames':[20,32],'close_frames':[38,46],'open_frames':[237,245],'return_frames':[244,254],
                  'source_transition_clearance_mm':distances,'optimizer_success':bool(solved.success)}
    print('INDEX_TRANSITION_AUTHORED',gun,results[gun],flush=True)
(O/'transitions.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
