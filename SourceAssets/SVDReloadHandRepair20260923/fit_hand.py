"""Adapt grouped finger flexion and the accepted rear-opposed thumb to SVD.

Keep donor metacarpals and finger flexion planes. Fit the complete hand before
small coupled closure adjustments; do not use free per-joint axial twist.
"""
import ast,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares,minimize
O=Path(__file__).parent;S=O.parent
d=json.loads((S/'SVDNaturalGrasp20260923/inputs.json').read_text())
old=json.loads((S/'SVDContactWrap20260923/grasp_fit.json').read_text())
donor=json.loads((S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
tree=ast.parse((S/'SVDMagazineFit20260923/fit_grasp.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Shell'],type_ignores=[]),'<shell>','exec'))
shell=Shell(d['magazine']);names=d['names'];parent=d['parents'];rest={n:np.array(m) for n,m in d['rest'].items()}
local={n:np.linalg.inv(rest[parent[n]])@rest[n] for n in names[1:]}
V=np.c_[d['vertices'],np.ones(len(d['vertices']))];labels=np.array(d['labels'])
weights=np.array([[w.get(n,0) for n in names] for w in d['weights']]);weights/=weights.sum(1)[:,None]
bound={n:V@np.linalg.inv(rest[n]).T for n in names}
active={n:np.flatnonzero(weights[:,j]>0) for j,n in enumerate(names)}
pads={n:np.array(ids) for n,ids in old['pad_regions'].items()};palm=np.array(old['palm_region'])
Q0={n:R.from_matrix(np.array(donor['basis'][n])[:3,:3]) for n in names[1:]}
H0=np.array(old['hand_in_mag']);turn=R.from_euler('z',0,degrees=True).as_matrix();H0[:3,:3]=turn@H0[:3,:3];H0[:3,3]=turn@H0[:3,3]
digits=['index','middle','ring','pinky']
thumb=['thumb_01_l','thumb_02_l','thumb_03_l']
def unit(v):return v/np.linalg.norm(v)
def frame(direction,normal):
 d=unit(direction);n=unit(normal-d*np.dot(normal,d));return np.column_stack((d,np.cross(n,d),n))
rd=[rest[thumb[1]][:3,3]-rest[thumb[0]][:3,3],rest[thumb[2]][:3,3]-rest[thumb[1]][:3,3]]
rd.append(rest[thumb[2]][:3,:3]@rest[thumb[1]][:3,:3].T@rd[1])
restnormal=unit(np.cross(rd[0],rd[1]));thumb_correction=[frame(v,restnormal).T@rest[n][:3,:3] for n,v in zip(thumb,rd)]
faces=np.array([[f[0],f[i],f[i+1]] for f in d['faces'] for i in range(1,len(f)-1)])
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)

def posed(x):
 H=H0.copy();H[:3,3]+=x[:3]/1000;H[:3,:3]=R.from_rotvec(np.radians(x[3:6])).as_matrix()@H0[:3,:3]
 Q={n:q.as_matrix() for n,q in Q0.items()}
 for j,f in enumerate(digits):
  mcp,pip=x[6+2*j:8+2*j]
  for k,angle in [('01',mcp),('02',pip),('03',pip*.65)]:
   n=f+'_'+k+'_l';Q[n]=R.from_rotvec(Q0[n].as_rotvec()*(angle/(36 if k=='03' else 48))).as_matrix()
 # Reuse the accepted AKM semantic thumb chain: a single CMC frame and
 # cumulative MCP/IP angles, converted back through each actual rest frame.
 az,el,roll,mcp,ratio=x[14:19];az,el,roll,mcp=np.radians([az,el,roll,mcp]);ip=mcp*ratio
 direction=np.array([math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)])
 reference=frame(direction,np.array([0.,0.,1.]))@R.from_rotvec([roll,0,0]).as_matrix()
 p={'hand_l':H};v=np.zeros((len(V),3))
 for n in names[1:]:
  if n in thumb:
   j=thumb.index(n);m=p[parent[n]]@local[n]
   m[:3,:3]=reference@R.from_rotvec([0,0,[0,mcp,mcp+ip][j]]).as_matrix()@thumb_correction[j]
   Q[n]=(np.linalg.inv(local[n])@np.linalg.inv(p[parent[n]])@m)[:3,:3];p[n]=m
  else:
   b=np.eye(4);b[:3,:3]=Q[n];p[n]=p[parent[n]]@local[n]@b
 for j,n in enumerate(names):
  ids=active[n];v[ids]+=(bound[n][ids]@p[n].T)[:,:3]*weights[ids,j,None]
 return H,Q,p,v

def semantic(v):
 values=[]
 for n,ids in pads.items():
  c=v[ids].mean(0)
  front,rear=shell.front_rear(c[2]);mid=(front+rear)*.5
  values.extend([(c[1]-mid if n.startswith('thumb') else mid-c[1])*1000,(c[2]+.050)*1000,(.051-c[2])*1000])
 return np.array(values)

def residual(x):
 H,Q,p,v=posed(x);dist=shell.clearance(v);values=[]
 for n,ids in pads.items():
  values.extend((dist[ids]-.4)*math.sqrt(5/len(ids)))
  # Preserve the accepted front-finger / rear-thumb opposition direction.
  desired_normal=np.array([0.,1.,0.]) if n.startswith('thumb') else np.array([0.,-1.,0.])
  values.append(2*(1+np.dot(p[n][:3,1],desired_normal)))
 values.extend((dist[palm]-.6)*math.sqrt(6/len(palm)))
 values.extend(np.minimum(dist+.65,0)*2)
 values.extend(np.minimum(semantic(v),0)*2)
 values.extend(x[3:6]*.15)
 values.extend((x[6:14]-np.tile([48,38],4))*.09)
 values.extend([(x[14]-116)*.10,(x[15]-30)*.10,x[16]*.20,(x[17]-65)*.10,(x[18]-.6)*3])
 return np.array(values)

x=np.r_[np.zeros(6),np.tile([48.,38.],4),116.,30.,0.,65.,.6]
bounds=[(-50,50),(-65,65),(-30,25)]+[(-35,35)]*3+[(25,85),(18,65)]*4+[(105,145),(24,40),(-12,12),(60,78),(.45,.65)]
fit=least_squares(residual,x,bounds=np.array(bounds).T,x_scale='jac',max_nfev=260,ftol=1e-6,xtol=1e-7,gtol=1e-5)
print('SVD_GROUP_GRASP_APPROX',float(np.dot(fit.fun,fit.fun)),float(shell.clearance(posed(fit.x)[3]).min()),flush=True)
def constraints(x):
 v=posed(x)[3]
 return np.r_[shell.clearance(np.concatenate([v,v[edges].mean(1),v[faces].mean(1)]))+.65,semantic(v)]
fit=minimize(lambda x:float(np.dot(residual(x),residual(x))),fit.x,method='SLSQP',bounds=bounds,
 constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':120,'ftol':.01})
H,Q,p,v=posed(fit.x)
def quat(m):
 q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
opened={}
for n,q in Q.items():
 opened[n]=R.from_rotvec(R.from_matrix(q).as_rotvec()*(.72 if n.startswith('thumb') else .55)).as_matrix()
open_x=fit.x.copy();open_x[17]*=.50
open_q=posed(open_x)[1]
for n in thumb:opened[n]=open_q[n]
out={'hand_in_mag':H.tolist(),'finger_basis':{n:quat(q) for n,q in Q.items()},'open_basis':{n:quat(q) for n,q in opened.items()},
 'parameters':fit.x.tolist(),'optimizer_success':bool(fit.success),'optimizer_message':str(fit.message),
 'minimum_clearance_mm':float(shell.clearance(v).min()),'pad_regions':{n:ids.tolist() for n,ids in pads.items()},'palm_region':palm.tolist(),
 'pad_means_mm':{n:float(shell.clearance(v[ids]).mean()) for n,ids in pads.items()},'palm_mean_mm':float(shell.clearance(v[palm]).mean()),
 'donor':str(S/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json'),
 'thumb_reference':str(S/'RifleMagazineGrip20260922/ThumbOppositionV2/author_thumb.py'),
 'method':'Rest-aware grouped finger flexion, fixed metacarpals, no four-finger axial twist; semantic rear-side CMC frame with cumulative MCP/IP flexion and independent release; actual glove surface fit',
 'game_tested':False}
(O/'grasp_candidate.json').write_text(json.dumps(out,indent=2))
print('SVD_GROUP_GRASP_RESULT',{k:out[k] for k in ['optimizer_success','optimizer_message','pad_means_mm','palm_mean_mm']},flush=True)
