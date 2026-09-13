"""Save all fitted alternatives on the current editable M1911 source; no render."""
import bpy, math
from mathutils import Matrix, Vector
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'M1911_CompactTactical_Assembly_Editable.blend'))
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
collection=bpy.data.collections.new('M1911_COMPACT_OPTICS_AND_MUZZLE');bpy.context.scene.collection.children.link(collection)
for key in ['holographic','panoramic_red_dot','suppressor']:
    with bpy.data.libraries.load(str(O/'M1911_CompactOptics_Editable.blend'),link=False) as (src,dst):
        dst.objects=['M1911_'+key]
    ob=dst.objects[0];collection.objects.link(ob)
    can=key=='suppressor';position=Vector((0,-.16787465,.02898) if can else (0,.030,.0495))
    # Optics author +X and suppressor author +Y both face down pistol -Y.
    local=Matrix.Translation(position) @ Matrix.Rotation(math.pi if can else -math.pi/2,4,'Z')
    ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='WPN_Barrel' if can else 'WPN_Slide'
    ob.matrix_world=root @ local
    ob.hide_set(key=='panoramic_red_dot');ob.hide_render=key=='panoramic_red_dot'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_CompactFit_Assembly_Editable.blend'))
print('M1911_COMPACT_ASSEMBLY_SAVED',flush=True)
