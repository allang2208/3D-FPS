"""Keep the four-finger front wrap; author a distinct rear-side thumb wrap."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.spatial import cKDTree
from scipy.optimize import minimize
import trimesh

O=Path(__file__).parent;BASE=O.parent
data=json.loads((BASE/'fit_input.json').read_text())
before=json.loads((BASE/'selected_grasp.json').read_text())
names=data['names'];rest={n:np.array(m) for n,m in data['rest'].items()}
inv={n:np.linalg.inv(m) for n,m in rest.items()}
local={n:inv[data['parents'][n]]@rest[n] for n in names[1:]}
vertices=np.c_[np.array(data['vertices']),np.ones(len(data['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in data['weights']]);weights/=weights.sum(axis=1)[:,None]
bound={n:vertices@inv[n].T for n in names}
thumb=['thumb_01_l','thumb_02_l','thumb_03_l']
def unit(v):return v/np.linalg.norm(v)
def frame(direction,normal):
    d=unit(direction);n=unit(normal-d*np.dot(normal,d));return np.column_stack((d,np.cross(n,d),n))
def quat(q):return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def wxyz(m):
    q=Rotation.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
rd=[rest[thumb[1]][:3,3]-rest[thumb[0]][:3,3],rest[thumb[2]][:3,3]-rest[thumb[1]][:3,3]]
rd.append(rest[thumb[2]][:3,:3]@rest[thumb[1]][:3,:3].T@rd[1])
restnormal=unit(np.cross(rd[0],rd[1]))
correction=[frame(d,restnormal).T@rest[n][:3,:3] for n,d in zip(thumb,rd)]
labels=np.array(data['labels']);ids=np.array([i for i,n in enumerate(labels) if n in thumb])
padids=np.array([i for i,n in enumerate(labels) if n=='thumb_03_l'])
report={}
for gun,old in before.items():
    H=np.array(old['hand_in_mag'])
    def pose(params):
        az,el,roll,mcp,ip=np.radians(params)
        direction=np.array([math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)])
        reference=frame(direction,np.array([0.,0.,1.]))
        reference=reference@Rotation.from_rotvec([roll,0,0]).as_matrix()
        p={'hand_l':H.copy()};basis=dict(old['finger_basis'])
        for n in names[1:]:
            parent=data['parents'][n];m=p[parent]@local[n]
            if n in thumb:
                index=thumb.index(n);angle=[0,mcp,mcp+ip][index]
                m[:3,:3]=reference@Rotation.from_rotvec([0,0,angle]).as_matrix()@correction[index]
                b=np.linalg.inv(local[n])@np.linalg.inv(p[parent])@m
                basis[n]=wxyz(b[:3,:3])
            else:
                b=np.eye(4);b[:3,:3]=quat(basis[n]);m=m@b
            p[n]=m
        skin=sum((bound[n]@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
        return p,skin,basis
    mag=data['magazines'][gun]
    faces=[[f[0],f[j],f[j+1]] for f in mag['faces'] for j in range(1,len(f)-1)]
    mesh=trimesh.Trimesh(vertices=mag['vertices'],faces=faces,process=False)
    triangles=mesh.triangles;tree=cKDTree(triangles.mean(1));normals=mesh.face_normals
    def nearest(points):
        _,ix=tree.query(points,k=16)
        near=trimesh.triangles.closest_point(triangles[ix.reshape(-1)],np.repeat(points,16,axis=0)).reshape(len(points),16,3)
        delta=points[:,None,:]-near;ds=np.sum(delta**2,2);which=ds.argmin(1);row=np.arange(len(points))
        return np.sqrt(ds[row,which]),np.sum(delta[row,which]*normals[ix[row,which]],axis=1),near[row,which]
    # The target is the magazine's rear shoulder, opposite the four fingers'
    # negative-Y front edge. Never let a nearest-surface fit select their side.
    target_z=.030 if gun=='AKM' else .030
    section=np.array(mag['vertices']);section=section[np.abs(section[:,2]-target_z)<.007]
    rear=float(np.max(section[:,1]));target=np.array([-.007,rear+.009,target_z])
    seed=np.array([130.,28.,0.,62.,35.])
    def objective(x):
        p,skin,_=pose(x);dist,signed,near=nearest(skin[ids][::2])
        pd,ps,pn=nearest(skin[padids][::2]);j2=p[thumb[1]][:3,3];j3=p[thumb[2]][:3,3]
        # Rear-side thumb contact plus explicit finger/thumb separation has
        # priority over minimum distance to an arbitrary magazine face.
        value=1.2*np.sum(((j3-target)*1000)**2)
        value+=2*np.sum((np.minimum(np.array([j2[1],j3[1]])-(rear-.004),0)*1000)**2)
        value+=5*np.mean((np.minimum(signed+.001,0)*1000)**2)
        value+=1.5*(np.sort(pd*1000)[:max(4,len(pd)//8)].mean()-.6)**2
        value+=.003*np.sum((x-seed)**2)
        return value
    solved=minimize(objective,seed,method='Powell',bounds=[(105,165),(5,45),(-30,30),(25,78),(8,65)],
                    options={'maxiter':24,'xtol':.002,'ftol':.001})
    params=solved.x;p,skin,basis=pose(params)
    opened=params.copy();opened[3]*=.45;opened[4]*=.40
    _,_,open_basis=pose(opened)
    report[gun]={**old,'revision':'ThumbOppositionV2','finger_basis':basis,'open_thumb_basis':{n:open_basis[n] for n in thumb},
                 'skin':skin.tolist(),'joints':{n:m[:3,3].tolist() for n,m in p.items()},
                 'thumb_semantic_degrees':params.tolist(),'rear_contact_target_m':target.tolist(),
                 'thumb_objective':float(solved.fun),'four_fingers_and_wrist_preserved':True,
                 'method':'Four fingers on front edge; thumb CMC opens to rear edge with independent MCP/IP flexion.'}
    print('REAR_THUMB_AUTHORED',gun,params.tolist(),'joint03',p[thumb[2]][:3,3].tolist(),flush=True)
(O/'selected_grasp.json').write_text(json.dumps(report),encoding='utf-8')
