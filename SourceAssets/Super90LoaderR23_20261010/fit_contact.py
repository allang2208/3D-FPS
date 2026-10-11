"""Fit the existing grasp around the real handle, including receiver clearance."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares
O=Path(__file__).parent;S=O.parent
d=json.loads((O/'geometry.json').read_text());rest={n:np.array(m) for n,m in d['rest'].items()};ri={n:np.linalg.inv(m) for n,m in rest.items()};parents=d['parents']
p={n:np.array(m) for n,m in json.loads((O/'source_poses.json').read_text())['empty'][150].items()}
gun=p['WPN_root']@ri['WPN_root'];gi=np.linalg.inv(gun)
mesh=d['meshes']['Super90_V7_M4_BareArmsV6'];weights=mesh['weights'];v=np.c_[mesh['positions'],np.ones(len(mesh['positions']))]
digits=[n for n in rest if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
ids=np.array([i for i,w in enumerate(weights) if sum(a for n,a in w.items() if n in digits or n=='hand_l')>.98])[::2]
groups={n:(np.array([j for j,i in enumerate(ids) if weights[i].get(n,0)>1e-5]),None) for n in ['hand_l',*digits]}
for n,(ix,_) in list(groups.items()):groups[n]=(ix,np.array([weights[ids[j]][n] for j in ix]),(v[ids[ix]]@ri[n].T))
local={n:np.linalg.inv(p[parents[n]])@p[n] for n in digits};h0=gi@p['hand_l']
body=d['meshes']['Super90_body'];bv=np.array(body['positions'])
# Right-hand-side silhouette of the actual mesh, sampled with +X ray casts.
ys=np.arange(-.28,.101,.001);zs=np.arange(-.97,-.689,.001);surface=np.full((len(ys),len(zs)),-1.)
for face in body['faces']:
    for k in range(1,len(face)-1):
        tri=bv[[face[0],face[k],face[k+1]]];a,b,c=tri
        den=(b[2]-c[2])*(a[1]-c[1])+(c[1]-b[1])*(a[2]-c[2])
        if abs(den)<1e-12:continue
        iy=np.flatnonzero((ys>=tri[:,1].min())&(ys<=tri[:,1].max()));iz=np.flatnonzero((zs>=tri[:,2].min())&(zs<=tri[:,2].max()))
        if not len(iy) or not len(iz):continue
        y,z=np.meshgrid(ys[iy],zs[iz],indexing='ij')
        u=((b[2]-c[2])*(y-c[1])+(c[1]-b[1])*(z-c[2]))/den
        vv=((c[2]-a[2])*(y-c[1])+(a[1]-c[1])*(z-c[2]))/den;ww=1-u-vv
        xx=np.where((u>=0)&(vv>=0)&(ww>=0),u*a[0]+vv*b[0]+ww*c[0],-1.)
        surface[np.ix_(iy,iz)]=np.maximum(surface[np.ix_(iy,iz)],xx)
lookup=RegularGridInterpolator((ys,zs),surface,bounds_error=False,fill_value=-1.)
np.savez_compressed(O/'receiver_surface.npz',ys=ys,zs=zs,surface=surface)
handle=d['meshes']['Super90_bolt'];hv=np.c_[handle['positions'],np.ones(len(handle['positions']))]
knob=hv[hv[:,0]>.026]@(gi@p['WPN_bolt']@ri['WPN_bolt']).T;knob=knob[:,:3];centre=knob.mean(0);tree=cKDTree(knob)
flex=json.loads((S/'Super90LoaderR21_20261010/grasp_target.json').read_text())['anatomical_flexion_axes'];flex={n:np.array(a) for n,a in flex.items()}
fit_digits=[f'{digit}_{k:02}_l' for digit in ('index','middle') for k in (1,2,3)]
def evaluate(a):
    rot=R.from_rotvec(np.deg2rad(a[3:6])).as_matrix();move=np.eye(4);move[:3,:3]=rot;move[:3,3]=centre+a[:3]*.001-rot@centre
    w={'hand_l':move@h0};loc={n:m.copy() for n,m in local.items()}
    for n,angle in zip(fit_digits,a[6:12]):loc[n][:3,:3]=R.from_rotvec(flex[n]*np.deg2rad(angle)).as_matrix()@loc[n][:3,:3]
    loc['thumb_01_l'][:3,:3]=R.from_rotvec(np.deg2rad(a[12:15])).as_matrix()@loc['thumb_01_l'][:3,:3]
    for n in digits:w[n]=w[parents[n]]@loc[n]
    points=np.zeros((len(ids),3))
    for n,(ix,weights_n,vertices) in groups.items():points[ix]+=(vertices@w[n].T)[:,:3]*weights_n[:,None]
    return w,loc,points,move
zero=np.zeros(15);_,_,start,_=evaluate(zero);pads={};targets={}
for n in ('index_02_l','middle_02_l'):
    ix=np.array([j for j,i in enumerate(ids) if weights[i].get(n,0)>.65]);dist,nearest=tree.query(start[ix]);chosen=ix[np.argsort(dist)[:8]]
    pads[n]=chosen;targets[n]=knob[tree.query(start[chosen].mean(0))[1]]
def objective(a):
    _,_,points,_=evaluate(a)
    hit=np.maximum(0,lookup(points[:,1:3])+.003-points[:,0])/.0015
    contact=np.concatenate([(points[ix].mean(0)-targets[n])/.0035 for n,ix in pads.items()])
    return np.r_[hit,contact,a[:3]/10,a[3:6]/18,a[6:12]/12,a[12:15]/24]
seed=zero.copy();seed[4]=-18
result=least_squares(objective,seed,bounds=([-15]*3+[-35]*3+[-18]*6+[-40]*3,[20]*3+[35]*3+[18]*6+[40]*3),diff_step=.001,max_nfev=180)
w,loc,points,move=evaluate(result.x)
out=dict(method='Grasp about real bolt tip with full palm/thumb receiver-side surface constraint',
    hand_gun_delta=move.tolist(),handle_centre_gun=centre.tolist(),finger_local={n:m.tolist() for n,m in loc.items()},parameters=result.x.tolist(),
    before_receiver_penetration_mm=float(np.maximum(0,lookup(start[:,1:3])-start[:,0]).max()*1000),
    after_receiver_penetration_mm=float(np.maximum(0,lookup(points[:,1:3])-points[:,0]).max()*1000),
    pad_error_mm={n:float(np.linalg.norm(points[ix].mean(0)-targets[n])*1000) for n,ix in pads.items()},
    pad_indices={n:ids[ix].tolist() for n,ix in pads.items()},pad_targets_gun={n:t.tolist() for n,t in targets.items()},runtime_tested=False)
(O/'contact_fit.json').write_text(json.dumps(out,indent=2));print('R23_CONTACT',json.dumps({k:out[k] for k in ('parameters','before_receiver_penetration_mm','after_receiver_penetration_mm','pad_error_mm')}),flush=True)
