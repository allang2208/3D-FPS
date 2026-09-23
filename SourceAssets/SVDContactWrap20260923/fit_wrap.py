"""Fit an anatomically coupled wrap to the current SVD shell and actual glove."""
import ast,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
O=Path(__file__).parent;S=O.parent
d=json.loads((S/'SVDNaturalGrasp20260923/inputs.json').read_text());prior=json.loads((S/'SVDMagazineFit20260923/grasp_fit.json').read_text())
tree=ast.parse((S/'SVDMagazineFit20260923/fit_grasp.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Shell'],type_ignores=[]),'<shell>','exec'))
shell=Shell(d['magazine']);names=d['names'];parent=d['parents'];rest={n:np.array(m) for n,m in d['rest'].items()}
local={n:np.linalg.inv(rest[parent[n]])@rest[n] for n in names[1:]}
V=np.c_[d['vertices'],np.ones(len(d['vertices']))];labels=np.array(d['labels'])
weights=np.array([[w.get(n,0) for n in names] for w in d['weights']]);weights/=weights.sum(1)[:,None]
bound={n:V@np.linalg.inv(rest[n]).T for n in names}
active={n:np.flatnonzero(weights[:,j]>0) for j,n in enumerate(names)}
faces=np.array([[f[0],f[i],f[i+1]] for f in d['faces'] for i in range(1,len(f)-1)])
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
accepted_input=json.loads((S/'SVDNaturalGrasp20260923/grasp_fit.json').read_text())
wrap_donor=json.loads((S/'M4WrapGrip20260910/wrap_fit.json').read_text())
H0=np.array(accepted_input['hand_in_mag']);Q0={n:R.from_quat([q[1],q[2],q[3],q[0]]).as_matrix() for n,q in wrap_donor['bone_local_rotations'].items()}
H0[0,3]+=.018;H0[1,3]+=.012
digits=['index','middle','ring','pinky']
pads={n:np.array(ids) for n,ids in prior['pad_regions'].items()}

def rz(degrees):return R.from_euler('z',degrees,degrees=True).as_matrix()
def pose(H,Q):
 p={'hand_l':H};v=np.zeros((len(V),3))
 for n in names[1:]:
  b=np.eye(4);b[:3,:3]=Q[n];p[n]=p[parent[n]]@local[n]@b
 for j,n in enumerate(names):
  ids=active[n];v[ids]+=(bound[n][ids]@p[n].T)[:,:3]*weights[ids,j,None]
 return p,v

oldp,oldv=pose(H0,Q0)
palm=np.flatnonzero((labels=='hand_l')&(oldv[:,1]>.002)&(oldv[:,1]<.049)&(oldv[:,2]>-.02))
palm=palm[np.argsort(oldv[palm,0])[:max(20,len(palm)//4)]]

def posed(x):
 H=H0.copy();H[:3,3]+=x[:3]/1000;H[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H0[:3,:3]
 Q={n:m.copy() for n,m in Q0.items()}
 for j,f in enumerate(digits):
  mcp,pip,ratio,spread=x[6+4*j:10+4*j]
  # MCP abduction and flexion only: no axial twisting to reach the shell.
  Q[f+'_01_l']=R.from_euler('y',spread,degrees=True).as_matrix()@rz(mcp)
  Q[f+'_02_l']=rz(pip)
  Q[f+'_03_l']=rz(min(48.,pip*ratio))
 Q['thumb_01_l']=Q0['thumb_01_l']@R.from_rotvec(np.radians(x[22:25])).as_matrix()
 Q['thumb_02_l']=Q0['thumb_02_l']@rz(x[25]);Q['thumb_03_l']=Q0['thumb_03_l']@rz(x[26])
 p,v=pose(H,Q);return H,Q,p,v

def sampled_surface(v,full=False):
 if full:return np.concatenate([v,v[edges].mean(1),v[faces].mean(1)])
 return v

def semantic(v):
 out=[]
 for n,ids in pads.items():
  c=v[ids].mean(0);front,rear=shell.front_rear(c[2]);middle=(front+rear)*.5
  out.extend([1000*(c[1]-middle if n.startswith('thumb') else middle-c[1]),(c[2]+.038)*1000,(.048-c[2])*1000])
 return np.array(out)

def objective(x):
 _,_,_,v=posed(x);dist=shell.clearance(v);value=0.
 for n,ids in pads.items():
  # Whole-pad contact and a natural chain take priority over a lone fingertip.
  value+=np.mean((dist[ids]-.25)**2)*(3.5 if '_02_' in n else 5.)
  c=v[ids].mean(0);front,rear=shell.front_rear(c[2])
  left=-np.interp(c[2],shell.z,shell.support[:,24])
  if '_02_' in n:
   value+=2*((c[1]-(rear if n.startswith('thumb') else front))*1000)**2
  else:
   value+=6*((c[0]-left)*1000)**2
   # A distal pad crosses the edge onto the opposite broad face.
   desired_y=rear-.010 if n.startswith('thumb') else front+.010
   value+=.8*((c[1]-desired_y)*1000)**2
 value+=8*np.mean((dist[palm]-.35)**2)
 value+=.012*np.dot(x[:3],x[:3])+.018*np.dot(x[3:6],x[3:6])+.025*np.dot(x[22:25],x[22:25])
 for j in range(4):
  mcp,pip,ratio,spread=x[6+4*j:10+4*j]
  value+=.018*(mcp-18)**2+.015*(pip-55)**2+.1*spread**2+20*(ratio-.65)**2
 return float(value)

bounds=[(-35,30),(-40,30),(-25,25)]+[(-40,40)]*3
for j in range(4):bounds += [(-15,65),(35,65),(.6,.85),(-14,14)]
bounds += [(-30,30)]*3+[(-12,35),(-10,30)]
x=np.zeros(27)
for j in range(4):x[6+4*j:10+4*j]=[18,45,.7,0]
x[25:]=[10,10]
if (O/'wrap_working.json').exists():x=np.array(json.loads((O/'wrap_working.json').read_text())['parameters'])

def penalty(x):
 H,Q,p,v=posed(x);c=shell.clearance(v);wrong=np.minimum(semantic(v),0)
 return objective(x)+200*np.mean(np.minimum(c+.45,0)**2)+25*min(0,c.min()+.45)**2+20*np.dot(wrong,wrong)
coarse=minimize(penalty,x,method='L-BFGS-B',bounds=bounds,options={'maxiter':200,'maxfun':7000,'ftol':1e-7})
x=coarse.x
(O/'wrap_working.json').write_text(json.dumps({'parameters':x.tolist(),'stage':'coarse'}))
print('SVD_CONTACT_COARSE',round(coarse.fun,3),str(coarse.message),flush=True)

def constraints(x):
 v=posed(x)[3];return np.r_[shell.clearance(sampled_surface(v,True))+.55,semantic(v)]
solution=minimize(objective,x,method='SLSQP',bounds=bounds,constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':110,'ftol':.01})
H,Q,p,v=posed(solution.x)
def wxyz(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
opened={n:m.copy() for n,m in Q.items()}
for j,f in enumerate(digits):
 mcp,pip,ratio,spread=solution.x[6+4*j:10+4*j]
 opened[f+'_01_l']=R.from_euler('y',spread,degrees=True).as_matrix()@rz(max(12,mcp-16))
 opened[f+'_02_l']=rz(max(10,pip-28));opened[f+'_03_l']=rz(max(6,min(48,pip*ratio)-18))
opened['thumb_01_l']=Q['thumb_01_l']@R.from_euler('x',-8,degrees=True).as_matrix()
opened['thumb_02_l']=Q['thumb_02_l']@rz(-12);opened['thumb_03_l']=Q['thumb_03_l']@rz(-10)
out={'hand_in_mag':H.tolist(),'finger_basis':{n:wxyz(q) for n,q in Q.items()},'open_basis':{n:wxyz(q) for n,q in opened.items()},
 'parameters':solution.x.tolist(),'objective':float(solution.fun),'optimizer_success':bool(solution.success),'optimizer_message':str(solution.message),
 'production_clearance_mm':float(shell.clearance(sampled_surface(v,True)).min()),
 'pad_means_mm':{n:float(shell.clearance(v[ids]).mean()) for n,ids in pads.items()},'palm_mean_mm':float(shell.clearance(v[palm]).mean()),
 'joint_flexion_deg':{f:{'MCP':float(solution.x[6+4*j]),'PIP':float(solution.x[7+4*j]),'DIP':float(min(48,solution.x[7+4*j]*solution.x[8+4*j]))} for j,f in enumerate(digits)},
 'method':'Current evaluated SVD; local X finger length, local Y abduction, local Z flexion; accepted M4 natural thumb and finger grouping adapted to SVD; middle pads on edges and distal pads on opposite broad face; bounded 0.55 mm glove compression',
 'game_tested':False}
(O/'grasp_fit.json').write_text(json.dumps(out,indent=2))
(O/'wrap_working.json').write_text(json.dumps({'parameters':solution.x.tolist(),'stage':'full_surface'}))
print('SVD_CONTACT_FIT',{k:out[k] for k in ['objective','optimizer_success','optimizer_message','production_clearance_mm','pad_means_mm','palm_mean_mm','joint_flexion_deg']},flush=True)
