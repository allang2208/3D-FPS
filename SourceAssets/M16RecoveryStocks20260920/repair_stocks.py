"""Replace only M16 stock interfaces, retaining donor face-corner UVs/normals."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
KEYS=['skeleton','qr_performance','core_stock','tactical_telescopic']
bpy.ops.wm.open_mainfile(filepath=str(S/'M16UniversalAttachments20260920/M16_CommonAttachments_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
(O/'Meshes').mkdir(exist_ok=True)
parts=json.loads((O/'factory_geometry.json').read_text())
ref=parts['M16A2_Receiver'];me=bpy.data.meshes.new('ReceiverCutReference');me.from_pydata(ref['vertices'],[],ref['faces'])
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
cut={e for e in bm.edges if e.is_boundary and all(abs(v.co.y-.041045)<.000002 for v in e.verts)}
assert len(cut)==106
start=min({v for e in cut for v in e.verts},key=lambda v:v.co.z);v=start;prev=None;contour=[]
while True:
 contour.append(v.co.copy());neighbours=[e.other_vert(v) for e in v.link_edges if e in cut and e.other_vert(v)!=prev]
 nxt=neighbours[0];prev,v=v,nxt
 if v==start:break
assert len(contour)==106
bm.free()
# Reuse the actual cut polygon. Clockwise as seen from the stock, viewed in XZ.
if sum(contour[i].x*contour[(i+1)%len(contour)].z-contour[(i+1)%len(contour)].x*contour[i].z for i in range(len(contour)))>0:contour.reverse()
report={'receiver_cut_vertices':len(contour),'interface_front_m':.04065,'interface_back_m':.0505,'stocks':{}}

def adapter():
 n=len(contour);verts=[];faces=[];groups=[];cx=-.000038;cz=.0917
 # Original teardrop cut, a thin endplate, and a solid buffer-tube shoulder.
 # Both caps are closed. The rear cap overlaps each donor stem, so there is
 # no annular passage from the camera into the hollow receiver.
 for y,rad in [(.04065,None),(.04225,None),(.04265,None),(.04315,.018),(.0485,.018),(.0505,.0169)]:
  for p in contour:
   if rad is None:
    scale=.995 if y==.04265 else 1.0
    verts.append((cx+(p.x-cx)*scale,y,cz+(p.z-cz)*scale))
   else:
    q=Vector((p.x-cx,0,p.z-cz)).normalized()*rad
    verts.append((cx+q.x,y,cz+q.z))
 for ring in range(5):
  for i in range(n):
   j=(i+1)%n;faces.append((ring*n+i,ring*n+j,(ring+1)*n+j,(ring+1)*n+i));groups.append(ring)
 faces.extend([tuple(reversed(range(n))),tuple(5*n+i for i in range(n))]);groups.extend([-1,-2])
 m=bpy.data.meshes.new('M16_ClosedReceiverAdapter');m.from_pydata(verts,[],faces);m.update()
 b=bmesh.new();b.from_mesh(m);bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(m);b.free();m.update()
 # Split normals along the machined rings, smooth only around circumference.
 normals=[]
 for p,g in zip(m.polygons,groups):
  if g<0:normals.extend([tuple(p.normal)]*len(p.loop_indices));continue
  for vi in p.vertices:
   ns=sum((f.normal for f,fg in zip(m.polygons,groups) if fg==g and vi in f.vertices),Vector()).normalized()
   normals.append(tuple(ns))
 for p in m.polygons:p.use_smooth=True
 m.normals_split_custom_set(normals)
 for index in range(4):
  uv=m.uv_layers.new(name='M16_UV'+str(index))
  for f in m.polygons:
   axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[i for i in range(3) if i!=axis]
   for li in f.loop_indices:
    p=m.vertices[m.loops[li].vertex_index].co;uv.data[li].uv=(p[a]/.04,p[b]/.04)
 return m

ad=adapter()
for key in KEYS:
 o=bpy.data.objects['SM_M16_'+key];src=o.data
 # Rebuild the donor without material 0 (the previous open annular collar).
 # All surviving face corners keep their UV0..3 and imported split normals.
 verts=[tuple(v.co) for v in src.vertices];faces=[];mats=[];smooth=[];normals=[];uvs=[[] for _ in range(4)]
 for f in src.polygons:
  if f.material_index==0:continue
  faces.append(tuple(f.vertices));mats.append(f.material_index);smooth.append(f.use_smooth)
  normals.extend(tuple(src.corner_normals[i].vector) for i in f.loop_indices)
  for j in range(4):uvs[j].extend(tuple(src.uv_layers[j].data[i].uv) for i in f.loop_indices)
 count=len(verts);verts.extend(tuple(v.co) for v in ad.vertices)
 for f in ad.polygons:
  faces.append(tuple(count+i for i in f.vertices));mats.append(0);smooth.append(True)
  normals.extend(tuple(ad.corner_normals[i].vector) for i in f.loop_indices)
  for j in range(4):uvs[j].extend(tuple(ad.uv_layers[j].data[i].uv) for i in f.loop_indices)
 dst=bpy.data.meshes.new(o.name+'_ClosedInterface');dst.from_pydata(verts,[],faces);dst.update()
 for mat in src.materials:dst.materials.append(mat)
 for f,mi,sm in zip(dst.polygons,mats,smooth):f.material_index=mi;f.use_smooth=sm
 for j,coords in enumerate(uvs):
  layer=dst.uv_layers.new(name='M16_UV'+str(j))
  for li,uv in enumerate(coords):layer.data[li].uv=uv
 dst.normals_split_custom_set(normals);o.data=dst
 # These sub-millimetre donor slits are recorded separately; only collapse
 # boundary clusters of the core model, not the preserved broad body surface.
 repairs=[]
 if key=='core_stock':
  b=bmesh.new();b.from_mesh(dst);ln=b.loops.layers.float_vector.new('M16_source_normal')
  li=0
  for f in b.faces:
   for l in f.loops:l[ln]=normals[li];li+=1
  bmesh.ops.remove_doubles(b,verts=list(b.verts),dist=.000002)
  pending={e for e in b.edges if e.is_boundary}
  while pending:
   e=pending.pop();vs=set(e.verts);stack=list(vs)
   while stack:
    v=stack.pop()
    for edge in v.link_edges:
     if edge in pending:pending.remove(edge);vs.update(edge.verts);stack.extend(edge.verts)
   span=max((a.co-c.co).length for a in vs for c in vs)
   assert span<.0004,'Unexpected donor opening outside the diagnosed micro-slits'
   target=min(vs,key=lambda v:v.index);center=sum((v.co for v in vs),Vector())/len(vs)
   repairs.append({'center_m':list(center),'span_m':span,'vertices':len(vs)})
   bmesh.ops.weld_verts(b,targetmap={v:target for v in vs if v!=target})
  # Welding can leave unused edges/vertices; remove only those without faces.
  bmesh.ops.delete(b,geom=[e for e in b.edges if not e.link_faces],context='EDGES')
  bmesh.ops.delete(b,geom=[v for v in b.verts if not v.link_faces],context='VERTS')
  kept_normals=[tuple(l[ln]) for f in b.faces for l in f.loops]
  b.loops.layers.float_vector.remove(ln);b.to_mesh(dst);b.free();dst.update();dst.normals_split_custom_set(kept_normals)
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 file=O/'Meshes'/(o.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
 report['stocks'][key]={'file':str(file),'vertices':len(dst.vertices),'polygons':len(dst.polygons),'slots':[m.name for m in dst.materials],'micro_repairs':repairs}
 o.hide_set(True)
# Keep the editable delivery scoped to the four repaired stock assemblies.
for o in list(bpy.data.objects):
 if o.name not in ['SM_M16_'+k for k in KEYS]:bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M16_ClosedStockInterfaces_Editable.blend'))
(O/'repairs.json').write_text(json.dumps(report,indent=2));print('M16_STOCK_INTERFACES_AUTHORED',json.dumps(report),flush=True)
