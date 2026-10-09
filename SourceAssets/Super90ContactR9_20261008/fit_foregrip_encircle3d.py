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
seeds=json.loads((O/'grip_hand_encircle2.json').read_text());parts=json.loads((O/'Diagnostics/foregrip_geometry.json').read_text());gun=np.load(O/'gun_idle_mesh.npz');mount=idle[ix['WPN_root']]@ri[ix['WPN_root']]
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
 hand=np.array(seeds[family]['hand']);local={n:np.array(m) for n,m in seeds[family]['local'].items()};initial=matrices(hand,local)
 field=np.load(O/('grip_sdf_'+family+'.npz'));grid=field['values'].astype(float);origin=field['origin'];step=field['step']
 def sdf(pp):return map_coordinates(grid,((pp-origin)/step).T,order=1,mode='nearest')
 joints=list(digits);near={n:np.flatnonzero(dominant==ix[n]) for n in selected};tips=['hand_l']+[d+'_03_l' for d in ('thumb','index','middle','ring','pinky')]
 def pose(x):
  h=hand.copy();h[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@h[:3,:3];h[:3,3]+=x[:3]*.01;loc={n:m.copy() for n,m in local.items()}
  for i,n in enumerate(joints):loc[n][:3,:3]=loc[n][:3,:3]@Rotation.from_rotvec(x[6+3*i:9+3*i]).as_matrix()
  return h,loc,matrices(h,loc)
 active=np.arange(len(ids))[::3];contactweight=0
 def residual(x):
  h,loc,p=pose(x);d=sdf(skin(p));pen=np.minimum(d[active]-.002,0)*1000*100/np.sqrt(len(active));contact=np.concatenate([np.maximum(np.partition(d[near[n]],5)[:5]-.004,0)*1000*contactweight for n in tips])
  return np.r_[pen,contact,x[:3]*.02,x[3:6]*.3,x[6:]*.5]
 limits=np.r_[[5.]*3,[np.deg2rad(35)]*3,*[[np.deg2rad(15 if 'metacarpal' in n else 50)]*3 for n in joints]];x=np.zeros(len(limits))
 for stride,contactweight in ((3,0),(3,.08),(1,.08)):
  active=np.arange(len(ids))[::stride];fit=least_squares(residual,x,bounds=(-limits,limits),max_nfev=200,ftol=1e-6,xtol=1e-7,gtol=1e-5);x=fit.x;h,loc,p=pose(x);d=sdf(skin(p));print('GRIP_3D',family,stride,contactweight,fit.nfev,'inside',sum(d<0),'min_mm',min(d)*1000,flush=True)
 out[family]={'hand':h.tolist(),'local':{n:m.tolist() for n,m in loc.items()},'parameters':x.tolist(),'inside_vertices':int(sum(d<0)),'min_mm':float(min(d)*1000)};(O/'grip_hand_encircle3d.json').write_text(json.dumps(out,indent=2))
