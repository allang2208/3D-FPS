"""Rigidly seat restored grips and replace only their mounting necks."""
import bpy,bmesh,json,gzip,math,heapq,ast,os,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;(O/'Exports').mkdir(exist_ok=True)
originals=json.loads((O/'originals.json').read_text());mount=json.load(gzip.open(O/'mount.json.gz','rt'));factory=np.array(list(mount['vertices'].values()));previous=json.loads((O/'model.json').read_text()) if (O/'model.json').exists() else {};report=previous.get('operations',{});out=previous.get('meshes',{})
# Extract just the existing boundary-preserving loft operation. The rejected
# whole-grip voxel/decimate operations are never invoked.
tree=ast.parse((O.parent/'GripJunction44/model.py').read_text());neck_ast=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='neck')
neck_code=ast.unparse(neck_ast).replace('dist=5e-06','dist=1.5e-08')
start=neck_code.index('    if not adj or any(');end=neck_code.index('    loops.sort(',start)
neck_code=neck_code[:start]+'''    if not adj or any(len(ns)%2 for ns in adj.values()):
        raise RuntimeError('Open original neck edge '+key)
    loops=planar_loops(adj)
'''+neck_code[end:]
exec(compile(neck_code,'boundary_neck','exec'))
def planar_loops(adj):
 # The phantom source has touching micro-islands at its head. A boundary
 # vertex can legitimately join four edges; trace bounded planar faces
 # instead of wrongly treating every such junction as a missing surface.
 order={v:sorted(ns,key=lambda w:math.atan2(w.co.y-v.co.y,w.co.x-v.co.x)) for v,ns in adj.items()}
 seen=set();loops=[]
 for start,neighbors in order.items():
  for second in neighbors:
   if (start,second) in seen:continue
   a,b=start,second;loop=[]
   while (a,b) not in seen:
    seen.add((a,b));loop.append(a);n=order[b];c=n[(n.index(a)-1)%len(n)];a,b=b,c
   if (a,b)!=(start,second) or len(loop)<3:continue
   area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(loop,loop[1:]+loop[:1]))*.5
   if area>1e-14 and len(set(loop))==len(loop):loops.append((area,loop))
 if not loops:raise RuntimeError('No closed receiver neck contour')
 return loops
top=factory[factory[:,2]>factory[:,2].max()-.000001,:2]
from mathutils.geometry import convex_hull_2d
points=[Vector(p) for p in top];outline=np.array([top[i] for i in convex_hull_2d(points)]);tc=(outline.min(0)+outline.max(0))*.5
def top_xy(theta):
 direction=np.array([math.cos(theta),math.sin(theta)]);hits=[]
 for a,b in zip(outline,np.roll(outline,-1,axis=0)):
  edge=b-a;den=direction[0]*edge[1]-direction[1]*edge[0]
  if abs(den)<1e-12:continue
  d=a-tc;t=(d[0]*edge[1]-d[1]*edge[0])/den;s=(d[0]*direction[1]-d[1]*direction[0])/den
  if t>0 and -.000001<=s<=1.000001:hits.append(t)
 if not hits:raise RuntimeError('Mount contour missing ray')
 return tc+direction*min(hits)
def center(v,z,band=.002):
 vv=v[abs(v[:,2]-z)<band]
 if len(vv)<5:raise RuntimeError('Missing grip contact slice')
 return (np.quantile(vv,.03,axis=0)+np.quantile(vv,.97,axis=0))*.5
for key,row in originals.items():
 if os.environ.get('R58_ONLY') and key!=os.environ['R58_ONLY']:continue
 bpy.ops.wm.open_mainfile(filepath=row['restored_blend'],use_scripts=False);bpy.context.preferences.filepaths.save_version=0
 ob=bpy.data.objects['Original_'+key];me=ob.data;v=np.array([v.co[:] for v in me.vertices]);hi=v[:,2].max()
 zs=np.array([-.030,-.055,-.080]);src=np.array([center(v,hi-d) for d in [.025,.050,.075]]);dst=np.array([center(factory,z,.003) for z in zs])
 # Only rigid rotation/translation. Original dimensions, texture coordinates,
 # recesses and finger-contact details survive exactly below the neck cut.
 aa=src[:,1:];bb=dst[:,1:];ac=aa.mean(0);bc=bb.mean(0);U,sv,V=np.linalg.svd((aa-ac).T@(bb-bc));rr=V.T@U.T
 if np.linalg.det(rr)<0:V[-1]*=-1;rr=V.T@U.T
 rot=Matrix.Identity(4)
 for i in range(2):
  for j in range(2):rot[i+1][j+1]=float(rr[i,j])
 trans=Vector((float(dst[:,0].mean()-src[:,0].mean()),*map(float,bc-rr@ac)));xf=Matrix.Translation(trans)@rot
 ns=[(xf.to_3x3()@n.vector).normalized() for n in me.corner_normals];me.transform(xf);me.normals_split_custom_set(ns)
 while len(me.uv_layers)<4:me.uv_layers.new(name='R58_Coating'+str(len(me.uv_layers)))
 for poly in me.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(poly.normal[i]))]
  for li in poly.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co
   for j in range(1,4):me.uv_layers[j].data[li].uv=(p[axes[0]]/(.12 if j==1 else .05),p[axes[1]]/(.025 if j==1 else .05))
  poly.material_index=1
 original_material=me.materials[0];me.materials.clear();me.materials.append(bpy.data.materials.new('LMG20122_Interface'));me.materials.append(original_material);original_material.name='LMG20122_'+row['variant']+'_1'
 for poly in me.polygons:poly.material_index=1
 cut=-.020
 if key=='phantom':
  # Choose a solid section of the original upper neck. All retries operate
  # on copies of the same source; no accumulated deformation is possible.
  original_mesh=me.copy();failure=None
  for candidate_cut in [-.022,-.026,-.014]:
   prior_mesh=ob.data;ob.data=original_mesh.copy();me=ob.data
   if prior_mesh!=original_mesh:bpy.data.meshes.remove(prior_mesh)
   try:neck(ob,key,candidate_cut,1);cut=candidate_cut;failure=None;break
   except (RuntimeError,ValueError) as error:failure=error;print('R58_NECK_SECTION',key,candidate_cut,str(error),flush=True)
  if failure:raise failure
  bpy.data.meshes.remove(original_mesh)
 else:neck(ob,key,cut,1)
 # Keep source UV at the shared edge; fade into neck projection only over
 # the newly authored faces, as the installed material fades source relief.
 fresh=me.attributes['J44NewFace'];mask=me.uv_layers[4];donors={}
 for p in me.polygons:
  if not fresh.data[p.index].value:
   for li in p.loop_indices:donors.setdefault(me.loops[li].vertex_index,li)
 for p in me.polygons:
  if not fresh.data[p.index].value:continue
  for li in p.loop_indices:
   vi=me.loops[li].vertex_index
   if vi in donors and mask.data[li].uv.x<1e-6:me.uv_layers[0].data[li].uv=me.uv_layers[0].data[donors[vi]].uv
 ob.name='SM_LMG201_'+row['variant'];bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 for q in bpy.data.objects:
  if q!=ob:q.hide_set(True)
 path=O/'Exports'/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 bpy.ops.file.pack_all();blend=O/(ob.name+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));me.calc_loop_triangles()
 report[key].update(source=row['source'],source_triangles=row['faces'],triangles=len(me.loop_triangles),rigid_fit=[list(r) for r in xf],body_scaled=False,voxel_remeshed=False,decimated=False,mount_contour_source=mount.get('source'),mount_top_xy=outline.tolist(),source_lower_uv_and_normals_preserved=True)
 out[key]={'fbx':str(path),'blend':str(blend),'variant':row['variant']}
 (O/'model.json').write_text(json.dumps({'meshes':out,'operations':report},indent=2));print('R58_GRIP_EXPORTED',key,len(me.loop_triangles),flush=True)
