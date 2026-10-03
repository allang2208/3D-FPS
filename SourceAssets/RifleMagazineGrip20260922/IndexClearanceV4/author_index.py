"""Index-only correction with complete-surface magazine clearance constraints."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.optimize import minimize

O=Path(__file__).parent; BASE=O.parent
data=json.loads((BASE/'fit_input.json').read_text())
data['magazines'].update(json.loads((BASE/'FingerContactV3/extra_magazines.json').read_text()))
prior=json.loads((BASE/'FingerContactV3/selected_grasp.json').read_text())
names=data['names']; parents=data['parents']; rest={n:np.array(v) for n,v in data['rest'].items()}
inv={n:np.linalg.inv(v) for n,v in rest.items()}; local={n:inv[parents[n]]@rest[n] for n in names[1:]}
vertices=np.c_[np.array(data['vertices']),np.ones(len(data['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in data['weights']]);weights/=weights.sum(1)[:,None]
bound={n:vertices@inv[n].T for n in names}; labels=np.array(data['labels'])
bones=['index_01_l','index_02_l','index_03_l']
owned=np.flatnonzero(weights[:,[names.index(n) for n in bones]].sum(1)>.10)
faces=np.array(data['faces']); relevant=faces[np.isin(faces,owned).all(1)]
edges=np.unique(np.sort(np.concatenate([relevant[:,[0,1]],relevant[:,[1,2]],relevant[:,[2,0]]]),axis=1),axis=0)

def rot(q):return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def wxyz(m):
    q=Rotation.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
def unit(v):return v/np.linalg.norm(v)

class Shell:
    """Conservative continuous outer cross sections, including surface ribs."""
    def __init__(self,mag):
        verts=np.array(mag['vertices']); tris=np.array([[f[0],f[j],f[j+1]] for f in mag['faces'] for j in range(1,len(f)-1)])
        self.z=np.linspace(verts[:,2].min()+1e-5,verts[:,2].max()-1e-5,240)
        self.low=verts[:,2].min();self.high=verts[:,2].max();self.equations=[]
        aa=verts[tris].reshape(-1,3);bb=np.roll(verts[tris],-1,axis=1).reshape(-1,3)
        for z in self.z:
            sel=(aa[:,2]-z)*(bb[:,2]-z)<0;a=aa[sel];b=bb[sel]
            t=(z-a[:,2])/(b[:,2]-a[:,2]);cross=a[:,:2]+t[:,None]*(b-a)[:,:2]
            self.equations.append(ConvexHull(cross).equations)
    def clearance(self,p):
        hi=np.clip(np.searchsorted(self.z,p[:,2]),1,len(self.z)-1);lo=hi-1
        ds=[]
        for indices in (lo,hi):
            d=np.empty(len(p))
            for zi in np.unique(indices):
                use=indices==zi;eq=self.equations[zi]
                d[use]=np.max(p[use,:2]@eq[:,:2].T+eq[:,2],axis=1)
            ds.append(d)
        t=np.clip((p[:,2]-self.z[lo])/(self.z[hi]-self.z[lo]),0,1)
        return np.maximum.reduce([ds[0]*(1-t)+ds[1]*t,self.low-p[:,2],p[:,2]-self.high])*1000

def samples(skin):
    return np.concatenate([skin[owned],skin[edges].mean(1),skin[relevant].mean(1)])

result={};report={}
for gun,old in prior.items():
    basis0=dict(old['finger_basis']);H=np.array(old['hand_in_mag'])
    def pose(basis):
        p={'hand_l':H.copy()}
        for n in names[1:]:
            b=np.eye(4);b[:3,:3]=rot(basis[n]);p[n]=p[parents[n]]@local[n]@b
        skin=sum((bound[n]@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
        return p,skin
    p0,skin0=pose(basis0)
    curl=unit(np.cross(p0[bones[1]][:3,3]-p0[bones[0]][:3,3],p0[bones[2]][:3,3]-p0[bones[1]][:3,3]))
    axes={n:p0[n][:3,:3].T@curl for n in bones}
    sides={n:unit(np.cross(np.array([0.,1.,0.]),axes[n])) for n in bones}
    shells={key:Shell(data['magazines'][key]) for key in (gun,gun+'_extended')}
    original={n:rot(basis0[n]) for n in bones}
    def posed(x):
        basis=dict(basis0)
        for j,n in enumerate(bones):
            twist=np.array([0.,1.,0.])*math.radians(x[6]) if j==0 else np.zeros(3)
            delta=Rotation.from_rotvec(axes[n]*math.radians(x[j])+sides[n]*math.radians(x[j+3])+twist).as_matrix()
            basis[n]=wxyz(original[n]@delta)
        p,skin=pose(basis);return basis,p,skin
    def clearance(x):
        _,p,skin=posed(x);pts=samples(skin)
        # Keep the index in its existing finger row instead of solving contact
        # by lifting its knuckle into an isolated hook above the other fingers.
        height=np.array([(p[n][2,3]-p0[n][2,3])*1000 for n in bones[1:]])
        return np.concatenate([*[shell.clearance(pts) for shell in shells.values()],7+height,7-height])
    # Keep pad contact while avoiding all sampled finger vertices, edge midpoints
    # and face centers. No mean penetration allowance or sparse vertex subsample.
    def objective(x):
        skin=posed(x)[2];value=.02*x[0]**2+.01*(x[1]+25)**2+.02*(x[2]-5)**2+.04*np.sum(np.array(x[3:6])**2)+.008*x[6]**2
        for shell in shells.values():
            for n in bones[1:]:
                d=shell.clearance(skin[labels==n]);patch=np.sort(d)[:max(12,len(d)//12)]
                value+=2*(patch.mean()-.8)**2
        return value
    before={k:{'minimum_clearance_mm':float(s.clearance(samples(skin0)).min()),
               'penetrating_samples':int(np.count_nonzero(s.clearance(samples(skin0))<0))} for k,s in shells.items()}
    print('INDEX_BEFORE',gun,before,flush=True)
    initial=np.array([0.,-35.,10.,0.,0.,0.,0.])
    solved=minimize(objective,initial,method='SLSQP',bounds=[(-15,15),(-50,10),(-15,20),(-10,10),(-5,5),(-4,4),(-35,35)],
                    constraints=[{'type':'ineq','fun':lambda x:clearance(x)-.45}],
                    options={'maxiter':100,'ftol':.00005})
    basis,p,skin=posed(solved.x)
    after={k:{'minimum_clearance_mm':float(s.clearance(samples(skin)).min()),
              'penetrating_samples':int(np.count_nonzero(s.clearance(samples(skin))<0))} for k,s in shells.items()}
    bends=lambda p:[float(np.degrees(np.arccos(np.clip(np.dot(unit(p[a][:3,1]),unit(p[b][:3,1])),-1,1)))) for a,b in zip(bones,bones[1:])]
    report[gun]={'before':before,'after':after,'joint_direction_angles_before':bends(p0),'joint_direction_angles_after':bends(p),'angles_degrees':solved.x.tolist(),'optimizer_success':bool(solved.success),
                 'optimizer_message':str(solved.message),'surface_sample_count':len(samples(skin))}
    print('INDEX_AFTER',gun,report[gun],flush=True)
    result[gun]={**old,'revision':'IndexClearanceV4','finger_basis':basis,'skin':skin.tolist(),
                 'joints':{n:m[:3,3].tolist() for n,m in p.items()},'index_correction_degrees':solved.x.tolist(),
                 'method':'Index-only joint rotation correction, with full finger surface clearance constraints.'}
    (O/'selected_grasp.json').write_text(json.dumps(result),encoding='utf-8')
    (O/'contact_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
