"""Repair charcoal Body and Traversal only; preserve native binds and UVs."""
import json,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/CharcoalGarmentRepair20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from author_charcoal_short_sleeves import tailor
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def tree(points,faces):return BVHTree.FromPolygons([Vector(x) for x in points],faces.tolist(),all_triangles=True)
def normals(p,f):
 n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
 for j in range(3):np.add.at(n,f[:,j],cross)
 return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
def bary(hit,tri):
 a,b,c=tri;v0=b-a;v1=c-a;v2=np.array(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
 if abs(den)<1e-12:return np.array([1.,0,0])
 v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;w=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den
 out=np.maximum([1-v-w,v,w],0);return out/sum(out)
def weights(d,ids,bc):
 w={}
 for i,b in zip(ids,bc):
  for n,value in d['weights'][i].items():w[n]=w.get(n,0)+float(b*value)
 w=dict(sorted(((n,v) for n,v in w.items() if v>1e-6),key=lambda q:-q[1])[:8]);s=sum(w.values());return {n:v/s for n,v in w.items()}
def save_blend(d,name):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
 for n in sorted({n for w in d['weights'] for n in w}):obj.vertex_groups.new(name=n)
 for i,w in enumerate(d['weights']):
  for n,v in w.items():obj.vertex_groups[n].add([i],v,'REPLACE')
 for slot in ['Textile','RolledHem','InnerTextile']:
  mat=bpy.data.materials.new(slot);mat.diffuse_color=(.045,.053,.065,1);mesh.materials.append(mat)
 layer=mesh.uv_layers.new(name='ProductionUV')
 for face,coords,mat in zip(mesh.polygons,d['uv'],d['triangle_materials']):
  face.material_index=mat;face.use_smooth=True
  for li,uv in zip(face.loop_indices,coords):layer.data[li].uv=(uv[0],1-uv[1])
 mesh.normals_split_custom_set([(n[0],-n[1],n[2]) for row in d['normals'] for n in row])
 obj['NativeBindJSON']=str(R/'Authored'/(name+'.json'));obj['Contract']=d['contract']
 bpy.ops.wm.save_as_mainfile(filepath=str(R/(name+'.blend')))
def recalc(d):
 p=np.array(d['positions']);f=np.array(d['triangles']);n=normals(p,f);d['normals']=n[f].tolist()
def body():
 d=tailor(read(P/'SourceAssets/FieldSweaterKnit20260929/Authored/Body.json'))
 skin=read(R/'Before/Body/skin.json');sp=np.array(skin['positions']);sf=np.array(skin['triangles']);sn=normals(sp,sf);bvh=tree(sp,sf)
 p=np.array(d['positions']);f=np.array(d['triangles']);original=p.copy();n=normals(p,f)
 # Paired shell surfaces receive one displacement/weight field. UV seams stay split.
 kd=KDTree(len(p))
 for i,v in enumerate(p):kd.insert(Vector(v),i)
 kd.balance();parent=list(range(len(p)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,v in enumerate(p):
  choices=sorted(kd.find_range(Vector(v),.27),key=lambda r:r[2])
  for _,j,dist in choices:
   if i!=j and (dist<.00001 or n[i]@n[j]<-.75):parent[root(i)]=root(j);break
 groups={}
 for i in range(len(p)):groups.setdefault(root(i),[]).append(i)
 groups=list(groups.values());group_id=np.empty(len(p),dtype=int)
 for i,g in enumerate(groups):group_id[g]=i
 edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
 def shared(delta):
  for g in groups:
   if len(g)>1:delta[g]=delta[g[np.argmax(np.linalg.norm(delta[g],axis=1))]]
  return delta
 # Fit the inner surface outside the real Body skin, not the original donor.
 # Smooth the displacement field, not the garment's folds or silhouette itself.
 for iteration in range(12):
  delta=np.zeros_like(p)
  for i,v in enumerate(p):
   hit,_,fi,dist=bvh.find_nearest(Vector(v));bc=bary(hit,sp[sf[fi]]);normal=(sn[sf[fi]]*bc[:,None]).sum(0);normal/=max(np.linalg.norm(normal),1e-8)
   signed=float((v-hit)@normal);margin=.6 if n[i]@normal>0 else .4
   if signed<margin:delta[i]=normal*(margin-signed)
  shared(delta);p+=delta
  if iteration<10:
   offset=p-original;total=np.zeros_like(p);count=np.zeros(len(p))
   np.add.at(total,edges[:,0],offset[edges[:,1]]);np.add.at(total,edges[:,1],offset[edges[:,0]])
   np.add.at(count,edges[:,0],1);np.add.at(count,edges[:,1],1)
   smooth=(total/np.maximum(count[:,None],1)-offset)*.35
   for g in groups:smooth[g]=smooth[g].mean(0)
   p+=smooth
 # Use the corresponding native body surface for the entire thickness group.
 ws=[None]*len(p)
 for g in groups:
  hit,_,fi,_=bvh.find_nearest(Vector(p[g].mean(0)));w=weights(skin,sf[fi],bary(hit,sp[sf[fi]]))
  for i in g:ws[i]=w
 d['positions']=p.tolist();d['weights']=ws;d['binding_source']=skin['source'];recalc(d)
 d['contract']='Charcoal T-shirt: anatomical-only sleeve cut; intact lower hem; native Body envelope fit and shared inner/outer weights; full skin retained under collar'
 write(R/'Authored/Body.json',d);save_blend(d,'Body')
 write(R/'body-authoring.json',dict(vertices=len(p),triangles=len(f),shell_groups=len(groups),max_fit_displacement_cm=float(np.linalg.norm(p-original,axis=1).max()),world_covers=[]))
 print('BODY_AUTHORED',len(p),len(f),flush=True)
def traversal():
 d=read(P/'SourceAssets/FieldSweaterKnit20260929/ShortSleeve/Traversal.json')
 current=read(R/'Before/Traversal/shirt.json')
 kd=KDTree(len(current['positions']))
 for i,p in enumerate(current['positions']):kd.insert(Vector(p),i)
 kd.balance()
 for i,p in enumerate(d['positions']):
  _,j,dist=kd.find(Vector(p))
  if dist>.001:raise RuntimeError('Traversal source geometry changed')
  d['weights'][i]=current['weights'][j]
 master=read(P/'SourceAssets/GarmentFoundation20260929/ue_chainmail_shirt.json')
 def key(data,f):return tuple(sorted(tuple(round(x,3) for x in data['positions'][v]) for v in f))
 caps={key(master,f) for f in master['triangles'][14392:14600]}
 deleted=[i for i,f in enumerate(d['triangles']) if key(d,f) in caps]
 if len(deleted)!=240:raise RuntimeError('Unexpected Traversal shoulder topology '+str(len(deleted)))
 keep=[i for i in range(len(d['triangles'])) if i not in set(deleted)]
 for field in ['triangles','normals','uv','triangle_materials']:d[field]=[d[field][i] for i in keep]
 used=sorted({v for f in d['triangles'] for v in f});mapping={v:i for i,v in enumerate(used)}
 for field in ['positions','weights']:d[field]=[d[field][i] for i in used]
 d['triangles']=[[mapping[v] for v in f] for f in d['triangles']]
 d['binding_source']=read(R/'Before/Traversal/paths.json')['native']
 d['contract']='Charcoal Traversal sleeves: obsolete shoulder closure patches removed; current fitted V7 native weights and complete inward cuff retained'
 write(R/'Authored/Traversal.json',d);save_blend(d,'Traversal')
 write(R/'traversal-authoring.json',dict(deleted_shoulder_faces=len(deleted),triangles=len(d['triangles'])))
 print('TRAVERSAL_AUTHORED',len(d['triangles']),flush=True)
if __name__=='__main__':body();traversal()
