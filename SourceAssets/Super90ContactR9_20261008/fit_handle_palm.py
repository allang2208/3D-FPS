"""Fit actual V7 skin to convex components of the saved game prop."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json,trimesh
from pathlib import Path
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
O=Path(__file__).parent;D=np.load(O/'fit_inputs.npz');names=D['names'].tolist();ix={n:i for i,n in enumerate(names)}
vs=D['vertices'];ws=D['weights'];fs=D['faces'];parents=D['parents'];rest=D['rest'];ri=np.linalg.inv(rest)
finger_names=D['finger_names'].tolist();selected=['hand_l']+finger_names;select_ids=[ix[n] for n in selected]
ids=np.flatnonzero(np.sum(ws[:,select_ids],axis=1)>.995);v=vs[ids];w=ws[ids];dominant=np.argmax(w,axis=1)
pre={n:(np.flatnonzero(w[:,ix[n]]>1e-6),v@ri[ix[n]].T) for n in selected}
base_hand=D['hand'];base_local={n:m for n,m in zip(finger_names,D['finger_local'])}
ph=ix['WPN_SOCKET_Magazine'];pf=fs[(D['labels']=='props')&np.all(ws[fs,ph]>.99,axis=1)]
bar_scale=np.array([.79,.79,.845]); mesh=trimesh.Trimesh(vertices=(vs@ri[ph].T)[:,:3]*bar_scale,faces=pf,process=True);mesh.remove_unreferenced_vertices()
parts=mesh.split(only_watertight=False);planes=[]
for part in parts:
    hull=ConvexHull(part.vertices);eq=np.unique(np.round(hull.equations,8),axis=0);planes.append(eq)
print('HANDLE_COMPONENTS',len(parts),[len(p) for p in planes],flush=True)
def sdf(points):
    return np.min(np.stack([np.max(points@p[:,:3].T+p[:,3],axis=1) for p in planes]),axis=0)
def matrices(hand,local):
    out={'hand_l':hand}
    for n in finger_names:out[n]=out[names[parents[ix[n]]]]@local[n]
    return out
def skin(out):
    points=np.zeros((len(v),3))
    for n in selected:
        valid,p=pre[n];points[valid]+=(p[valid]@out[n].T)[:,:3]*w[valid,ix[n],None]
    return points
original=matrices(base_hand,base_local);joints=[n for n in finger_names if 'metacarpal' not in n]
axis={n:original[n][:3,:3].T@np.array([0.,0.,1.]) for n in joints}
a,b,c=[original[n][:3,3] for n in ('thumb_01_l','thumb_02_l','thumb_03_l')]
thumb=np.cross(b-a,c-b);thumb/=np.linalg.norm(thumb)
for n in joints:
    if n.startswith('thumb'):axis[n]=original[n][:3,:3].T@thumb
initial=skin(original);dist=sdf(initial);contacts={}
palm_ids=np.flatnonzero(np.isin(dominant,[ix[n] for n in selected if n=='hand_l' or 'metacarpal' in n]))
palm_local=(np.c_[initial[palm_ids],np.ones(len(palm_ids))]@np.linalg.inv(base_hand).T)[:,:3]
palm_planes=np.unique(np.round(ConvexHull(palm_local).equations,8),axis=0)
bar_points=np.vstack([part.vertices for part in parts]+[np.array([[0.,0.,0.]])])
def palm_distance(hand):
    pp=(np.c_[bar_points,np.ones(len(bar_points))]@np.linalg.inv(hand).T)[:,:3]
    return np.max(pp@palm_planes[:,:3].T+palm_planes[:,3],axis=1)
for n in ['hand_l']+joints:
    rows=np.flatnonzero(dominant==ix[n])
    if len(rows):contacts[n]=rows[np.argsort(np.abs(dist[rows]))[:10]]
def pose(x):
    hand=base_hand.copy();hand[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@hand[:3,:3];hand[:3,3]+=x[:3]
    local={n:m.copy() for n,m in base_local.items()}
    for n,a in zip(joints,x[6:]):local[n][:3,:3]=local[n][:3,:3]@Rotation.from_rotvec(axis[n]*a).as_matrix()
    return hand,local,matrices(hand,local)
active=np.arange(len(ids))[::3]
def residual(x):
    hand_now,_,m=pose(x);points=skin(m);d=sdf(points)
    pen=np.minimum(d[active]-.0012,0)*1000*100/np.sqrt(len(active))
    # The nearest genuine skin patches remain near the bar; palm and fingertips
    # are separate constraints. Native finger lengths and scales never change.
    contact=np.concatenate([np.maximum(np.abs(d[rows]-.0025)-.002,0)*1000*.08/np.sqrt(len(rows)) for rows in contacts.values()])
    return np.r_[pen,contact,np.minimum(palm_distance(hand_now)-.0015,0)*1000*100/np.sqrt(len(bar_points)),x[:3]*1000*.015,x[3:6]*.12,x[6:]*.08]
bounds=np.r_[[.05]*3,[np.deg2rad(35)]*3,[np.deg2rad(30)]*len(joints)]
x=np.zeros(len(bounds));x[0]=-.027
for stride in (3,1):
    active=np.arange(len(ids))[::stride]
    result=least_squares(residual,x,bounds=(-bounds,bounds),max_nfev=180,ftol=2e-7,xtol=2e-7,gtol=1e-5,diff_step=.002)
    x=result.x;hand,local,m=pose(x);d=sdf(skin(m))
    print('FIT',stride,result.nfev,'inside',sum(d<0),'min_mm',min(d)*1000,'parameters',x[:6].tolist(),flush=True)
out=json.loads((O.parent/'Super90ContactR8_20261008/hand_fit.json').read_text())
out['loader_hand_in_handle']=hand.tolist();out['loader_finger_local']={n:m.tolist() for n,m in local.items()}
print('PALM_PEN_MM',float(min(palm_distance(hand))*1000),flush=True); out['loader_bar_scale']=bar_scale.tolist(); out['loader_surface_fit']={'min_clearance_mm':float(min(d)*1000),'inside_vertices':int(sum(d<0)),
 'translation_m':x[:3].tolist(),'rotation_degrees':np.rad2deg(x[3:6]).tolist(),
 'joint_degrees':dict(zip(joints,np.rad2deg(x[6:]).tolist())),
 'contact_gaps_mm':{n:float(np.median(d[rows])*1000) for n,rows in contacts.items()}}
(O/'hand_fit.json').write_text(json.dumps(out,indent=2))
