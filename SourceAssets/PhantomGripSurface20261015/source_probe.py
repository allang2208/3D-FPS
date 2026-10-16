import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
entry=O/'diagnose.py';exec(compile(entry.read_text(encoding='utf-8').split("for key in ['M4'")[0],str(entry),'exec'))
ob,scene=setup('M4');me=ob.data
for f in me.polygons:f.use_smooth=True
for e in me.edges:e.use_edge_sharp=False
bpy.context.view_layer.objects.active=ob
if me.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
scene.cycles.samples=24
scene.render.filepath=str(V/'M4_all_smooth.png');bpy.ops.render.render(write_still=True)
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(O.parent/'PhantomRearGripMultiview_20260913/seed_91627/textured_master_00001_.glb'))
high=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
high.data.transform(high.matrix_world);high.parent=None;high.matrix_world=Matrix.Identity(4)
high.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'))
fit=json.loads((O.parent/'PhantomRearGripIntegration20260913/authoring.json').read_text())['fits']['M4']['root_space_metres']
high.data.transform(Matrix(fit))
for v in high.data.vertices:
 t=max(0,min(1,(v.co.z+.045)/.030));t=t*t*(3-2*t)
 v.co.y-=.011*t;v.co.z+=.012*t
 if v.co.z>.020:v.co.z+=.0045*max(0,min(1,(v.co.y-.008)/.014))
for f in high.data.polygons:f.use_smooth=True
high.data.materials.clear();high.data.materials.append(ob.data.materials[0]);high.hide_render=True
bpy.context.view_layer.objects.active=ob
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
mod=ob.modifiers.new('Restore high source surface normals','DATA_TRANSFER');mod.object=high;mod.use_loop_data=True;mod.data_types_loops={'CUSTOM_NORMAL'};mod.loop_mapping='POLYINTERP_NEAREST'
bpy.ops.object.modifier_apply(modifier=mod.name)
scene.render.filepath=str(V/'M4_high_normal_transfer.png');bpy.ops.render.render(write_still=True)
ob.hide_render=True;high.hide_render=False
scene.render.filepath=str(V/'M4_dense_source.png');bpy.ops.render.render(write_still=True)
high.hide_render=True;ob.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_HighNormalProbe.blend'))
print('HIGH_NORMAL_TRANSFER_COMPLETE',len(high.data.polygons),flush=True)
