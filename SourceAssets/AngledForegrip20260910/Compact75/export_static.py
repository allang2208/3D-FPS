import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Foregrip_Fitted.blend'))
r=bpy.data.objects['SK_M4_Infima'];fit=json.loads((O/'fit_pose.json').read_text());delta=r.matrix_world@r.data.bones['WPN_root'].matrix_local@Matrix(fit['old']['WPN_root']).inverted()@r.matrix_world.inverted()
bpy.ops.object.select_all(action='DESELECT')
parts=[o for o in bpy.context.scene.objects if o.name.startswith('FG_')]
for ob in parts:ob.matrix_world=delta@ob.matrix_world;ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.convert(target='MESH');bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_M4_AngledForegrip'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.export_scene.fbx(filepath=str(O/'SM_M4_AngledForegrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,path_mode='STRIP')
(O/'static_export.json').write_text(json.dumps({'materials':[m.name for m in ob.data.materials],'dimensions_m':list(ob.dimensions),'vertices':len(ob.data.vertices)},indent=2))
print('FOREGRIP_STATIC_DONE')
