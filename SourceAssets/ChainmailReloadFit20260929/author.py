"""Conform sleeve skinning to each native arm, keeping authored geometry/layers."""
import json
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChainmailReloadFit20260929')
def read(p):return json.loads(p.read_text())
summary={}
for rig in read(R/'sources.json'):
 shirt=read(R/(rig+'_shirt.json'));skin=read(R/(rig+'_skin.json'));q=np.array(skin['positions']);p=np.array(shirt['positions'])
 if rig in ['ASH12','M16']:
  # These two rifles have posed reference skeletons. Their old sleeve envelope
  # was transported with the bad torso-heavy weights too. Transport the repaired
  # canonical sleeve and its continuous weights together into the native bind.
  master=read(R/'M4_fitted.json')
  def matrix(t):return np.asarray(Matrix.Translation(Vector(t['p']))@Quaternion((t['q'][3],*t['q'][:3])).to_matrix().to_4x4()@Matrix.Diagonal(Vector((*t['s'],1))))
  names={n for w in master['weights'] for n in w};transforms={n:matrix(shirt['rest'][n])@np.linalg.inv(matrix(master['rest'][n])) for n in names}
  edits=[]
  for i,(pos,w) in enumerate(zip(master['positions'],master['weights'])):
   point=sum((transforms[n]@np.r_[pos,1])[:3]*v for n,v in w.items()).tolist()
   shirt['positions'][i]=point;shirt['weights'][i]=w;edits.append(dict(vertex_id=i,position=point,weights=w))
  (R/(rig+'_fitted.json')).write_text(json.dumps(shirt,separators=(',',':')));(R/(rig+'_edits.json')).write_text(json.dumps(edits,separators=(',',':')))
  summary[rig]=dict(vertices=len(p),edited=len(edits),native_bind_transport=True)
  print('CHAINMAIL_AUTHORED',rig,summary[rig],flush=True)
  if rig=='M16':continue
  p=np.array(shirt['positions'])
 # Bone-side influence identifies mirrored dual-pistol arms without assuming X.
 def side(weights):
  score={s:sum(v for n,v in weights.items() if n.endswith('_'+s)) for s in ['l','r']}
  return max(score,key=score.get)
 skin_sides=[side(w) for w in skin['weights']];trees={}
 for s in ['l','r']:
  faces=[f for f,m in zip(skin['triangles'],skin['materials']) if m in [0,1,2,3] and all(skin_sides[i]==s for i in f)]
  if faces:trees[s]=(BVHTree.FromPolygons([Vector(v) for v in q],faces,all_triangles=True),faces)
 edits=[];distances=[];preserved=0;caps=0
 for i,pos in enumerate(p):
  s=side(shirt['weights'][i])
  if s not in trees:raise RuntimeError('Missing arm '+rig+s)
  # ADS34 deliberately corrected 201's right shoulder against its own source.
  # Keep that shoulder correction and its transition, rather than replacing it
  # with the shared PKM bare-arm shoulder used below the shirt.
  if rig=='LMG201' and s=='r':
   elbow=np.array(shirt['rest']['lowerarm_r']['p']);wrist=np.array(shirt['rest']['hand_r']['p']);axis=(wrist-elbow)/np.linalg.norm(wrist-elbow)
   if (pos-elbow)@axis<2:preserved+=1;continue
  tree,faces=trees[s];hit,normal,fi,distance=tree.find_nearest(Vector(pos))
  if fi is None:raise RuntimeError('Unmatched sleeve '+rig+' '+str(i))
  # Open proximal closure extends towards the torso beyond the bare-arm shell.
  # Keep it attached to its authored shoulder, never project it across the body.
  if distance>8:caps+=1;continue
  ids=faces[fi];a,b,c=q[ids];v0=b-a;v1=c-a;v2=np.array(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
  if abs(den)<1e-12:raise RuntimeError('Degenerate arm triangle')
  v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;w=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den;bary=np.maximum([1-v-w,v,w],0);bary/=sum(bary);weights={}
  for vi,mix in zip(ids,bary):
   for n,value in skin['weights'][vi].items():weights[n]=weights.get(n,0)+float(mix*value)
  weights=dict(sorted(((n,v) for n,v in weights.items() if v>1e-6),key=lambda x:-x[1])[:8]);total=sum(weights.values());weights={n:v/total for n,v in weights.items()}
  shirt['weights'][i]=weights;row=dict(vertex_id=i,weights=weights)
  if rig=='ASH12':row['position']=pos.tolist()
  edits.append(row);distances.append(distance)
 (R/(rig+'_fitted.json')).write_text(json.dumps(shirt,separators=(',',':')));(R/(rig+'_edits.json')).write_text(json.dumps(edits,separators=(',',':')))
 summary[rig]=dict(vertices=len(p),edited=len(edits),preserved_ADS34=preserved,preserved_proximal_caps=caps,max_projection_cm=max(distances))
 print('CHAINMAIL_AUTHORED',rig,summary[rig],flush=True)
(R/'authored.json').write_text(json.dumps(summary,indent=2))
