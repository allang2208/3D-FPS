"""Complete the existing AKM mouth locally; preserve the accepted outer shell."""
import bpy,bmesh,sys,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;sys.path.insert(0,str(O.parent/'ExtMagPattern20260919'))
from export_tangents import export
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ExtMagContact20260919/AKM_ExtMag_Closed_Editable.blend'))
ob=bpy.data.objects['SM_ExtMag_AKM40_Closed'];mesh=ob.data
bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active;nl=bm.loops.layers.float_vector.new('OriginalNormals')
for f in bm.faces:
 for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=mesh.corner_normals[i].vector
edges=[e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts)>-.11]
vs={v for e in edges for v in e.verts};center=sum((v.co for v in vs),Vector())/len(vs)
# Keep the asymmetric factory feed contour. Inset 1 mm at each side and
# descend 11 mm: the mouth has a rim, interior walls and a recessed follower.
lo=[min(v.co[i] for v in vs) for i in range(2)];hi=[max(v.co[i] for v in vs) for i in range(2)]
inner={};bottom={}
for v in vs:
 p=v.co.copy()
 for i in range(2):p[i]=center[i]+(p[i]-center[i])*(1-.002/(hi[i]-lo[i]))
 inner[v]=bm.verts.new(p);p=p.copy();p.z-=.011;bottom[v]=bm.verts.new(p)
newfaces=[]
for e in edges:
 l=e.link_loops[0];a=l.vert;b=l.link_loop_next.vert
 newfaces.append(bm.faces.new((b,a,inner[a],inner[b])))
 newfaces.append(bm.faces.new((inner[b],inner[a],bottom[a],bottom[b])))
# Order the directed boundary, rather than sorting a concave contour by angle.
nextv={e.link_loops[0].vert:e.link_loops[0].link_loop_next.vert for e in edges}
start=next(iter(nextv));order=[start];v=nextv[start]
while v!=start:order.append(v);v=nextv[v]
f=bm.faces.new([bottom[v] for v in reversed(order)]);newfaces.append(f)
mouth=bpy.data.materials.new('AKM_Magazine_Mouth');mesh.materials.append(mouth)
for f in newfaces:
 f.material_index=1;f.smooth=False;f.normal_update()
 for l in f.loops:
  # Metal-only receiver crop, no unrelated atlas edges or structural normals.
  l[uv].uv=(.055+(l.vert.co.y-lo[1])/(hi[1]-lo[1])*.23,.053+(l.vert.co.x-lo[0])/(hi[0]-lo[0])*.039)
  l[nl]=f.normal
bmesh.ops.triangulate(bm,faces=newfaces)
bm.normal_update();normals=[l[nl].normalized() if l[nl].length>.5 else f.normal.copy() for f in bm.faces for l in f.loops]
bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(normals)
ob.name='SM_ExtMag_AKM40_Mouth';bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
(O/'FBX').mkdir(exist_ok=True);export(mesh,O/'FBX/SM_ExtMag_AKM40_Mouth.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_ExtMag_Mouth_Editable.blend'))
(O/'mouth_authoring.json').write_text(json.dumps({'source':'ExtMagContact20260919/AKM_ExtMag_Closed_Editable.blend','rim_mm':1,'recess_mm':11,'boundary_edges_used':len(edges),'changed':'mouth interior only; original exterior, curve, mount and UV0 preserved'},indent=2))
