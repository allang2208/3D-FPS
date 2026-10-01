"""Give the existing complete iron-sight mesh its own visibility material slot."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;C=O.parent/'HK416CommonAttachments20260930'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(C/'HK416_Modular_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST';r.animation_data_clear()
sight=next(o for o in bpy.context.scene.objects if o.get('HK416_SourceObject')=='ironsight_low')
source=sight.data.materials[0];m=source.copy();m.name='M_HK416_FactorySights';sight.data.materials[0]=m
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT')
for o in [r]+[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.get('HK416_SourceObject') or o.get('inspect_skin_source'))]:
 o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=r
file=O/'SK_HK416_ModularSights.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'HK416_ModularSights_Editable.blend'))
(O/'sight_section.json').write_text(json.dumps({'mesh':str(file),'source_blend':str(C/'HK416_Modular_Editable.blend'),'section':m.name,'original_material':source.name,'source_object':'ironsight_low','vertices':len(sight.data.vertices),'faces':len(sight.data.polygons),'geometry_modified':False},indent=2))
print('HK416_SIGHT_SECTION_AUTHORED',flush=True)
