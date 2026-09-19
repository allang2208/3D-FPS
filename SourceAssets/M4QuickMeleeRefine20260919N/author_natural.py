"""Bake a grip-centred right-hand turn and the connected arm from K."""
import json, sys
from pathlib import Path

import bpy
from mathutils import Matrix

P = Path(__file__).parent
sys.path.insert(0, str(P))
from natural_wrist import NaturalWrist, EDITED
SOURCE = P.parent / 'M4QuickMeleeRefine20260919K'
plan = {'revision':'NaturalGripTurnN','source_revision':'HingeShoulderRefineK','profiles':sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Base','Drum','Angled','Vertical','Canted','Prism']}
source_receipt = json.loads((SOURCE / 'authoring.json').read_text())
receipt = {'revision': plan['revision'], 'source_revision': plan['source_revision'],
           'profiles': {}, 'testing': 'Scoped source inspection requested; see source_checks.json; no PIE claim'}

for profile in plan['profiles']:
    source = SOURCE / profile / f'M4_QuickCombat_{profile}_Editable.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_M4_Infima']
    original = bpy.data.actions['M4_QuickCombatRefineK_' + profile]
    rig.animation_data.action = original
    rig.animation_data.action_slot = original.slots[0]
    names = [bone.name for bone in rig.data.bones]
    parents = {bone.name: bone.parent.name if bone.parent else None for bone in rig.data.bones}
    rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
    local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}
    first, last = int(scene.frame_start), int(scene.frame_end)

    # Cache the complete source before keying any changes into a new action.
    poses = []
    for frame in range(first, last + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        poses.append({bone.name: bone.matrix.copy() for bone in rig.pose.bones})
    idle = poses[0]
    balance = NaturalWrist(idle, rest, source_receipt['profiles'][profile]['skin_stations'])
    edited = set(EDITED)

    action = original.copy()
    action.name = 'M4_QuickCombatRefineN_' + profile
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    prefixes = tuple(f'pose.bones["{n}"].' for n in edited)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if curve.data_path.startswith(prefixes):
                        bag.fcurves.remove(curve)

    previous = {}
    for frame, old in zip(range(first, last + 1), poses):
        target = dict(old)
        target.update(balance.apply(old, (frame-first) / scene.render.fps))
        for name in edited:
            parent = parents[name]
            basis = local_rest[name].inverted() @ (target[parent].inverted() @ target[name]
                                                   if parent else target[name])
            location, rotation, scale = basis.decompose()
            if name in previous and previous[name].dot(rotation) < 0:
                rotation.negate()
            previous[name] = rotation.copy()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.location, bone.rotation_quaternion, bone.scale = location, rotation, scale
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=frame, group=name)

    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path.startswith(prefixes):
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    scene.frame_set(first)
    destination = P / profile
    (destination / 'Animations').mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = destination / 'Animations' / f'A_M4_QuickCombat_{profile}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
                            axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                            bake_anim=True, bake_anim_use_all_actions=False,
                            bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                            bake_anim_step=1.0, bake_anim_simplify_factor=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination / f'M4_QuickCombat_{profile}_Editable.blend'))
    receipt['profiles'][profile] = {'source': str(source), 'action': action.name,
                                   'edited_bones': sorted(edited), 'fbx': str(fbx),
                                   'duration': (last-first) / scene.render.fps, 'samples':balance.records}
    print('M4_WRIST_N_EXPORTED', profile, flush=True)

(P / 'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
