"""Replace recessed 201 connectors with one solid, convex, smoothly tapered neck."""
import bpy,bmesh,ast,json,math,heapq,itertools
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,kdtree
from mathutils.geometry import convex_hull_2d
O=Path(__file__).parent;previous=O.parent/'LMG201GripJunction20261007';sources=json.loads((O/'input.json').read_text());report={};outputs={}
factory=np.array(list(json.loads((previous/'Input/factory.json').read_text())['factory']['vertices'].values()));f_top=factory[factory[:,2]>.005999,:2]
outline=f_top[convex_hull_2d([Vector(v) for v in f_top])];tc=(outline.min(0)+outline.max(0))*.5

def contour_ray(poly,center,theta):
 direction=np.array([math.cos(theta),math.sin(theta)]);hits=[]
 for a,b in zip(poly,np.roll(poly,-1,axis=0)):
  edge=b-a;den=direction[0]*edge[1]-direction[1]*edge[0]
  if abs(den)<1e-14:continue
  d=a-center;r=(d[0]*edge[1]-d[1]*edge[0])/den;s=(d[0]*direction[1]-d[1]*direction[0])/den
  if r>0 and -1e-7<=s<=1.0000001:hits.append(r)
 if not hits:raise RuntimeError('No outer connector boundary')
 return center+direction*min(hits)

def top_xy(theta):return contour_ray(outline,tc,theta)

def planar_loops(adj):
 order={v:sorted(ns,key=lambda w:math.atan2(w.co.y-v.co.y,w.co.x-v.co.x)) for v,ns in adj.items()};seen=set();loops=[]
 for start,neighbors in order.items():
  for second in neighbors:
   if (start,second) in seen:continue
   a,b=start,second;loop=[]
   while (a,b) not in seen:
    seen.add((a,b));loop.append(a);n=order[b];c=n[(n.index(a)-1)%len(n)];a,b=b,c
   if (a,b)!=(start,second) or len(loop)<3:continue
   area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(loop,loop[1:]+loop[:1]))*.5
   if area>1e-14 and len(set(loop))==len(loop):loops.append((area,loop))
 if not loops:raise RuntimeError('No continuous grip shoulder')
 return loops

def solid_parameters(positions):
 global lower_hull,lower_center,angles
 xy=positions[:,:2];lower_hull=xy[convex_hull_2d([Vector(v) for v in xy])];lower_center=(lower_hull.min(0)+lower_hull.max(0))*.5
 d=np.linalg.norm(np.roll(xy,-1,axis=0)-xy,axis=1);s=np.r_[0,np.cumsum(d[:-1])]/d.sum()
 # One monotonic ring, independent of any recessed groove in the source cut.
 start=math.atan2(xy[0,1]-lower_center[1],xy[0,0]-lower_center[0]);angles=start+s*2*math.pi
 relative=np.mod(angles-start,2*math.pi);used=set()
 for p in outline:
  a=(math.atan2(p[1]-tc[1],p[0]-tc[0])-start)%(2*math.pi);delta=np.abs(relative-a);delta=np.minimum(delta,2*math.pi-delta)
  index=next(int(i) for i in np.argsort(delta) if int(i) not in used);relative[index]=a;used.add(index)
 angles=start+np.sort(relative)
 return np.array([top_xy(a) for a in angles])

def solid_ring(t,positions,targets):
 # A convex Minkowski interpolation gives a full outer shoulder at every
 # height; source finger relief and notches cannot create an inset in it.
 blend=t*t*(3-2*t)
 cloud=((1-blend)*lower_hull[:,None,:]+blend*outline[None,:,:]).reshape(-1,2)
 poly=cloud[convex_hull_2d([Vector(v) for v in cloud])];center=lower_center*(1-blend)+tc*blend
 xy=np.array([contour_ray(poly,center,a) for a in angles])
 # The tiny first transition shares the exact textured grip boundary. All
 # other new rings are convex, with no waist, recessed panel or cut-out.
 join=min(1.,t/.08);join=join*join*(3-2*join)
 return positions[:,:2]*(1-join)+xy*join

tree=ast.parse((O.parent/'LMG20120260927/GripJunction44/model.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='neck');code=ast.unparse(node).replace('dist=5e-06','dist=1.5e-08')
start=code.index('    if not adj or any(');end=code.index('    loops.sort(',start)
code=code[:start]+"    if not adj or any(len(ns)%2 for ns in adj.values()):\n        raise RuntimeError('Open source shoulder '+key)\n    loops=planar_loops(adj)\n"+code[end:]
code=code.replace('targets = np.array([top_xy(math.atan2(v.co.y - center.y, v.co.x - center.x)) for v in base])','targets = solid_parameters(positions)')
code=code.replace('xy = positions[:, :2] * (1 - smooth) + targets * smooth + slopes * height * t * (1 - t) ** 2','xy = solid_ring(t, positions, targets)')
if 'solid_parameters(positions)' not in code or 'xy = solid_ring' not in code:raise RuntimeError('Neck constructor source changed')
exec(compile(code,'solid_neck_constructor','exec'))

for key,row in sources.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
 bpy.ops.import_scene.fbx(filepath=row['fbx'],use_custom_normals=True)
 ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;oldnorm=[n.vector.copy() for n in me.corner_normals]
 # Author in the same physical WPN_root frame as the measured factory face.
 world=np.array([list(ob.matrix_world@v.co) for v in me.vertices])
 with (previous/'Input'/(key+'.bin')).open('rb') as f:
  h=json.loads(f.readline());expected=np.fromfile(f,'<f4',h['vertices']*3).reshape(-1,3)
 with (previous/'Plans'/(key+'.bin')).open('rb') as f:
  h=json.loads(f.readline());ids=np.fromfile(f,'<i4',h['moved']);expected[ids]=np.fromfile(f,'<f4',len(ids)*3).reshape(-1,3)
 expected=expected*np.array([.01,-.01,.01]);kd=kdtree.KDTree(len(expected))
 for i,p in enumerate(expected):kd.insert(Vector(p),i)
 kd.balance();sample=world[np.linspace(0,len(world)-1,min(320,len(world)),dtype=int)]
 scale=np.linalg.norm(np.ptp(expected,axis=0))/np.linalg.norm(np.ptp(world,axis=0));options=[]
 for perm in itertools.permutations(range(3)):
  for signs in itertools.product((-1,1),repeat=3):
   rot=np.eye(3)[list(perm)]*np.array(signs)[:,None]
   if np.linalg.det(rot)<0:continue
   transformed=(sample@rot.T)*scale
   error=np.mean([kd.find(Vector(p))[2] for p in transformed]);options.append((error,rot))
 error,rot=min(options,key=lambda v:v[0]);xf=Matrix((rot*scale).tolist()).to_4x4()@ob.matrix_world
 normals=[(xf.to_3x3().inverted().transposed()@n).normalized() for n in oldnorm]
 me.transform(xf);ob.matrix_world=Matrix.Identity(4)
 for p in me.polygons:p.use_smooth=True
 me.normals_split_custom_set(normals)
 if error>.0002:raise RuntimeError('Source frame is ambiguous '+key+' '+str(error))
 # UV4 belongs to the old connector, which is completely removed above the
 # new shoulder. Recreate that same channel for the new solid connector.
 while len(me.uv_layers)>4:me.uv_layers.remove(me.uv_layers[-1])
 original=me.copy();last_error=None
 for cut in (-.030,-.028,-.032,-.034,-.036,-.040):
  discarded=ob.data;ob.data=original.copy();me=ob.data;bpy.data.meshes.remove(discarded)
  try:neck(ob,key,cut,1);last_error=None;break
  except RuntimeError as error:last_error=error;print('SOLID_SHOULDER_SECTION',key,cut,str(error),flush=True)
 if last_error:raise last_error
 bpy.data.meshes.remove(original)
 # Resolve source UV at the shared bottom edge without a texture seam.
 fresh=me.attributes['J44NewFace'];mask=me.uv_layers[4];donors={}
 for p in me.polygons:
  if not fresh.data[p.index].value:
   for li in p.loop_indices:donors.setdefault(me.loops[li].vertex_index,li)
 for p in me.polygons:
  if not fresh.data[p.index].value:continue
  for li in p.loop_indices:
   vi=me.loops[li].vertex_index
   if vi in donors and mask.data[li].uv.x<1e-6:me.uv_layers[0].data[li].uv=me.uv_layers[0].data[donors[vi]].uv
 ob.name=row['path'].rsplit('/',1)[1];bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 fbx=O/'Exports'/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 blend=O/(ob.name+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));me.calc_loop_triangles()
 report[key].update(design='Solid continuous convex connector; no recessed waist, grooves or cut-out',body_below_z_m=cut,frame_alignment_m=float(min(options,key=lambda v:v[0])[0]),triangles=len(me.loop_triangles),uv_sets=len(me.uv_layers),whole_grip_scaled=False)
 outputs[key]={'fbx':str(fbx),'blend':str(blend),'path':row['path'],'source_sha256':row['sha256']}
 (O/'model.json').write_text(json.dumps({'meshes':outputs,'operations':report},indent=2));print('SOLID_JUNCTION_AUTHORED',key,flush=True)
