"""Shared shell deformation, smooth shoulder skinning, explicit open root rims."""
import json,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/CharcoalGarmentRepair20260930')
sys.path.insert(0,str(R));from author import read,write,normals,bary,save_blend,recalc
def rim(d):
 bm=bmesh.new();uv=bm.loops.layers.uv.verify();deform=bm.verts.layers.deform.verify();names=sorted({n for w in d['weights'] for n in w})
 vs=[bm.verts.new(p) for p in d['positions']]
 for v,w in zip(vs,d['weights']):
  for n,a in w.items():v[deform][names.index(n)]=a
 for f,coords,mat in zip(d['triangles'],d['uv'],d['triangle_materials']):
  face=bm.faces.new([vs[i] for i in f]);face.material_index=mat
  for l,t in zip(face.loops,coords):l[uv].uv=t
 # Only reconnect the exposed root's UV seam duplicates, not shell layers.
 boundary={v for e in bm.edges if e.is_boundary for v in e.verts}
 bmesh.ops.remove_doubles(bm,verts=list(boundary),dist=.00001)
 pending={e for e in bm.edges if e.is_boundary};loops=[]
 while pending:
  e=pending.pop();ring=[e.verts[0],e.verts[1]]
  while ring[-1]!=ring[0]:
   edge=next((q for q in ring[-1].link_edges if q in pending),None)
   if edge is None:raise RuntimeError('Unclosed Traversal root contour')
   pending.remove(edge);ring.append(edge.other_vert(ring[-1]))
  loops.append(ring[:-1])
 if len(loops)!=4:raise RuntimeError('Expected only four root loops')
 added=0
 for sign in [-1,1]:
  a,b=[loop for loop in loops if np.mean([v.co.x for v in loop])*sign>0]
  paired=[min(b,key=lambda q:(q.co-v.co).length_squared) for v in a]
  if len(set(paired))!=len(a):raise RuntimeError('Root inner/outer correspondence')
  # Smooth the outline with one common offset per thickness pair.
  for _ in range(3):
   mid=[(v.co+q.co)*.5 for v,q in zip(a,paired)]
   changes=[(mid[(i-1)%len(a)]+mid[(i+1)%len(a)]-2*mid[i])*.25 for i in range(len(a))]
   for v,q,delta in zip(a,paired,changes):v.co+=delta;q.co+=delta
  for i,v in enumerate(a):
   j=(i+1)%len(a);edge=bm.edges.get((v,a[j]));old=edge.link_loops[0]
   verts=[v,a[j],paired[j],paired[i]]
   if old.vert==v:verts.reverse()
   face=bm.faces.new(verts);face.material_index=1;added+=2
   for l in face.loops:l[uv].uv=(i/len(a),0 if l.vert in a else .2/25)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
 d.update(positions=[list(v.co) for v in bm.verts],weights=[{names[i]:w for i,w in v[deform].items()} for v in bm.verts],triangles=[[v.index for v in f.verts] for f in bm.faces],uv=[[list(l[uv].uv) for l in f.loops] for f in bm.faces],triangle_materials=[f.material_index for f in bm.faces])
 bm.free();recalc(d);return added
def matrix(t):
 m=np.eye(4);m[:3,:3]=np.array(Quaternion((t['q'][3],*t['q'][:3])).to_matrix())@np.diag(t['s']);m[:3,3]=t['p'];return m
def finish(profiles=None):
 report={}
 for profile in (profiles or ['Body','Traversal']):
  d=read(R/'Authored'/(profile+'.json'));added=rim(d) if profile=='Traversal' else 0
  skin=read(R/'Before'/profile/'skin.json');sp=np.array(skin['positions']);sf=np.array(skin['triangles']);rest={n:matrix(t) for n,t in skin['rest'].items()}
  p=np.array(d['positions']);initial=p.copy();f=np.array(d['triangles']);n=normals(p,f);names=sorted(rest);ni={n:i for i,n in enumerate(names)}
  w=np.zeros((len(p),len(names)))
  for i,ws in enumerate(d['weights']):
   for name,value in ws.items():w[i,ni[name]]=value
  kd=KDTree(len(p))
  for i,q in enumerate(p):kd.insert(Vector(q),i)
  kd.balance();parent=list(range(len(p)))
  def root(i):
   while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
   return i
  for i,v in enumerate(p):
   choices=sorted(kd.find_range(Vector(v),.27),key=lambda r:r[2])
   for _,j,dist in choices:
    if i!=j and (dist<.00001 or n[i]@n[j]<-.75):parent[root(i)]=root(j);break
  gg={}
  for i in range(len(p)):gg.setdefault(root(i),[]).append(i)
  groups=list(gg.values())
  edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0);count=np.zeros(len(p))
  np.add.at(count,edges[:,0],1);np.add.at(count,edges[:,1],1)
  def smooth(values):
   out=np.zeros_like(values);np.add.at(out,edges[:,0],values[edges[:,1]]);np.add.at(out,edges[:,1],values[edges[:,0]])
   return out/np.maximum(count[:,None],1)
  mask=(p[:,2]>127)&(np.abs(p[:,0])>8) if profile=='Body' else np.ones(len(p),bool)
  for _ in range(10 if profile=='Body' else 2):
   averaged=smooth(w);w[mask]=w[mask]*.55+averaged[mask]*.45
   for g in groups:w[g]=w[g].mean(0)
  for row in w:
   row[np.argsort(row)[:-8]]=0;row/=row.sum()
  d['weights']=[{names[j]:float(a) for j,a in enumerate(row) if a>1e-7} for row in w]
  # Corresponding source skin is evaluated in the few poses that expose the
  # reported surfaces. Correct surface offsets, never alter animations/bones.
  pose_rows=read(R/'Before'/profile/'poses.json')
  keys=['Idle_0','Rifle_5'] if profile=='Body' else ['Climb_0','Climb_3','Climb_6','Climb_9','Mantle_5','Vault_5']
  frames=[{n:np.eye(4) for n in names}]+[{n:matrix(pose_rows[key]['bones'][n])@np.linalg.inv(rest[n]) for n in names} for key in keys]
  sw=np.zeros((len(sp),len(names)))
  for i,ws in enumerate(skin['weights']):
   for name,value in ws.items():sw[i,ni[name]]=value
  caches=[]
  for frame in frames:
   mats=np.array([frame[n] for n in names]);sk=np.zeros_like(sp)
   for j,m in enumerate(mats):
    ids=np.flatnonzero(sw[:,j]);sk[ids]+=(sp[ids]@m[:3,:3].T+m[:3,3])*sw[ids,j,None]
   linear=np.einsum('vb,bij->vij',w,mats[:,:3,:3]);translation=w@mats[:,:3,3]
   caches.append((BVHTree.FromPolygons([Vector(q) for q in sk],sf.tolist(),all_triangles=True),sk,normals(sk,sf),linear,translation,np.linalg.pinv(linear)))
  for iteration in range(8):
   for bvh,sk,sn,linear,translation,inverse in caches:
    points=np.einsum('vij,vj->vi',linear,p)+translation;delta=np.zeros_like(p)
    for i,v in enumerate(points):
     hit,_,fi,dist=bvh.find_nearest(Vector(v));bc=bary(hit,sk[sf[fi]]);normal=(sn[sf[fi]]*bc[:,None]).sum(0);normal/=max(np.linalg.norm(normal),1e-8);signed=float((v-hit)@normal)
     margin=.35
     if signed<margin:delta[i]=inverse[i]@(normal*min(.8,margin-signed))
    for g in groups:
     if len(g)>1:delta[g]=delta[g[np.argmax(np.linalg.norm(delta[g],axis=1))]]
    # Spread corrections over adjacent cloth vertices to avoid sharp spikes.
    spread=smooth(delta)*.2;delta=delta*.8+spread
    for g in groups:delta[g]=delta[g].mean(0)
    p+=delta
   print('CHARCOAL_FIT',profile,iteration,float(np.linalg.norm(p-initial,axis=1).max()),flush=True)
  d['positions']=p.tolist();recalc(d)
  d['contract']+='; smooth native shoulder weights and common shell motion field; shoulder thickness rim without cap' if profile=='Traversal' else '; smooth shoulder weight transitions with native pose clearance'
  write(R/'Authored'/(profile+'.json'),d);save_blend(d,profile)
  report[profile]=dict(shoulder_rim_triangles=added,motion_fit_poses=['Rest']+keys,max_finish_displacement_cm=float(np.linalg.norm(p-initial,axis=1).max()),runtime_tested=False)
 previous=read(R/'finish-authoring.json') if (R/'finish-authoring.json').exists() else {}
 previous.update(report);write(R/'finish-authoring.json',previous)
if __name__=='__main__':finish(profiles=['Body'] if '--body-only' in sys.argv else None)
