"""SVD front-half grasp: natural local thumb hinges, no rear-edge reach.

Fits the existing glove skin without changing rest transforms, bone lengths,
joint translations, metacarpals, mesh dimensions or skinning.
"""
import ast,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares,minimize
O=Path(__file__).parent;S=O.parent
d=json.loads((S/'SVDNaturalGrasp20260923/inputs.json').read_text())
old=json.loads((S/'SVDReloadHandRepair20260923/grasp_fit.json').read_text())
donor=json.loads((S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
tree=ast.parse((S/'SVDMagazineFit20260923/fit_grasp.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Shell'],type_ignores=[]),'<shell>','exec'))
shell=Shell(d['magazine']);names=d['names'];parent=d['parents'];rest={n:np.array(m) for n,m in d['rest'].items()}
local={n:np.linalg.inv(rest[parent[n]])@rest[n] for n in names[1:]}
V=np.c_[d['vertices'],np.ones(len(d['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in d['weights']]);weights/=weights.sum(1)[:,None]
bound={n:V@np.linalg.inv(rest[n]).T for n in names}
active={n:np.flatnonzero(weights[:,j]>0) for j,n in enumerate(names)}
pads={n:np.array(ids) for n,ids in old['pad_regions'].items()};palm=np.array(old['palm_region'])
Q0={n:R.from_matrix(np.array(donor['basis'][n])[:3,:3]) for n in names[1:]}
H0=np.array(old['hand_in_mag']);digits=['index','middle','ring','pinky']
faces=np.array([[f[0],f[i],f[i+1]] for f in d['faces'] for i in range(1,len(f)-1)])
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)

def posed(x):
 H=H0.copy();H[:3,3]+=x[:3]/1000;H[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H0[:3,:3]
 Q={n:q.as_matrix() for n,q in Q0.items()}
 for j,f in enumerate(digits):
  mcp,pip=x[6+2*j:8+2*j]
  for k,angle in [('01',mcp),('02',pip),('03',pip*.65)]:
   n=f+'_'+k+'_l';Q[n]=R.from_rotvec(Q0[n].as_rotvec()*(angle/(36 if k=='03' else 48))).as_matrix()
 # Bounded CMC opposition lets the pad face the side wall. It does not aim
 # at the rear edge; the finger hinges remain in one continuous local plane.
 Q['thumb_01_l']=(R.from_euler('yz',x[14:16],degrees=True)*R.from_euler('x',x[18],degrees=True)).as_matrix()
 Q['thumb_02_l']=R.from_euler('z',x[16],degrees=True).as_matrix()
 Q['thumb_03_l']=R.from_euler('z',x[17],degrees=True).as_matrix()
 p={'hand_l':H};v=np.zeros((len(V),3))
 for n in names[1:]:
  b=np.eye(4);b[:3,:3]=Q[n];p[n]=p[parent[n]]@local[n]@b
 for j,n in enumerate(names):
  ids=active[n];v[ids]+=(bound[n][ids]@p[n].T)[:,:3]*weights[ids,j,None]
 return H,Q,p,v

def front_half(v):
 values=[]
 for n,ids in pads.items():
  c=v[ids].mean(0);front,rear=shell.front_rear(c[2]);mid=(front+rear)*.5
  values.extend([(mid-.004-c[1])*1000,(c[2]+.050)*1000,(.045-c[2])*1000])
  if n.startswith('thumb'):
   # Thumb stays on the near broad face beside the front edge. It does not
   # cross the rear edge or oppose the fingers across the entire length.
   values.extend([(c[0]-.011)*1000,(c[1]-front-.002)*1000])
 return np.array(values)

def residual(x):
 H,Q,p,v=posed(x);dist=shell.clearance(v);values=[]
 for n,ids in pads.items():
  values.extend((dist[ids]-.7)*math.sqrt((15 if n.startswith('thumb') else 4)/len(ids)))
  c=v[ids].mean(0)
  if n.startswith('thumb'):
   front,rear=shell.front_rear(c[2])
   values.extend([(c[1]-front-.018)*1000*.45,(c[0]-.021)*1000*.35])
   values.append(5*(1+p[n][0,1]))
 values.extend((dist[palm]-1)*math.sqrt(5/len(palm)))
 values.extend(np.minimum(dist+.65,0)*2)
 values.extend(np.minimum(front_half(v),0)*3)
 values.extend(x[3:6]*.12)
 values.extend((x[6:14]-np.tile([48,38],4))*.08)
 values.extend((x[14:18]-np.array([-25,50,24,20]))*np.array([.12,.10,.1,.12]))
 values.append(x[18]*.15)
 values.append((x[17]-x[16]*.7)*.18)
 return np.array(values)

x=np.r_[json.loads((O/'grasp_front_initial.json').read_text())['parameters'],0.]
x[15]=55;x[16:18]=[24,18]
bounds=[(-30,25),(-35,8),(-20,15)]+[(-25,25)]*3+[(25,80),(18,62)]*4+[(-42,5),(0,85),(12,60),(5,38),(-35,35)]
fit=least_squares(residual,x,bounds=np.array(bounds).T,x_scale='jac',max_nfev=180,ftol=2e-6,xtol=1e-6,gtol=1e-4)
print('SVD_FRONT_GRASP_FIT',float(np.dot(fit.fun,fit.fun)),float(shell.clearance(posed(fit.x)[3]).min()),flush=True)

def constraints(x):
 v=posed(x)[3]
 return np.r_[shell.clearance(np.concatenate([v,v[edges].mean(1),v[faces].mean(1)]))+.65,front_half(v),x[16]*.85+5-x[17]]

fit=minimize(lambda x:float(np.dot(residual(x),residual(x))),fit.x,method='SLSQP',bounds=bounds,
 constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':100,'ftol':.02})
H,Q,p,v=posed(fit.x)

def quat(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]

# Open in the same front-half opposition plane before the entire hand moves
# outward. Do not sweep back to the previous rear-edge thumb pose on release.
open_x=fit.x.copy();open_x[6:14]*=.55;open_x[16:18]*=.5
opened=posed(open_x)[1]
out={'hand_in_mag':H.tolist(),'finger_basis':{n:quat(q) for n,q in Q.items()},'open_basis':{n:quat(q) for n,q in opened.items()},
 'parameters':fit.x.tolist(),'optimizer_success':bool(fit.success),'optimizer_message':str(fit.message),
 'minimum_clearance_mm':float(shell.clearance(v).min()),'pad_regions':{n:ids.tolist() for n,ids in pads.items()},'palm_region':palm.tolist(),
 'pad_means_mm':{n:float(shell.clearance(v[ids]).mean()) for n,ids in pads.items()},'palm_mean_mm':float(shell.clearance(v[palm]).mean()),
 'pad_centers_mag_mm':{n:(v[ids].mean(0)*1000).tolist() for n,ids in pads.items()},
 'front_half_margin_mm':float(front_half(v).min()),
 'donor':str(S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json'),
 'method':'Front-half only; thumb on near broad face beside front edge; natural rest-local CMC opposition with no rear reach; grouped finger hinges; unchanged joint lengths and scale',
 'game_tested':False}
(O/'grasp_candidate.json').write_text(json.dumps(out,indent=2))
print('SVD_FRONT_GRASP_RESULT',{k:out[k] for k in ['optimizer_success','optimizer_message','parameters','front_half_margin_mm','pad_means_mm','palm_mean_mm']},flush=True)
