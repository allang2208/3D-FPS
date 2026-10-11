"""Source-only comparison of the reported right wrist and stock contact."""
from pose_io import *
from support_geometry import skinned,clearance
g=json.loads((O.parents[1]/'Super90LoaderR23_20261010/geometry.json').read_text())
mesh=g['meshes']['Super90_V7_M4_BareArmsV6'];v=np.c_[mesh['positions'],np.ones(len(mesh['positions']))]
rf=rest['hand_r'][:3,3]-rest['lowerarm_r'][:3,3];ri={n:np.linalg.inv(m) for n,m in rest.items()}
s=(v[:,:3]-rest['lowerarm_r'][:3,3])@rf/(rf@rf)
ids=np.array([i for i,w in enumerate(mesh['weights']) if sum(x for n,x in w.items() if n.endswith('_r'))>.99 and .68<s[i]<1.06])
weights={n:np.array([mesh['weights'][i].get(n,0) for i in ids]) for n in names}
weights={n:w for n,w in weights.items() if w.max()>0}
def compressed(p):
    linear=sum(w[:,None,None]*(p[n]@ri[n])[:3,:3] for n,w in weights.items())
    return np.percentile(np.linalg.svd(linear,compute_uv=False)[:,-1],[0,5,50]).tolist()
auth=json.loads((O/'authored_poses.json').read_text());report={};motion={}
for family in ['base',*D['profiles']]:
    old,_=decode(family);rows=[]
    for f in [0,18,27,40,49,60,82,115,149,182,206,216]:
        a=old[f];b={n:np.array(m) for n,m in auth[family][f].items()}
        lengths=lambda p:[float(np.linalg.norm(p[j][:3,3]-p[i][:3,3])) for i,j in [('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]]
        fixed=['WPN_root',*[n for n in names if n.endswith('_l')]]
        contacts=[]
        for finger in ['thumb','index','middle','ring','pinky']:
            n=finger+'_03_r';previous=finger+'_02_r'
            tip=ri[n]@np.r_[rest[n][:3,3]+.70*(rest[n][:3,3]-rest[previous][:3,3]),1.]
            contacts.append(float(1000*np.linalg.norm(((a[n]-b[n])@tip)[:3])))
        rows.append(dict(frame=f,before_wrist_singular=compressed(a),after_wrist_singular=compressed(b),
            upper_fore_length_error_mm=(1000*(np.array(lengths(b))-lengths(a))).tolist(),
            unchanged_gun_left_matrix_max_error=float(max(np.max(np.abs(a[n]-b[n])) for n in fixed)),
            fingertip_contact_displacement_mm=contacts,
            sampled_stock_clearance_mm=float(1000*np.min(clearance(skinned(b),np.linalg.inv(b['WPN_root']@ri['WPN_root']))))))
    report[family]=rows
    def elbow_steps(poses):
        points=np.array([np.array(p['lowerarm_r'])[:3,3] for p in poses])
        return float(100*np.max(np.linalg.norm(np.diff(points,axis=0),axis=1)))
    motion[family]=dict(before_max_elbow_step_cm=elbow_steps(old),after_max_elbow_step_cm=elbow_steps(auth[family]))
(O/'source_wrist_comparison.json').write_text(json.dumps(report,indent=2))
(O/'source_motion_continuity.json').write_text(json.dumps(motion,indent=2))
print(json.dumps({f:[r for r in rows if r['frame'] in (40,49)] for f,rows in report.items()},indent=2),flush=True)
