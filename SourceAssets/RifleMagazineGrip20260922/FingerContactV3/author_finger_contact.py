"""Tighten four finger pads, with the accepted palm and rear thumb fixed."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.spatial import cKDTree,ConvexHull
from scipy.optimize import minimize
import trimesh
O=Path(__file__).parent;BASE=O.parent
data=json.loads((BASE/'fit_input.json').read_text())
data['magazines'].update(json.loads((O/'extra_magazines.json').read_text()))
previous=json.loads((BASE/'ThumbOppositionV2/selected_grasp.json').read_text())
names=data['names'];rest={n:np.array(v) for n,v in data['rest'].items()};inv={n:np.linalg.inv(v) for n,v in rest.items()}
local={n:inv[data['parents'][n]]@rest[n] for n in names[1:]}
vertices=np.c_[np.array(data['vertices']),np.ones(len(data['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in data['weights']]);weights/=weights.sum(1)[:,None]
bound={n:vertices@inv[n].T for n in names};labels=np.array(data['labels'])
digits=['index','middle','ring','pinky']
def unit(v):return v/np.linalg.norm(v)
def rot(q):return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def wxyz(m):
    q=Rotation.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
class Shell:
    def __init__(self,mag):
        faces=[[f[0],f[j],f[j+1]] for f in mag['faces'] for j in range(1,len(f)-1)]
        mesh=trimesh.Trimesh(vertices=mag['vertices'],faces=faces,process=False)
        self.tri=mesh.triangles;self.tree=cKDTree(self.tri.mean(1));self.z=np.linspace(mesh.bounds[0,2]+.001,mesh.bounds[1,2]-.001,120);self.hulls=[]
        aa=self.tri.reshape(-1,3);bb=np.roll(self.tri,-1,axis=1).reshape(-1,3)
        for z in self.z:
            select=(aa[:,2]-z)*(bb[:,2]-z)<0;a=aa[select];b=bb[select]
            t=(z-a[:,2])/(b[:,2]-a[:,2]);cross=a[:,:2]+t[:,None]*(b-a)[:,:2]
            self.hulls.append(ConvexHull(cross).equations if len(cross)>3 else None)
    def distance(self,points):
        _,idx=self.tree.query(points,k=12)
        near=trimesh.triangles.closest_point(self.tri[idx.reshape(-1)],np.repeat(points,12,axis=0)).reshape(len(points),12,3)
        ds=np.sum((near-points[:,None,:])**2,2);which=ds.argmin(1);row=np.arange(len(points));near=near[row,which]
        inside=np.zeros(len(points),dtype=bool);iz=np.clip(np.searchsorted(self.z,points[:,2]),0,len(self.z)-1)
        for zi in np.unique(iz):
            use=iz==zi;eq=self.hulls[zi]
            if eq is not None:inside[use]=np.max(points[use,:2]@eq[:,:2].T+eq[:,2],axis=1)<-.0001
        inside&=(points[:,2]>self.z[0])&(points[:,2]<self.z[-1])
        return np.sqrt(ds[row,which])*np.where(inside,-1,1),near
result={}
for gun,old in previous.items():
    baseline=dict(old['finger_basis']);H=np.array(old['hand_in_mag'])
    def pose(basis):
        p={'hand_l':H.copy()}
        for n in names[1:]:
            b=np.eye(4);b[:3,:3]=rot(basis[n]);p[n]=p[data['parents'][n]]@local[n]@b
        skin=sum((bound[n]@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
        return p,skin
    p0,skin0=pose(baseline);skinmesh=trimesh.Trimesh(vertices=skin0,faces=data['faces'],process=False)
    normals=skinmesh.vertex_normals
    shells=[Shell(data['magazines'][gun]),Shell(data['magazines'][gun+'_extended'])]
    basis=dict(baseline);changes={};pad_report={}
    for digit in digits:
        bones=[digit+f'_{j:02d}_l' for j in (1,2,3)]
        d1=p0[bones[1]][:3,3]-p0[bones[0]][:3,3];d2=p0[bones[2]][:3,3]-p0[bones[1]][:3,3]
        curl_axis=unit(np.cross(d1,d2))
        axes={n:p0[n][:3,:3].T@curl_axis for n in bones}
        original={n:rot(baseline[n]) for n in bones}
        owned=np.array([i for i,n in enumerate(labels) if n in bones])[::2]
        padsets={}
        for n in bones[1:]:
            ids=np.array([i for i,label in enumerate(labels) if label==n])
            distance,near=shells[0].distance(skin0[ids]);direction=near-skin0[ids]
            facing=np.sum(direction*normals[ids],1)/np.maximum(np.linalg.norm(direction,axis=1),1e-8)
            candidates=ids[facing>.35]
            if len(candidates)<12:candidates=ids
            d,_=shells[0].distance(skin0[candidates]);order=np.argsort(np.abs(d))
            # A patch of actual glove surface, not the bone endpoint or the
            # single closest vertex, supplies each pad's contact objective.
            padsets[n]=candidates[order[:max(12,len(candidates)//3)]]
        def posed(delta):
            b=dict(basis)
            for n,angle in zip(bones,delta):b[n]=wxyz(original[n]@Rotation.from_rotvec(axes[n]*math.radians(angle)).as_matrix())
            p,skin=pose(b);return b,p,skin
        def objective(delta):
            _,p,skin=posed(delta);value=0.
            for shell in shells:
                d,_=shell.distance(skin[owned]);penetration=np.minimum(d*1000+.8,0)
                value+=5*np.mean(penetration**2)+3*np.mean(np.sort(penetration**2)[-max(3,len(d)//15):])
                for n,ids in padsets.items():
                    pad,_=shell.distance(skin[ids]);pad*=1000
                    value+=3*(np.mean(pad)-.6)**2+.6*np.mean(np.maximum(pad-1.2,0)**2)
            value+=.006*np.sum(np.array(delta)**2)
            return value
        # Curl in the native flexion plane only. Small counter-adjustments at
        # PIP/DIP keep a pad flat while MCP brings its complete finger inward.
        solved=minimize(objective,[8.,0.,0.],method='Powell',bounds=[(-3,32),(-25,25),(-28,18)],
                        options={'maxiter':28,'xtol':.002,'ftol':.0005})
        basis,p,skin=posed(solved.x);changes[digit]=solved.x.tolist()
        pad_report[digit]={}
        for n,ids in padsets.items():
            bd,_=shells[0].distance(skin0[ids]);ad,_=shells[0].distance(skin[ids])
            pad_report[digit][n]={'authoring_patch_mean_before_mm':float(bd.mean()*1000),'authoring_patch_mean_after_mm':float(ad.mean()*1000)}
        print('FINGER_CONTACT_AUTHORED',gun,digit,solved.x.tolist(),pad_report[digit],flush=True)
    p,skin=pose(basis)
    result[gun]={**old,'revision':'FingerContactV3','finger_basis':basis,'skin':skin.tolist(),
                 'joints':{n:m[:3,3].tolist() for n,m in p.items()},'four_finger_delta_degrees':changes,
                 'authoring_pad_distances':pad_report,'palm_and_thumb_preserved':True,'four_fingers_and_wrist_preserved':False,
                 'method':'Small per-joint flexion-plane rotations bring four glove pads against the shell; rear thumb and wrist unchanged.'}
    (O/'selected_grasp.json').write_text(json.dumps(result),encoding='utf-8')
