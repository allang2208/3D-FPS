"""Requested saved-animation hand/cuff review; sample the whole idle loop."""
import json,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/IdleCrossedR4/Review'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rig=read(R.parent/'authored.json');rig['asset']='Authored Crossed R4';names=rig['names'];ix={n:i for i,n in enumerate(names)}
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
body=Surface(P/'SourceAssets/ChapelNun20261115/IdleRelaxedR3/Review/InputsAfter/body.json');robe=Surface(P/'SourceAssets/ChapelNun20261115/IdleRelaxedR3/Review/InputsAfter/robe.json')
visible=robe.t[~np.isin(robe.m,[9])]
hand_ids={s:np.asarray([i for i,n in enumerate(body.dominant) if n.endswith('_'+s) and n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))]) for s in ('l','r')}
results=[];wrist_samples={s:[] for s in ('l','r')}
for sample in range(0,361,30):
 w=fk(rig['frames'][sample]);bp=body.skin(w);rp=robe.skin(w);cloth=BVHTree.FromPolygons(rp.tolist(),visible.tolist(),all_triangles=True)
 row={'time':sample/30,'sides':{}};hand_triangles={};hand_edges={}
 for side in ('l','r'):
  shoulder,elbow,wrist,mcp=[w[ix[n+'_'+side],:3,3] for n in ('upperarm','lowerarm','hand','middle_01')]
  wrist_samples[side].append(wrist.tolist());forward=unit(mcp-wrist)
  mask=np.zeros(len(bp),bool);mask[hand_ids[side]]=True
  # Skin proximal to the cuff opening is intentionally clothed; inspect exposed
  # palm/finger triangles at least 3 cm distal to the wrist centre separately.
  mask&=((bp-wrist)@forward>3.)
  tris=body.t[mask[body.t].all(axis=1)];ids=np.unique(tris);skin_edges=edges(tris)
  hand_triangles[side]=tris;hand_edges[side]=skin_edges
  hit=intersections(bp,skin_edges,cloth)
  minimum=min(float(cloth.find_nearest(Vector(bp[i]))[3]) for i in ids)
  palm=BVHTree.FromPolygons(bp.tolist(),tris.tolist(),all_triangles=True)
  near=((rp-wrist)@forward>3.)&(np.linalg.norm(rp-wrist,axis=1)<17)
  close_tris=visible[near[visible].any(axis=1)]
  reverse=intersections(rp,edges(close_tris),palm)
  finger_angles={}
  for digit in ('index','middle','ring','pinky'):
   a,b,c=[w[ix[f'{digit}_{j:02d}_{side}'],:3,3] for j in (1,2,3)]
   finger_angles[digit]=angle(b-a,c-b)
  row['sides'][side]=dict(upperarm_from_vertical_deg=angle(elbow-shoulder,[0,0,-1]),elbow_flexion_deg=angle(elbow-shoulder,wrist-elbow),
    wrist_axis_bend_deg=angle(mcp-wrist,wrist-elbow),finger_middle_joint_bend_deg=finger_angles,
    exposed_hand_to_cloth_min_cm=minimum,hand_edge_cloth_crossings=len(hit),cloth_edge_hand_crossings=len(reverse))
 pair_hits={}
 for side,other in [('l','r'),('r','l')]:
  other_tree=BVHTree.FromPolygons(bp.tolist(),hand_triangles[other].tolist(),all_triangles=True)
  pair_hits[side]=len(intersections(bp,hand_edges[side],other_tree))
 row['hand_pair_crossings']=pair_hits
 results.append(row);print('NUN_RELAXED_CONTACT_SAMPLE',sample,{s:(row['sides'][s]['hand_edge_cloth_crossings'],row['sides'][s]['cloth_edge_hand_crossings']) for s in ('l','r')},flush=True)
report=dict(animation=rig['asset'],samples=results,wrist_range_cm={s:np.ptp(v,axis=0).tolist() for s,v in wrist_samples.items()},
 method='Saved compressed animation with native LBS; exact BVH edge/triangle crossings in both directions; exposed hand distal to wrist by 3 cm; 13 evenly spaced poses',
 limitations='Numerical contact uses skinned surfaces, excluding live cloth and material cuff displacement. Engine captures cover actual components and materials separately.')
(R/'author_contact_review.json').write_text(json.dumps(report,indent=2))
print('NUN_RELAXED_CONTACT_REVIEW_SAVED',flush=True)
