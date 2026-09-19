"""Local steel patches for the existing lower-shell holes; no silhouette remesh."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parent/'ExtMagPattern20260919';sys.path.insert(0,str(P));from export_tangents import export
bpy.ops.wm.open_mainfile(filepath=str(P/'AKM_ExtMag_Editable.blend'));ob=bpy.data.objects['SM_ExtMag_AKM40'];mesh=ob.data
bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active;nl=bm.loops.layers.float_vector.new('PreservedNormal')
for f in bm.faces:
 for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=mesh.corner_normals[i].vector
edges={e for e in bm.edges if e.is_boundary and all(v.co.z<-.19 for v in e.verts)};before=len(edges);patches=[]
while edges:
 e=edges.pop();component={e};stack=list(e.verts)
 while stack:
  v=stack.pop()
  for edge in v.link_edges:
   if edge in edges:edges.remove(edge);component.add(edge);stack.extend(edge.verts)
 vertices={v for edge in component for v in edge.verts}
 center=bm.verts.new(sum((v.co for v in vertices),Vector())/len(vertices))
 # Coherent island centres keep a UV seam from interpolating across the atlas.
 refs=[]
 for edge in component:
  l=edge.link_loops[0];refs.append((l,l.link_loop_next,l[uv].uv.copy(),l.link_loop_next[uv].uv.copy()))
 centers=[]
 for a,b,ua,ub in refs:
  midpoint=(ua+ub)*.5;near=[(u+v)*.5 for _,_,u,v in refs if ((u+v)*.5-midpoint).length<.025]
  centers.append(sum(near,Vector((0,0)))/len(near))
 for (a,b,ua,ub),uc in zip(refs,centers):
  f=bm.faces.new((b.vert,a.vert,center));f.smooth=True
  for l,t in zip(f.loops,[ub,ua,uc]):l[uv].uv=t
  f.normal_update()
  for l in f.loops:l[nl]=f.normal
 patches.append(len(refs))
bm.normal_update();normals=[l[nl].normalized() if l[nl].length>.5 else f.normal.copy() for f in bm.faces for l in f.loops]
remaining=sum(e.is_boundary and all(v.co.z<-.19 for v in e.verts) for e in bm.edges)
bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(normals)
ob.name='SM_ExtMag_AKM40_Closed';bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
(O/'FBX').mkdir(exist_ok=True);fallback=export(mesh,O/'FBX'/'SM_ExtMag_AKM40_Closed.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_ExtMag_Closed_Editable.blend'))
(O/'mesh_repair.json').write_text(json.dumps({'source':str(P/'AKM_ExtMag_Editable.blend'),'lower_open_edges_before':before,'patch_groups':len(patches),'patch_triangles':sum(patches),'lower_open_edges_after':remaining,'tangent_fallback_corners':fallback,'preserved':'all existing vertices, silhouette, feed opening and original faces'},indent=2))
