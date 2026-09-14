"""Package the authored clips with skin clusters for UE skeleton discovery."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'FatZombie_Meshy_Animated.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
contract=json.loads((ROOT/'animation_contract.json').read_text())
scene=bpy.context.scene;scene.render.fps=120
for role,item in contract['clips'].items():
    action=bpy.data.actions['A_FatZombie_'+role]
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_start=0;scene.frame_end=item['frames'][1];scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig]+meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT/f'final/A_FatZombie_{role}.fbx'),use_selection=True,
        object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE',path_mode='STRIP',embed_textures=False)
print('FAT_ZOMBIE_SKIN_PACKAGED')
