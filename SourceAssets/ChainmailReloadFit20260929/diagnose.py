"""Per-clip offline LOD0 stretch comparison at 10 Hz, including endpoints."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChainmailReloadFit20260929')
def read(p):return json.loads(p.read_text())
def matrix(t):
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
def prepare(d):
 p=np.array(d['positions']);groups={}
 for i,w in enumerate(d['weights']):
  for n,v in w.items():groups.setdefault(n,[]).append((i,v))
 out=[]
 for n,rows in groups.items():
  a=np.array(rows);ids=a[:,0].astype(int);out.append((n,ids,a[:,1,None],np.linalg.inv(matrix(d['rest'][n]))))
 return p,out
def posed(data,mat):
 p,groups=data;out=np.zeros_like(p)
 for n,ids,w,inv in groups:
  m=mat[n]@inv;out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w
 return out
report=read(R/'diagnosis.json') if (R/'diagnosis.json').exists() else {}
for rig,source in read(R/'sources.json').items():
 if len(sys.argv)>1 and rig not in sys.argv[1:]:continue
 before=read(R/(rig+'_shirt.json'));installed=R/(rig+'_saved.json');after=read(installed if installed.exists() else R/(rig+'_fitted.json'));a=prepare(before);b=prepare(after)
 p=a[0];faces=np.array(before['triangles']);faces=faces[np.array(before['materials'])==0]
 edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
 length=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);valid=length>.1;edges=edges[valid];length=length[valid]
 after_length=np.maximum(np.linalg.norm(b[0][edges[:,0]]-b[0][edges[:,1]],axis=1),1e-8)
 rows={}
 for pose in read(R/(rig+'_poses.json')):
  mat={n:matrix(t) for n,t in pose['bones'].items()};row=rows.setdefault(pose['clip'],dict(samples=0,before_max=0,after_max=0,before_p99=0,after_p99=0))
  row['samples']+=1
  for name,data in [('before',a),('after',b)]:
   pp=posed(data,mat);ratio=np.linalg.norm(pp[edges[:,0]]-pp[edges[:,1]],axis=1)/(length if name=='before' else after_length)
   worst=float(ratio.max());row[name+'_p99']=max(row[name+'_p99'],float(np.percentile(ratio,99)))
   if worst>row[name+'_max']:row[name+'_max']=worst;row[name+'_worst_time']=pose['time']
 report[rig]=rows
 (R/'diagnosis.json').write_text(json.dumps(report,indent=2));print('CHAINMAIL_DIAG',rig,len(rows),max(r['before_max'] for r in rows.values()),max(r['after_max'] for r in rows.values()),flush=True)
