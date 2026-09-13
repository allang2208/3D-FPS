"""Assemble the fitted red dot and brake on the current pistol source without rendering."""
import bpy,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
collection=bpy.data.collections.new('M1911_REFINED_REDDOT_AND_BRAKE');bpy.context.scene.collection.children.link(collection)
for key in ['panoramic_red_dot','brake']:
    with bpy.data.libraries.load(str(O/('M1911_'+key+'_Editable.blend')),link=False) as (src,dst):dst.objects=['M1911_'+key]
    ob=dst.objects[0];collection.objects.link(ob)
    brake=key=='brake';position=Vector((0,-.16187465,.02898) if brake else (0,.030,.0495))
    local=Matrix.Translation(position) @ Matrix.Rotation(math.pi if brake else -math.pi/2,4,'Z')
    ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='WPN_Barrel' if brake else 'WPN_Slide';ob.matrix_world=root @ local
    ob.hide_set(False);ob.hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_RedDot_Brake_Assembly_Editable.blend'))
print('M1911_REDDOT_BRAKE_ASSEMBLY_SAVED',flush=True)
