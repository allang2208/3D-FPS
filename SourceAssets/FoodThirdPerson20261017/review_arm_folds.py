"""Inspect folds inside each actual arm surface, rather than only arm-to-torso clearance."""
import json,numpy as np
from scipy.spatial.transform import Rotation as Q
from pathlib import Path
O=Path(__file__).parent;d=json.loads((O/'graph_source.json').read_text());g=json.loads((O/'body_geometry.json').read_text());ix={n:i for i,n in enumerate(d['names'])};ps=d['parents']
def matrices(f):
 a=np.zeros((len(f),4,4));a[:,3,3]=1;a[:,:3,:3]=Q.from_quat(f[:,3:7]).as_matrix()*f[:,None,7:];a[:,:3,3]=f[:,:3];return a
rest=matrices(np.array(d['reference']))
for i,p in enumerate(ps):
 if p>=0:rest[i]=rest[p]@rest[i]
inv=np.linalg.inv(rest);v=np.array(g['positions']);f=np.array(g['triangles']);p=np.column_stack((v,np.ones(len(v))))
w=np.zeros((len(v),len(ix)))
for i,ww in enumerate(g['weights']):
 for n,x in ww.items():w[i,ix[n]]=x
active=np.where(w.max(0)>0)[0];w=w[:,active];wf=w[f].mean(1)
normal=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
def under(i,a):
 while i>=0:
  if i==a:return True
  i=ps[i]
 return False
regions={s:np.array([under(i,ix['upperarm_'+s]) for i in active]) for s in ['l','r']}
report=[]
for sample in d['cases'][0]['samples']:
 if round(sample['time']*60)%6:continue
 m=matrices(np.array(sample['world']))@inv;deformed=np.zeros_like(v);expected=np.zeros_like(normal)
 for j,b in enumerate(active):
  deformed+=(p@m[b].T)[:,:3]*w[:,j,None];expected+=(normal@m[b,:3,:3].T)*wf[:,j,None]
 fn=np.cross(deformed[f[:,1]]-deformed[f[:,0]],deformed[f[:,2]]-deformed[f[:,0]]);dot=(fn*expected).sum(1);fold=dot<-1e-7
 row={'time':sample['time'],'folds':{}}
 for s,mask in regions.items():
  ids=np.where(fold&(wf[:,mask].sum(1)>.7))[0];row['folds'][s]=[int(i) for i in ids]
 report.append(row)
(O/'arm_folds_source.json').write_text(json.dumps(report,indent=2))
for s in regions:
 worst=max(report,key=lambda r:len(r['folds'][s]));print(s,'worst',worst['time'],len(worst['folds'][s]),'triangles',worst['folds'][s])
