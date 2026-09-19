"""Close only lower-body gaps; retain the accepted silhouette and feed opening."""
import bpy,bmesh,json,sys,itertools
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parent/'ExtMagPattern20260919';sys.path.insert(0,str(P));from export_tangents import export
bpy.ops.wm.open_mainfile(filepath=str(P/'AKM_ExtMag_Editable.blend'));ob=bpy.data.objects['SM_ExtMag_AKM40'];mesh=ob.data
bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active;nl=bm.loops.layers.float_vector.new('PreservedNormal')
for f in bm.faces:
 for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=mesh.corner_normals[i].vector
def stitch_t_junctions():
 count=0
 for _ in range(3):
  edges=[e for e in bm.edges if e.is_boundary and all(v.co.z<-.19 for v in e.verts)]
  vertices=list({v for e in edges for v in e.verts});changed=0
  for e in edges:
   if not e.is_valid or not e.is_boundary:continue
   a,b=e.verts;delta=b.co-a.co;den=delta.length_squared
   if den<1e-12:continue
   splits=[]
   for v in vertices:
    if not v.is_valid or v in e.verts:continue
    t=(v.co-a.co).dot(delta)/den
    if .0001<t<.9999 and (v.co-(a.co+delta*t)).length<.00005:splits.append((t,v))
   current=a;prev=0
   for t,v in sorted(splits,key=lambda p:p[0]):
    if t-prev<.0001 or not v.is_valid:continue
    edge=next((x for x in current.link_edges if x.other_vert(current)==b),None)
    if edge is None:break
    _,new=bmesh.utils.edge_split(edge,current,(t-prev)/(1-prev));bmesh.ops.weld_verts(bm,targetmap={new:v});current=v;prev=t;changed+=1
  count+=changed
  if not changed:break
 return count
stitched=stitch_t_junctions()
boundary=[e for e in bm.edges if e.is_boundary and all(v.co.z<-.19 for v in e.verts)]
source_uv={v:[l[uv].uv.copy() for l in v.link_loops] for e in boundary for v in e.verts}
new=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
remaining_edges={e for e in bm.edges if e.is_boundary and all(v.co.z<-.19 for v in e.verts)}
while remaining_edges:
 e=remaining_edges.pop();component={e};stack=list(e.verts)
 while stack:
  v=stack.pop()
  for edge in v.link_edges:
   if edge in remaining_edges:remaining_edges.remove(edge);component.add(edge);stack.extend(edge.verts)
 new.extend(bmesh.ops.edgenet_fill(bm,edges=list(component),mat_nr=0,use_smooth=True)['faces'])
tri=bmesh.ops.triangulate(bm,faces=new)['faces'];added=set(tri)
for f in added:
 # Preserve actual boundary corner UVs, choosing the coherent island when a
 # seam vertex has multiple UV values. No new image or arbitrary UV strip.
 options=[source_uv.get(l.vert,[Vector((0,0))]) for l in f.loops]
 choices=[]
 for values in options:
  unique={tuple(round(x,6) for x in v):v for v in values};choices.append(list(unique.values()))
 candidate=min(itertools.product(*choices),key=lambda vs:sum((vs[i]-vs[(i+1)%len(vs)]).length_squared for i in range(len(vs))))
 for l,t in zip(f.loops,candidate):l[uv].uv=t;l[nl]=f.normal
 f.smooth=True
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
bm.normal_update();normals=[l[nl].normalized() if l[nl].length>.5 else f.normal.copy() for f in bm.faces for l in f.loops]
remaining=sum(e.is_boundary and all(v.co.z<-.19 for v in e.verts) for e in bm.edges)
gaps=[e for e in bm.edges if e.is_boundary and all(v.co.z<-.19 for v in e.verts)]
print('GAP_EDGES',len(gaps),'STITCHED',stitched,flush=True)
bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(normals)
ob.name='SM_ExtMag_AKM40_Closed';bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
(O/'FBX').mkdir(exist_ok=True);fallback=export(mesh,O/'FBX'/'SM_ExtMag_AKM40_Closed.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'AKM_ExtMag_Closed_Editable.blend'))
(O/'mesh_repair.json').write_text(json.dumps({'source':str(P/'AKM_ExtMag_Editable.blend'),'lower_open_edges_before':len(boundary),'patch_triangles':len(added),'lower_open_edges_after':remaining,'tangent_fallback_corners':fallback,'preserved':'all existing vertices, silhouette, feed opening and original faces'},indent=2))
