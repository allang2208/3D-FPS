"""Export only the replacement motion donors; retain previous source assets."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).parent; (ROOT/'prepared').mkdir(exist_ok=True)
report={}
for library,clips in [('human-base-animations.glb',{'Jog':'Jog','Hit_Chest':'HitChest'}),('human-addon-animations.glb',{'Zombie_Walk_2':'ZombiePosture'})]:
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(ROOT.parent/'sources'/library))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE'); rig.name='M2MRoot'
    for name,role in clips.items():
        a=bpy.data.actions[name]; rig.animation_data_create(); rig.animation_data.action=a; rig.animation_data.action_slot=a.slots[0]
        for track in rig.animation_data.nla_tracks: track.mute=True
        start,end=a.frame_range; scene=bpy.context.scene; scene.frame_start=round(start); scene.frame_end=round(end)
        scene.frame_set(scene.frame_start); bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.fbx(filepath=str(ROOT/f'prepared/A_M2M_{role}.fbx'),use_selection=True,object_types={'ARMATURE'},
            add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
        report[role]={'source':name,'library':library,'source_frames':[start,end],'source_fps':30,'export_seconds':(round(end)-round(start))/30}
(ROOT/'source_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('REPLACEMENT_DONORS_PREPARED '+json.dumps(report))
