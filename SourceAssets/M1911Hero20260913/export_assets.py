"""Export the accepted skeleton at a cleared bind pose; keep author layers."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
def export_assets(out):
    s=bpy.context.scene;rig=bpy.data.objects['SK_M1911_Manny'];hands=bpy.data.objects['SK_Manny_Arms_Export']
    low=bpy.data.collections['M1911_LOW'];action=rig.animation_data.action if rig.animation_data else None
    # REST display alone does not clear an active Action's bone channels for FBX.
    rig.animation_data_clear()
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    rig.data.pose_position='POSE';bpy.context.view_layer.update()
    author_space=bpy.data.objects.get('M1911_AuthoringBindSpace')
    if not author_space:
        author_space=bpy.data.objects.new('M1911_AuthoringBindSpace',None);s.collection.objects.link(author_space)
        author_space.matrix_world=rig.data.bones['WPN_root'].matrix_local
        for colname in ['M1911_HIGH','M1911_CAGE']:
            for ob in bpy.data.collections[colname].objects:
                ob.parent=author_space;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    def select(objects):
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:ob.hide_set(False);ob.select_set(True)
        bpy.context.view_layer.objects.active=objects[-1]
    copies=[]
    for ob in low.objects:
        x=ob.copy();x.data=ob.data.copy();s.collection.objects.link(x);x.hide_set(False);copies.append(x)
    select(copies);bpy.ops.object.join();gun=bpy.context.object;gun.name='M1911_Hero_Export'
    select([hands,gun,rig])
    bpy.ops.export_scene.fbx(filepath=str(out/'SK_M1911_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.data.objects.remove(gun,do_unlink=True)
    if action:
        rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    s.frame_set(0);hands.hide_set(False);hands.hide_render=False
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'M1911_Hero_Editable.blend'))
if __name__=='__main__':
    O=Path(__file__).parent
    bpy.ops.wm.open_mainfile(filepath=str(O/'M1911_Hero_Editable.blend'))
    export_assets(O)
    print('M1911_HERO_BIND_EXPORT_COMPLETE',flush=True)
