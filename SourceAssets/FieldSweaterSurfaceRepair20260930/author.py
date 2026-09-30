"""Native body fit and native-topology traversal sleeves, background Blender."""
import copy,sys,math,runpy
from collections import defaultdict
from pathlib import Path
import bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write
helpers=runpy.run_path(str(P/'SourceAssets/CharcoalGarmentRepair20260930/author.py'))
bary,weights,recalc,normals=[helpers[k] for k in ['bary','weights','recalc','normals']]

def body():
 d=read(P/'SourceAssets/FieldSweaterKnit20260929/Authored/Body.json');skin=read(R/'Before/Body/skin.json')
 p=np.array(d['positions']);original=p.copy();f=np.array(d['triangles']);n=normals(p,f)
 sp=np.array(skin['positions']);sf=np.array(skin['triangles']);sn=normals(sp,sf)
 tree=BVHTree.FromPolygons([Vector(v) for v in sp],sf.tolist(),all_triangles=True)
 kd=KDTree(len(p))
 for i,v in enumerate(p):kd.insert(Vector(v),i)
 kd.balance();parent=list(range(len(p)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,v in enumerate(p):
  choices=sorted(kd.find_range(Vector(v),.30),key=lambda x:x[2])
  for _,j,dist in choices:
   if i!=j and (dist<.00001 or n[i]@n[j]<-.75):parent[root(i)]=root(j);break
 groups=defaultdict(list)
 for i in range(len(p)):groups[root(i)].append(i)
 groups=list(groups.values())
 edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
 count=np.zeros(len(p));np.add.at(count,edges[:,0],1);np.add.at(count,edges[:,1],1)
 def smooth(v):
  result=np.zeros_like(v);np.add.at(result,edges[:,0],v[edges[:,1]]);np.add.at(result,edges[:,1],v[edges[:,0]])
  return result/np.maximum(count[:,None],1)
 for iteration in range(8):
  delta=np.zeros_like(p)
  for i,v in enumerate(p):
   hit,_,fi,_=tree.find_nearest(Vector(v));normal=(sn[sf[fi]]*bary(hit,sp[sf[fi]])[:,None]).sum(0);normal/=max(np.linalg.norm(normal),1e-9)
   signed=float((v-hit)@normal)
   if signed<.65:delta[i]=normal*min(1.,.65-signed)
  for group in groups:delta[group]=delta[group[np.argmax(np.linalg.norm(delta[group],axis=1))]]
  delta=delta*.8+smooth(delta)*.2
  for group in groups:delta[group]=delta[group].mean(0)
  p+=delta
 names=sorted(skin['rest']);ni={n:i for i,n in enumerate(names)};w=np.zeros((len(p),len(names)))
 for group in groups:
  hit,_,fi,_=tree.find_nearest(Vector(p[group].mean(0)));field=weights(skin,sf[fi],bary(hit,sp[sf[fi]]))
  for name,value in field.items():w[group,ni[name]]=value
 # The same continuous field across seams and thickness, including the large
 # shoulder/torso transitions that stretched the original body shirt.
 for _ in range(6):
  w=w*.7+smooth(w)*.3
  for group in groups:w[group]=w[group].mean(0)
 for row in w:row[np.argsort(row)[:-8]]=0;row/=row.sum()
 d['positions']=p.tolist();d['weights']=[{names[j]:float(v) for j,v in enumerate(row) if v>1e-7} for row in w]
 d['binding_source']=skin['source'];d['contract']='Full long-knit Body; native body clearance and shared shell weights; continuous shoulder deformation; garment-specific neck, hem and wrist skin coverage'
 recalc(d);write(R/'Authored/Body.json',d)
 write(R/'body-authoring.json',dict(vertices=len(p),triangles=len(f),max_fit_cm=float(np.linalg.norm(p-original,axis=1).max()),shared_shell_groups=len(groups)))
 print('FIELD_BODY_AUTHORED',len(f),flush=True)

def traversal():
 skin=read(R/'Before/Traversal/skin.json');template=read(P/'SourceAssets/FieldSweaterCameraRepair20260930/Authored/Traversal.json')
 names=sorted(skin['rest']);sp=np.array(skin['positions']);faces=[f for f,m in zip(skin['triangles'],skin['materials']) if m in [0,1,3]]
 used=sorted({i for f in faces for i in f});bm=bmesh.new();deform=bm.verts.layers.deform.verify();vs={i:bm.verts.new(sp[i]) for i in used}
 for i,v in vs.items():
  for name,value in skin['weights'][i].items():v[deform][names.index(name)]=value
 for f in faces:bm.faces.new([vs[i] for i in f])
 # Join native material seams, then cut one smooth shoulder plane per arm.
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
 for side in ['l','r']:
  a=Vector(skin['rest']['upperarm_'+side]['p']);b=Vector(skin['rest']['lowerarm_'+side]['p']);axis=(b-a).normalized();sign=1 if a.x>0 else -1
  selected={v for v in bm.verts if v.co.x*sign>0}
  geom=list(selected)+[e for e in bm.edges if all(v in selected for v in e.verts)]+[f for f in bm.faces if all(v in selected for v in f.verts)]
  bmesh.ops.bisect_plane(bm,geom=geom,dist=.00001,plane_co=a+axis,plane_no=axis,clear_inner=True,clear_outer=False)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update();bm.normal_update()
 p=np.array([list(v.co) for v in bm.verts]);f=np.array([[v.index for v in face.verts] for face in bm.faces]);ws=[{names[i]:v for i,v in vertex[deform].items()} for vertex in bm.verts]
 # Native UE winding has inward cross-product normals in this coordinate system.
 n=normals(p,f);boundary=[(e.link_loops[0].vert.index,e.link_loops[0].link_loop_next.vert.index) for e in bm.edges if e.is_boundary]
 bm.free();d=dict(template);d.update(positions=[],weights=ws+copy.deepcopy(ws),triangles=[],uv=[],normals=[],triangle_materials=[])
 clearance=np.full(len(p),.55);thickness=.20
 for i,v in enumerate(p):
  side='l' if v[0]<0 else 'r';w=np.array(skin['rest']['hand_'+side]['p']);e=np.array(skin['rest']['lowerarm_'+side]['p']);axis=(w-e)/np.linalg.norm(w-e)
  t=float((v-w)@axis);blend=np.clip((-t)/6,0,1);clearance[i]=.24+.31*blend
 for offset in [clearance,clearance-thickness]:d['positions'].extend((p+n*offset[:,None]).tolist())
 def coords(ids):
  row=[]
  for i in ids:
   v=p[i];side='l' if v[0]<0 else 'r';a=np.array(skin['rest']['upperarm_'+side]['p']);e=np.array(skin['rest']['lowerarm_'+side]['p']);w=np.array(skin['rest']['hand_'+side]['p'])
   u=(e-a)/np.linalg.norm(e-a);l=(w-e)/np.linalg.norm(w-e);upper=float((v-a)@u);lower=float((v-e)@l)
   axis=l if lower>0 else u;center=e if lower>0 else a;seed=np.array([0.,1.,0.]);seed-=axis*(seed@axis);seed/=np.linalg.norm(seed);cross=np.cross(axis,seed)
   q=v-center;row.append([math.atan2(q@cross,q@seed)/(2*math.pi), (np.linalg.norm(e-a)+lower if lower>0 else upper)/25])
  if max(v[0] for v in row)-min(v[0] for v in row)>.5:
   for v in row:
    if v[0]<0:v[0]+=1
  return [[u*1.5,v] for u,v in row]
 count=len(p)
 for face in f.tolist():
  uv=coords(face);side='l' if p[face,0].mean()<0 else 'r';w=np.array(skin['rest']['hand_'+side]['p']);e=np.array(skin['rest']['lowerarm_'+side]['p']);axis=(w-e)/np.linalg.norm(w-e)
  cuff=float((p[face].mean(0)-w)@axis)>-7
  d['triangles'].append(face);d['uv'].append(uv);d['triangle_materials'].append(1 if cuff else 0)
  d['triangles'].append([i+count for i in face[::-1]]);d['uv'].append(uv[::-1]);d['triangle_materials'].append(2)
 for a,b in boundary:
  ids=[b,a,a+count,b+count];uv=[[0,0],[.02,0],[.02,.008],[0,.008]]
  for ix in [[0,1,2],[0,2,3]]:d['triangles'].append([ids[k] for k in ix]);d['uv'].append([uv[k] for k in ix]);d['triangle_materials'].append(1)
 d['binding_source']=skin['source'];d['contract']='Traversal long knit rebuilt from actual V7 arm surface and elbow topology; exact paired native weights; clean planar shoulder opening; retained hand boundary, continuous inner/outer thickness and ribbed wrist region'
 recalc(d);write(R/'Authored/Traversal.json',d)
 write(R/'traversal-authoring.json',dict(triangles=len(d['triangles']),native_surface_vertices=count,paired_weights=True,thickness_cm=thickness,shoulder_trim_cm=1.0))
 print('FIELD_TRAVERSAL_AUTHORED',len(d['triangles']),flush=True)

if __name__=='__main__':body();traversal()
