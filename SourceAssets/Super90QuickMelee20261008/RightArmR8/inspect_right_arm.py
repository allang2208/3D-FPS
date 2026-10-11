"""Scoped source diagnosis for the user's right wrist/forearm screenshot."""
from pose_io import *
g=json.loads((O.parents[1]/'Super90LoaderR23_20261010/geometry.json').read_text())
cam=json.loads((OLD/'camera_basis.json').read_text());CL=np.array(cam['linear']);CO=np.array(cam['origin_m'])
skin=g['meshes']['Super90_V7_M4_BareArmsV6'];v=np.c_[skin['positions'],np.ones(len(skin['positions']))]
ri={n:np.linalg.inv(m) for n,m in rest.items()}
rf=rest['hand_r'][:3,3]-rest['lowerarm_r'][:3,3]
station=(v[:,:3]-rest['lowerarm_r'][:3,3])@rf/(rf@rf)
ids=np.array([i for i,w in enumerate(skin['weights']) if sum(x for n,x in w.items() if n.endswith('_r'))>.99 and .68<station[i]<1.06])
def axis_bend(p):
    fore=unit(p['hand_r'][:3,3]-p['lowerarm_r'][:3,3]);hd=(rot(p['hand_r'])*rot(rest['hand_r']).inv()).as_matrix()
    return float(np.degrees(np.arccos(np.clip(fore@unit(hd@rf),-1,1))))
def compress(p):
    linear=np.zeros((len(ids),3,3))
    for j,i in enumerate(ids):
        for n,w in skin['weights'][i].items():linear[j]+=w*(p[n]@ri[n])[:3,:3]
    return np.percentile(np.linalg.svd(linear,compute_uv=False)[:,-1],[0,5,50]).tolist()
report={}
for family in ['base',*D['profiles']]:
    poses,_=decode(family);samples=[]
    for f in [0,18,27,40,49,60,82,115,149,182,206,216]:
        p=poses[f];samples.append(dict(frame=f,time=float(times[f]),wrist_axis_bend=axis_bend(p),wrist_skin_singular=compress(p),
            joints_camera_cm={n:(100*(CL@p[n][:3,3]+CO)).tolist() for n in ['upperarm_r','lowerarm_r','hand_r']},
            wrist_aligned_fore_direction_camera=(CL@(rot(p['hand_r'])*rot(rest['hand_r']).inv()).as_matrix()@unit(rf)).tolist()))
    report[family]=samples
(O/'source_diagnosis.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report['base'],indent=2),flush=True)
