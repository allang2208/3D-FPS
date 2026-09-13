"""Deliver an editable attachment assembly on the accepted pistol rig."""
import bpy,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.data.bones['WPN_root'].matrix_local.copy()
with bpy.data.libraries.load(str(O/'M1911_Attachments_Editable.blend'),link=False) as (source,dest):
    dest.objects=[n for n in source.objects if n in ['M1911_holographic','M1911_panoramic_red_dot','M1911_suppressor']]
col=bpy.data.collections.new('M1911_FITTED_SHARED_ATTACHMENTS');bpy.context.scene.collection.children.link(col)
for ob in dest.objects:
    col.objects.link(ob);suppressor=ob.name=='M1911_suppressor'
    # Same centimetre measurements and frames as M1911AttachmentVisual.cpp.
    origin=Vector((0,-.17587465,.02898)) if suppressor else Vector((0,.032,.0535))
    mount=Matrix.Translation(origin)@Matrix.Rotation(math.pi if suppressor else -math.pi/2,4,'Z')
    ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='WPN_Barrel' if suppressor else 'WPN_Slide'
    ob.matrix_world=rig.matrix_world@root@mount
    ob.hide_set(ob.name=='M1911_holographic');ob.hide_render=ob.name=='M1911_holographic'
    ob['shared_part']=ob.name;ob['runtime_source']='Source/FPSGAME/Weapons/M1911AttachmentVisual.cpp'
bpy.context.scene['M1911AttachmentNotes']='Panoramic is visible by default. Toggle holographic/panoramic visibility for the alternate optic. Attachments retain the existing action rig.'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_FittedAttachments_Editable.blend'))
print('M1911_FITTED_ASSEMBLY_SAVED',flush=True)
