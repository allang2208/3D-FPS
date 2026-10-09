import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O/'pydeps'));import igl
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
from scipy.ndimage import map_coordinates
from scipy.optimize import least_squares
D=np.load(O/'fit_inputs.npz');names=D['names'].tolist();ix={n:i for i,n in enumerate(names)};rest=D['rest'];ri=np.linalg.inv(rest);parents=D['parents'];vs=D['vertices'];ws=D['weights'];idle=D['idle']
digits=D['finger_names'].tolist();selected=['hand_l']+digits;ids=np.flatnonzero(ws[:,[ix[n] for n in selected]].sum(axis=1)>.995);v=vs[ids];w=ws[ids];dominant=np.argmax(w,axis=1)
weighted={n:np.flatnonzero(w[:,ix[n]]>1e-6) for n in selected};pre={n:v[weighted[n]]@ri[ix[n]].T for n in selected}
seeds=json.loads((O/'grip_hand_seeds.json').read_text());parts=json.loads((O/'Diagnostics/foregrip_geometry.json').read_text());gun=np.load(O/'gun_idle_mesh.npz');mount=idle[ix['WPN_root']]@ri[ix['WPN_root']]
def matrices(h,local):
 p={'hand_l':h}
 for n in digits:p[n]=p[names[parents[ix[n]]]]@local[n]
 return p
def skin(p):
 out=np.zeros((len(ids),3))
 for n in selected:
  j=ix[n];vi=weighted[n];out[vi]+=(pre[n]@p[n].T)[:,:3]*w[vi,j,None]
 return out
out={}
for family in seeds:
 hand=np.array(seeds[family]['hand']);local={n:np.array(m) for n,m in seeds[family]['local'].items()};initial=matrices(hand,local);points=skin(initial)
 V=gun['vertices'].copy();F=gun['faces'].copy();grip=[]
 for part in (('vertical','tactical_vertical') if family=='vertical' else (family,)):
  vv=np.array(parts[part]['vertices']);vv=(np.c_[vv,np.ones(len(vv))]@mount.T)[:,:3];ff=np.array(parts[part]['faces']);F=np.vstack([F,ff+len(V)]);V=np.vstack([V,vv]);grip.append(vv)
 origin=points.min(axis=0)-.04;upper=points.max(axis=0)+.04;step=.00125;shape=np.ceil((upper-origin)/step).astype(int)+1
 q=np.stack(np.meshgrid(*(np.arange(n)*step+v for n,v in zip(shape,origin)),indexing='ij'),axis=-1).reshape(-1,3)
 distances=igl.signed_distance(q,V,F,igl.SIGNED_DISTANCE_TYPE_UNSIGNED)[0];inside=np.abs(igl.fast_winding_number(V,F,q))>.5;distances[inside]*=-1;grid=distances.reshape(shape)
 np.savez_compressed(O/('grip_sdf_'+family+'.npz'),values=grid.astype(np.float32),origin=origin,step=step)
 def sdf(pp):return map_coordinates(grid,((pp-origin)/step).T,order=1,mode='nearest')
 joints=[n for n in digits if 'metacarpal' not in n];axes={}
 for digit in ('thumb','index','middle','ring','pinky'):
  a,b,c=[initial[f'{digit}_0{i}_l'][:3,3] for i in (1,2,3)];axis=np.cross(b-a,c-b);axis/=np.linalg.norm(axis)
  for n in joints:
   if n.startswith(digit):axes[n]=initial[n][:3,:3].T@axis
 near={n:np.flatnonzero(dominant==ix[n]) for n in selected};tips=['hand_l']+[d+'_03_l' for d in ('thumb','index','middle','ring','pinky')]
 palm_ids=np.flatnonzero(np.isin(dominant,[ix[n] for n in selected if n=='hand_l' or 'metacarpal' in n]));palm_local=(np.c_[points[palm_ids],np.ones(len(palm_ids))]@np.linalg.inv(hand).T)[:,:3];palm_planes=np.unique(np.round(ConvexHull(palm_local).equations,8),axis=0);grip_samples=np.vstack(grip)[::15]
 def pose(x):
  h=hand.copy();h[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@h[:3,:3];h[:3,3]+=x[:3];loc={n:m.copy() for n,m in local.items()}
  for n,a in zip(joints,x[6:]):loc[n][:3,:3]=loc[n][:3,:3]@Rotation.from_rotvec(axes[n]*a).as_matrix()
  return h,loc,matrices(h,loc)
 active=np.arange(len(ids))[::3]
 def residual(x):
  h,loc,p=pose(x);d=sdf(skin(p));pen=np.minimum(d[active]-.002,0)*1000*100/np.sqrt(len(active));contact=np.concatenate([np.maximum(np.partition(d[near[n]],5)[:5]-.003,0)*1000*.8 for n in tips])
  pp=(np.c_[grip_samples,np.ones(len(grip_samples))]@np.linalg.inv(h).T)[:,:3];palm=np.max(pp@palm_planes[:,:3].T+palm_planes[:,3],axis=1)
  return np.r_[pen,contact,np.minimum(palm-.001,0)*1000*50/np.sqrt(len(palm)),x[:3]*1000*.015,x[3:6]*.2,x[6:]*.15]
 limits=np.r_[[.035]*3,[np.deg2rad(25)]*3,[np.deg2rad(45)]*len(joints)];x=np.full(len(limits),.0001)
 for stride in (3,1):
  active=np.arange(len(ids))[::stride];fit=least_squares(residual,x,bounds=(-limits,limits),max_nfev=160,ftol=1e-7,xtol=1e-7,gtol=1e-5,diff_step=.002);x=fit.x;h,loc,p=pose(x);d=sdf(skin(p));print('GRIP_FIT',family,stride,fit.nfev,'inside',sum(d<0),'min_mm',min(d)*1000,flush=True)
 out[family]={'hand':h.tolist(),'local':{n:m.tolist() for n,m in loc.items()},'parameters':x.tolist(),'inside_vertices':int(sum(d<0)),'min_mm':float(min(d)*1000)};(O/'grip_hand_fits.json').write_text(json.dumps(out,indent=2))
