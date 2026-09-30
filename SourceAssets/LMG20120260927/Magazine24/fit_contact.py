"""Adapt the approved SVD partial wrap to 201's actual curved magazine.

Fit bounded rigid placement and grouped four-finger flex only. Preserve the
approved thumb/metacarpals, rest, skin, segment lengths and scale.
"""
import ast,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares,minimize
O=Path(__file__).parent;P=O.parents[2]
def matrix(t):
 m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
source=P/'SourceAssets/SVDMagazineFit20260923/fit_grasp.py'
tree=ast.parse(source.read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Shell')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'))
rigs=json.loads((O/'sources.json').read_text())['rigs']
surface=json.loads((O.parent/'Refine12/201_surface.json').read_text())
faces=np.array([f for f,i in zip(surface['triangles'],surface['material_ids']) if surface['materials'][i].startswith('M_LMG201_Magazine')])
ids=np.unique(faces);remap={int(v):i for i,v in enumerate(ids)}
restmag=matrix(surface['bones']['WPN_SOCKET_Magazine'])
mag=(np.linalg.inv(restmag)@np.c_[np.array(surface['vertices'])[ids],np.ones(len(ids))].T).T[:,:3]
shell=Shell({'vertices':mag.tolist(),'faces':[[remap[int(v)] for v in f] for f in faces]})
skin=json.loads((P/'SourceAssets/PKMLowpoly20260922/LeftState50/Input/Bare.json').read_text())
donor=json.loads((O/'Sources/akm_base_reload.json').read_text())['poses'][148]
names=[n for n in donor if n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))]
# Read the approved SVD front-half hand in the common physical rest space.
# FBX reflects Y and converts metres to centimetres; retain each UE bone's
# native bind axes instead of copying Blender quaternion components.
svd=json.loads((O/'Sources/svd_blender.json').read_text());F=np.diag([100.,-100.,100.,1.]);Fi=np.linalg.inv(F)
native={n:F@np.array(svd['pose'][n])@np.linalg.inv(np.array(svd['rest'][n]))@Fi@matrix(rigs['201']['bones'][n]) for n in names+['WPN_SOCKET_Magazine']}
finger_local={n:np.linalg.inv(native[rigs['201']['bones'][n]['parent']])@native[n] for n in names if n!='hand_l'}
M=matrix(donor['WPN_SOCKET_Magazine']['world'])
svdG=np.linalg.inv(native['WPN_SOCKET_Magazine'])@native['hand_l']
# The magazine sizes differ; reuse the approved palm orientation and fingers,
# initialize its height from this weapon's action before rigid contact placement.
G=svdG.copy();H=M@G
world={n:matrix(v['world']) for n,v in donor.items()};world['hand_l']=H
for n in names:
 if n!='hand_l':world[n]=world[rigs['201']['bones'][n]['parent']]@finger_local[n]
labels=[max(w,key=w.get) for w in skin['weights']]
ids=[i for i,n in enumerate(labels) if n in names and sum(w for k,w in skin['weights'][i].items() if k in names)>.995]
labels=np.array([labels[i] for i in ids]);verts=np.c_[np.array(skin['positions'])[ids],np.ones(len(ids))]
weights=[skin['weights'][i] for i in ids];posed=np.zeros((len(ids),3))
for n in {n for w in weights for n in w}:
 if n not in donor:raise RuntimeError('Missing weighted donor '+n)
 xf=world[n]@np.linalg.inv(matrix(skin['bones'][n]))
 posed+=(verts@xf.T)[:,:3]*np.array([w.get(n,0) for w in weights])[:,None]
G=np.linalg.inv(M)@H;v=(np.linalg.inv(M)@np.c_[posed,np.ones(len(posed))].T).T[:,:3]
# Fixed SVD contact patches preserve the donor's palmar and finger semantics;
# never let the objective choose a knuckle or nail as its closest contact.
svd_mag=svd['magazines'][0];sv=(np.linalg.inv(native['WPN_SOCKET_Magazine'])@F@np.c_[svd_mag['vertices'],np.ones(len(svd_mag['vertices']))].T).T[:,:3]
donor_shell=Shell({'vertices':sv.tolist(),'faces':svd_mag['faces']})
dist=donor_shell.clearance(v)
pads={}
for n in names:
 if n=='hand_l' or n.endswith(('02_l','03_l')):
  group=np.flatnonzero(labels==n)
  if len(group):pads[n]=group[np.argsort(dist[group])[:max(8,len(group)//6)]]
fingers=['index','middle','ring','pinky'];axes={}
Wmag={n:np.linalg.inv(M)@world[n] for n in names}
for f in fingers:
 a,b,c=[Wmag[f+'_'+k+'_l'] for k in ['01','02','03']]
 axis=np.cross(b[:3,3]-a[:3,3],c[:3,3]-b[:3,3]);axis/=np.linalg.norm(axis)
 for k in ['01','02','03']:
  n=f+'_'+k+'_l';axes[n]=Wmag[n][:3,:3].T@axis
bound={n:(np.linalg.inv(matrix(skin['bones'][n]))@verts.T).T for n in names}
ws={n:np.array([w.get(n,0) for w in weights]) for n in names}
def articulated(x):
 local={n:m.copy() for n,m in finger_local.items()}
 for j,f in enumerate(fingers):
  for k,delta in [('01',x[6+2*j]),('02',x[7+2*j]),('03',x[7+2*j]*.65)]:
   n=f+'_'+k+'_l';local[n][:3,:3]=local[n][:3,:3]@R.from_rotvec(axes[n]*np.radians(delta)).as_matrix()
 pose={'hand_l':H};vv=np.zeros_like(posed)
 for n in names:
  if n!='hand_l':pose[n]=pose[rigs['201']['bones'][n]['parent']]@local[n]
  vv+=(bound[n]@pose[n].T)[:,:3]*ws[n][:,None]
 return (np.linalg.inv(M)@np.c_[vv,np.ones(len(vv))].T).T[:,:3],local
def transformed(x):
 shaped,_=articulated(x)
 rot=R.from_rotvec(np.radians(x[3:6])).as_matrix();p=G[:3,3]
 t=p+np.array(x[:3])/1000-rot@p
 return shaped@rot.T+t,rot,t
def residual(x):
 q,_,_=transformed(x);d=shell.clearance(q);values=[]
 for n,idx in pads.items():
  # Thumb stays in its already approved upward pose; its full length need not
  # be pasted onto the curved shell. Palm and curled fingertips own the grasp.
  importance=.2 if n.startswith('thumb') else 4 if n=='hand_l' else 1.2
  values.extend((d[idx]-1.0)*np.sqrt(importance/len(idx)))
 values.extend(np.minimum(d-.35,0)*8.)
 values.extend(x[:3]*.025);values.extend(x[3:6]*.22);values.extend(x[6:]*.25)
 return np.array(values)
limits=[(-45,80),(-100,90),(-65,55),(-15,15),(-15,15),(-15,15)]+[(-22,22),(-22,22)]*4
# Begin outside the shell on the palm/front side; an already penetrating
# starting pose traps a nonsmooth surface constraint at the wrong wall.
start=np.r_[[8.,15.,-25.,0.,0.,0.],np.tile([-12.,-12.],4)]
# Contact fitting penalizes the complete visible hand surface heavily.
# Average pad error alone otherwise accepts a few buried fingers.
fit=least_squares(residual,start,bounds=np.array(limits).T,max_nfev=180,ftol=1e-6,xtol=1e-6,gtol=1e-5)
q,rot,t=transformed(fit.x);D=np.eye(4);D[:3,:3]=rot;D[:3,3]=t
out={'method':'Actual V7 surface and curved 201 magazine; accepted SVD front-half palm and thumb-up; bounded placement and four-finger flex; native AKM full arm motion, no limb IK',
 'donor_frame':148,'hand_in_mag':(D@G).tolist(),'rigid_delta_mag':D.tolist(),'parameters_mm_degrees':fit.x.tolist(),
 'magazine_bounds_m':[mag.min(0).tolist(),mag.max(0).tolist()],
 'authoring_pad_gaps_mm':{n:float(np.mean(shell.clearance(q[idx]))) for n,idx in pads.items()},
 'authoring_surface_clearance_mm':float(shell.clearance(q).min()),'contact_fit_feasible':bool(fit.success and shell.clearance(q).min()>=0),
 'finger_rotations_changed':True,'runtime_tested':False}
out['finger_adaptation']='Four fingers: bounded MCP/PIP flex only, coupled DIP; accepted SVD thumb and metacarpals preserved'
out['finger_local']={n:{'p':m[:3,3].tolist(),'q':R.from_matrix(m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)).as_quat().tolist(),'s':np.linalg.norm(m[:3,:3],axis=0).tolist()} for n,m in articulated(fit.x)[1].items()}
(O/'contact.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
