"""Seat the three PKM rear grips on the factory receiver interface."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;A=O.parent/'Accessories14';E=O/'Exports';E.mkdir(exist_ok=True)
src=json.loads((O/'source_frames.json').read_text());old=Matrix(json.loads((A/'authoring.json').read_text())['rear_grip_transform']);fit=Matrix(json.loads((O.parent/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
factory=[Vector(p) for ob in src['factory_grip'] for p in ob['vertices_gun']]
zmax=max(p.z for p in factory);zmin=min(p.z for p in factory)
def center(points):return Vector([(min(v[i] for v in points)+max(v[i] for v in points))*.5 for i in range(3)])
top=center([p for p in factory if p.z>zmax-.012]);bottom=center([p for p in factory if p.z<zmin+.018])
top.z=zmax;top.x=0;bottom.x=0
target_axis=(bottom-top).normalized();result={}
bpy.context.preferences.filepaths.save_version=0
for key in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
 bpy.ops.wm.open_mainfile(filepath=str(A/f'SM_PKM_{key}.blend'))
 body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='PKM_GripTang')
 body.data.transform(old.inverted()@body.matrix_world);body.matrix_world=Matrix.Identity(4)
 verts=[v.co.copy() for v in body.data.vertices]
 # Use each collar's own upper face: the phantom collar is shorter than
 # the other two. A shared collar centre would leave it offset by 13 mm.
 collar_ids={i for p in body.data.polygons if p.material_index==1 for i in p.vertices}
 collar_top=max(verts[i].z for i in collar_ids)
 anchor=center([verts[i] for i in collar_ids if verts[i].z>collar_top-.0001]);anchor.z=collar_top
 body_ids={i for p in body.data.polygons if p.material_index==0 for i in p.vertices};points=[verts[i] for i in body_ids];low=min(v.z for v in points)
 source_bottom=center([v for v in points if v.z<low+.014]);source_bottom.x=anchor.x
 axis=(source_bottom-anchor).normalized();rot=axis.rotation_difference(target_axis).to_matrix().to_4x4()
 scale=(bottom-top).length/(source_bottom-anchor).length
 # Match longitudinal fit with a small uniform correction; keep the authored
 # width/profile rather than crushing the mesh to the old grip's bounding box.
 scale=max(.94,min(1.08,scale))
 xf=fit@Matrix.Translation(top)@rot@Matrix.Scale(scale,4)@Matrix.Translation(-anchor)
 body.data.transform(xf)
 # Existing donor collar is part of the imported body. Rebuild only its
 # vertices against PKM's measured receiver footprint; body finish is retained.
 body_used={i for p in body.data.polygons if p.material_index==0 for i in p.vertices}
 # Flatten the topmost donor collar face to the PKM seat. Lower collar edges
 # retain their fitted slope so the joint stays connected to the grip body.
 for i in collar_ids-body_used:
  p=body.data.vertices[i].co;g=fit.inverted()@p
  upper=max(0,min(1,(verts[i].z-.004)/(collar_top-.004)))
  g.z=g.z*(1-upper)+(zmax-.0005)*upper
  g.x=max(-.0165,min(.0165,g.x));g.y=max(top.y-.031,min(top.y+.031,g.y))
  body.data.vertices[i].co=fit@g
 tang=bpy.data.objects['PKM_GripTang'];bpy.data.objects.remove(tang,do_unlink=True)
 mat=bpy.data.materials.get('PKM14_Interface')
 bpy.ops.mesh.primitive_cube_add(size=1,location=fit@Vector((0,top.y,zmax-.002)))
 tang=bpy.context.object;tang.name='PKM_GripTang';tang.dimensions=(.030,.060,.006)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);tang.data.materials.append(mat)
 bevel=tang.modifiers.new('SeatEdge','BEVEL');bevel.width=.0008;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
 normal=tang.modifiers.new('SeatNormals','WEIGHTED_NORMAL');normal.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=normal.name)
 tang.data.transform(tang.matrix_world);tang.matrix_world=Matrix.Identity(4)
 # Preserve UV0/UV1 and update only the physical coating coordinates.
 for ob in [body,tang]:
  while len(ob.data.uv_layers)<3:ob.data.uv_layers.new(name='PKM_CoatingUV' if len(ob.data.uv_layers)==2 else 'SourceUV')
  for face in ob.data.polygons:
   axis_idx=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis_idx]
   for loop in face.loop_indices:
    p=ob.data.vertices[ob.data.loops[loop].vertex_index].co;ob.data.uv_layers[2].data[loop].uv=(p[axes[0]]/.05,p[axes[1]]/.05)
  if ob==tang:
   for a,b in zip(ob.data.uv_layers[0].data,ob.data.uv_layers[2].data):a.uv=b.uv
  ob.data.uv_layers.active_index=0
 bpy.ops.object.select_all(action='DESELECT')
 for ob in [body,tang]:ob.select_set(True)
 bpy.context.view_layer.objects.active=body
 name='SM_PKM_'+key
 bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
 result[key]={'name':name,'mount_gun':list(top),'bottom_gun':list(bottom),'uniform_scale':scale,'donor_to_root':[list(v) for v in xf],'rotation_deg':math.degrees(axis.angle(target_axis))}
 print('PKM15_REARGRIP_EXPORTED',key,flush=True)
(O/'reargrips.json').write_text(json.dumps(result,indent=2))
