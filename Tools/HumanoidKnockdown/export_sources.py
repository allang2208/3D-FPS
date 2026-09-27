"""Extract licensed Mesh2Motion clips, preserving the original skeleton and timing."""
import bpy, json
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidKnockdown20260926')
SOURCE = Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieMeshy20260913/sources')
ROOT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
report = {}
for package, clips in [('human-base-animations.glb', ['Hit_Knockback', 'LayToIdle']),
                       ('human-addon-animations.glb', ['Zombie_Rise'])]:
    for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE / package))
    rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
    rig.name = 'M2MRoot'
    for track in rig.animation_data.nla_tracks: track.mute = True
    for name in clips:
        action = next(a for a in bpy.data.actions if a.name == name or a.name.endswith('|' + name))
        rig.animation_data.action = action
        if len(action.slots): rig.animation_data.action_slot = action.slots[0]
        first, last = action.frame_range
        scene.frame_start, scene.frame_end = round(first), round(last)
        samples = []
        for f in [first, first + (last-first)*.5, last]:
            scene.frame_set(int(f), subframe=f-int(f))
            bpy.context.view_layer.update()
            sample = {bone: list(rig.matrix_world @ rig.pose.bones[bone].head)
                      for bone in ['pelvis','spine_03','head','hand_l','hand_r','foot_l','foot_r']}
            rest = rig.data.bones['spine_03'].matrix_local
            chest = rig.pose.bones['spine_03'].matrix
            sample['chest_facing'] = list((rig.matrix_world.to_3x3() @ chest.to_3x3()
                                          @ rest.to_3x3().inverted() @ Vector((0,-1,0))).normalized())
            samples.append(sample)
        bpy.ops.object.select_all(action='DESELECT')
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        output = ROOT / ('A_M2M_' + name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(output), use_selection=True, object_types={'ARMATURE'},
            add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
            axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')
        report[name] = {'source': package, 'first': first, 'last': last,
                        'seconds': (last-first)/30, 'samples_m': samples, 'fbx': str(output)}
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / (Path(package).stem + '.blend')))
(ROOT / 'source_clips.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KNOCKDOWN_SOURCES ' + json.dumps(report))
