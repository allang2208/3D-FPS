"""Author V45: bring the charged hold in so the left elbow bends."""
import bpy, json, sys
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
sys.path.insert(0, str(P.parent / 'CompactRecoveryV8'))
import hold_shift as hs
import shoulder_transport as st
import rhythm_clock

SOURCE = P / 'AzureRunesword_ChargedShoulderV44.blend'
OUT = P / 'ExportV45'
OUT.mkdir(exist_ok=True)
FPS = 480.0
DISTANCE = 0.070
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')
EDITED = ('WPN_root', 'upperarm_l', 'lowerarm_l', 'hand_l',
          'upperarm_r', 'lowerarm_r', 'hand_r')

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n] for n in rest}

report = {'source': str(SOURCE), 'fps': FPS, 'hold_shift_m': DISTANCE,
          'edited_bones': list(EDITED), 'clips': []}

for clip in CLIPS:
    source = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    start, end = map(int, source.frame_range)
    targets = {}
    stats = {'left_elbow_before_deg': 0.0, 'left_elbow_after_deg': 0.0,
             'right_elbow_before_deg': 0.0, 'right_elbow_after_deg': 0.0,
             'left_reach_before_m': 0.0, 'left_reach_after_m': 0.0,
             'weight_min': 1.0, 'weight_max': 0.0}
    for f in range(start, end + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        weight = hs.envelope(clip, f / FPS, rhythm_clock.source_time)
        built, info = hs.build(pose, weight, DISTANCE, rest=rest,
                               roll_solver=lambda p, r: st.solve_roll(p, r, cap=95.0))
        targets[f] = built if built else {n: pose[n] for n in EDITED}
        if info:
            left, right = info['left'], info['right']
            stats['left_elbow_before_deg'] = max(stats['left_elbow_before_deg'],
                                                 left['elbow_bone_angle_before'])
            stats['left_elbow_after_deg'] = max(stats['left_elbow_after_deg'],
                                                left['elbow_bone_angle_after'])
            stats['right_elbow_before_deg'] = max(stats['right_elbow_before_deg'],
                                                  right['elbow_bone_angle_before'])
            stats['right_elbow_after_deg'] = max(stats['right_elbow_after_deg'],
                                                 right['elbow_bone_angle_after'])
            stats['left_reach_before_m'] = max(stats['left_reach_before_m'],
                                               left['reach_before_m'])
            stats['left_reach_after_m'] = max(stats['left_reach_after_m'],
                                              left['reach_after_m'])
        stats['weight_min'] = min(stats['weight_min'], weight)
        stats['weight_max'] = max(stats['weight_max'], weight)

    source.name = 'REF_V45_' + source.name
    source.use_fake_user = True
    action = source.copy()
    action.name = 'A_RuneSword_' + clip
    action.use_fake_user = True

    def edited_curve(curve):
        return any(curve.data_path.startswith('pose.bones["' + n + '"].') for n in EDITED)

    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if edited_curve(curve):
                        bag.fcurves.remove(curve)

    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_start, scene.frame_end = start, end
    previous_q = {}
    for f in range(start, end + 1):
        scene.frame_set(f)
        entry = targets[f]
        for name in EDITED:
            parent_name = parent[name]
            parent_pose = entry.get(parent_name)
            if parent_pose is None:
                parent_pose = rig.pose.bones[parent_name].matrix.copy()
            m = parent_pose.inverted() @ entry[name]
            loc, q, scale = (local_rest[name].inverted() @ m).decompose()
            if name in previous_q and q.dot(previous_q[name]) < 0:
                q.negate()
            previous_q[name] = q.copy()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.location = loc
            bone.rotation_quaternion = q
            bone.scale = scale
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=f, group=name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if edited_curve(curve):
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'

    scene.render.fps = int(FPS)
    scene.render.fps_base = 1.0
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / ('A_RuneSword_' + clip + '.fbx')),
        use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    report['clips'].append({'clip': clip, 'frames': [start, end],
                            'seconds': (end - start) / FPS, **stats})
    print('V45_EXPORTED', clip, json.dumps(stats), flush=True)

target = bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action = target
rig.animation_data.action_slot = target.slots[0]
scene.frame_start, scene.frame_end = 0, 960
scene.frame_set(960)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_ChargedHoldV45.blend'))
report['method'] = ('Whole hold (sword plus both hands) shifted along the left '
                    'wrist-to-shoulder line, both arms re-solved with a two-bone IK '
                    'that keeps the authored elbow side; hand grips and orientations '
                    'are unchanged so contact with the hilt is preserved')
(P / 'authoring_v45.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RUNESWORD_V45_AUTHORED', flush=True)
