"""Place the refined saddle on the unchanged current pistol, without a render."""
import bpy,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
collection=bpy.data.collections.new('M1911_SCULPTED_PANORAMIC_MOUNT');bpy.context.scene.collection.children.link(collection)
with bpy.data.libraries.load(str(O/'M1911_SculptedMount_Editable.blend'),link=False) as (src,dst):dst.objects=['M1911_panoramic_red_dot']
ob=dst.objects[0];collection.objects.link(ob);ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='WPN_Slide'
ob.matrix_world=root @ Matrix.Translation((0,.030,.0495)) @ Matrix.Rotation(-math.pi/2,4,'Z')
ob.hide_set(False);ob.hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_SculptedMount_Assembly_Editable.blend'))
print('M1911_SCULPTED_MOUNT_ASSEMBLED',flush=True)
