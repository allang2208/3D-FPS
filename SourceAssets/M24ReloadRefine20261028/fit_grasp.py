"""Fit native distal flexion and limited MCP/PIP closure to the real magazine."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'reload_library','exec'))
import bmesh
from mathutils.bvhtree import BVHTree
base=clips['reload'][24];mag=bpy.data.objects['M24_clip'];bm=bmesh.new();bm.from_mesh(mag.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
bvh=BVHTree.FromPolygons([list(v.co) for v in bm.verts],[tuple(v.index for v in f.verts) for f in bm.faces],all_triangles=True);bm.free()
bm=bmesh.new()
for v in mag.data.vertices:bm.verts.new(v.co)
bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.normal_update()
center=sum((v.co for v in bm.verts),Vector())/len(bm.verts);planes=[]
for f in bm.faces:
 n=f.normal.copy()
 if n.dot(f.calc_center_median()-center)<0:n=-n
 planes.append((*n,n.dot(f.verts[0].co)))
planes=np.array(planes);bm.free()
M=rest['WPN_Magazine']@base['WPN_Magazine'].inverted();ids={n:i for i,n in enumerate(names)}
verts=np.array([list(v.co)+[1] for v in skin.data.vertices]);weights=np.zeros((len(verts),len(names)))
for v in skin.data.vertices:
 for g in v.groups:
  n=skin.vertex_groups[g.group].name
  if n in ids:weights[v.index,ids[n]]=g.weight
dominant=weights.argmax(1)
local={n:base[parents[n]].inverted()@base[n] for n in names if parents[n]}
def Q(z):return Quaternion((0,0,1),math.radians(z))
def posed(finger,params):
 row=clone(base)
 for j in (1,2,3):
  n=f'{finger}_{j:02d}_l';v=local[n];q=v.to_quaternion()
  if j==3:q=local_rest[n].to_quaternion()@Q(params[2])
  else:q=local_rest[n].to_quaternion()@Q(params[j-1])@local_rest[n].to_quaternion().inverted()@q
  if j==1:q=local_rest[n].to_quaternion()@Quaternion((0,1,0),math.radians(params[3]))@local_rest[n].to_quaternion().inverted()@q
  row[n]=row[parents[n]]@Matrix.LocRotScale(v.translation,q,v.to_scale())
 return row
result={};final=clone(base)
for finger in ('index','middle','ring','pinky','thumb'):
 chosen=[i for i,n in enumerate(names) if n.startswith(finger+'_') and n.endswith('_l')]
 selected=np.where(np.isin(dominant,chosen))[0][::3]
 W=np.einsum('vk,kij,vj->kvi',weights[selected],np.array([np.array(rest[n].inverted()) for n in names]),verts[selected],optimize=True)
 tipmask=dominant[selected]==ids[finger+'_03_l']
 def score(params,detail=False):
  row=posed(finger,params);P=np.einsum('kij,kvj->vi',np.array([np.array(M@row[n]) for n in names]),W,optimize=True)[:,:3]
  ds=[]
  envelope=np.max(P@planes[:,:3].T-planes[:,3],axis=1)
  for p,inside in zip(P,envelope<0):
   hit,normal,_,d=bvh.find_nearest(Vector(p));ds.append(-d if inside and (Vector(p)-hit).dot(normal)<0 else d)
  ds=np.array(ds);penetration=np.maximum(-ds-.0006,0)*1000;near=np.sort(np.abs(ds[tipmask])*1000)[:6]
  value=float((penetration**2).mean()*25+penetration.max()**2*8+np.mean((near-1.5)**2)*.06+(.12*params[0])**2+(.12*params[1])**2+(.04*(params[2]-(12 if finger=='thumb' else 28)))**2+(.10*params[3])**2)
  return {'score':value,'penetration_mm':float(max(0,-ds.min())*1000),'tip_nearest_mm':float(near.mean())} if detail else value
 p=[0,0,12 if finger=='thumb' else 28,0]
 for step in (8,4,2):
  for axis in range(4):
   candidates=[]
   for offset in (-step,0,step):
    trial=p.copy();trial[axis]+=offset
    if axis<2 and abs(trial[axis])>14:continue
    if axis==2 and not (0<=trial[2]<=24 if finger=='thumb' else 12<=trial[2]<=42):continue
    if axis==3 and abs(trial[3])>12:continue
    candidates.append((score(trial),trial))
   p=min(candidates,key=lambda x:x[0])[1]
 row=posed(finger,p)
 for j in (1,2,3):final[f'{finger}_{j:02d}_l']=row[f'{finger}_{j:02d}_l']
 result[finger]={'adjustments_deg':p,'surface':score(p,True)}
 print('FINGER_FIT',finger,result[finger],flush=True)
(O/'grasp_fit.json').write_text(json.dumps(result,indent=2))
(O/'grasp_pose.json').write_text(json.dumps({n:[list(v) for v in m] for n,m in final.items()}))
setup_render();folder=O/'Fit';folder.mkdir(exist_ok=True)
for view in ('left','right','bottom'):show(final,folder/f'grasp_{view}.png',view)
