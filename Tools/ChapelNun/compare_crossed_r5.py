"""Requested saved-animation hand/cuff review; sample the whole idle loop."""
import json,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/IdleCrossedR5/Review'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rig=read(R.parent/'authored.json');rig['asset']='Authored Crossed R5';names=rig['names'];ix={n:i for i,n in enumerate(names)}
def fk(frame):
 w=[Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:])) for v in frame]
 for i,p in enumerate(rig['parents']):
  if p>=0:w[i]=w[p]@w[i]
 return np.asarray([list(m) for m in w])
class Surface:
 def __init__(self,path):
  self.d=read(path);self.p=np.asarray(self.d['positions']);self.t=np.asarray(self.d['triangles']);self.m=np.asarray(self.d['triangle_materials']);groups={};self.dominant=[]
  for i,weights in enumerate(self.d['weights']):
   self.dominant.append(self.d['bones'][max(weights,key=lambda p:p[1])[0]]['name'])
   for bone,weight in weights:groups.setdefault(bone,[]).append((i,weight))
  self.groups=[]
  for j,rows in groups.items():
   b=self.d['bones'][j];m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];a=np.asarray(rows)
   self.groups.append((ix[b['name']],np.linalg.inv(m),a[:,0].astype(int),a[:,1,None]))
 def skin(self,w):
  out=np.zeros_like(self.p)
  for i,inv,ids,weights in self.groups:
   m=w[i]@inv;out[ids]+=(self.p[ids]@m[:3,:3].T+m[:3,3])*weights
  return out
def unit(v):return v/max(np.linalg.norm(v),1e-10)
def angle(a,b):return float(np.degrees(np.arccos(np.clip(np.dot(unit(a),unit(b)),-1,1))))
def edges(triangles):
 return np.unique(np.sort(np.concatenate((triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]])),axis=1),axis=0)
def intersections(points,edge_list,tree):
 hits=[]
 for a,b in edge_list:
  delta=points[b]-points[a];length=float(np.linalg.norm(delta))
  if length<.002:continue
  pos,normal,face,dist=tree.ray_cast(Vector(points[a]),Vector(delta/length),length)
  if pos is not None and .001<dist<length-.001:hits.append([int(a),int(b),float(dist)])
 return hits
body=Surface(P/'SourceAssets/ChapelNun20261115/IdleCrossedR4/Review/InputsAfter/body.json');robe=Surface(P/'SourceAssets/ChapelNun20261115/IdleCrossedR4/Review/InputsAfter/robe.json')
visible=robe.t[~np.isin(robe.m,[9])]
torso_tris=robe.t[np.isin(robe.m,[0,4,7])]
sleeve_tris=robe.t[np.isin(robe.m,[1,2])]
sleeve_side={s:np.array([n.endswith('_'+s) for n in robe.dominant]) for s in ('l','r')}
hand_ids={s:np.asarray([i for i,n in enumerate(body.dominant) if n.endswith('_'+s) and n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))]) for s in ('l','r')}

comparison={}
for rev in ('R4','R5'):
 rig=read(P/f'SourceAssets/ChapelNun20261115/IdleCrossed{rev}/authored.json');w=fk(rig['frames'][0]);bp=body.skin(w)
 comparison[rev]={}
 for side in ('l','r'):
  ids=hand_ids[side]
  comparison[rev][side]={'hand_frontmost_y':float(bp[ids,1].max()),'hand_mean_y':float(bp[ids,1].mean()),'finger_tip_y':{d:w[ix[d+'_03_'+side],:3,3].tolist() for d in ('index','middle','ring','pinky')}}
(R.parent/'pose_comparison.json').write_text(json.dumps(comparison,indent=2))
print(comparison,flush=True)
