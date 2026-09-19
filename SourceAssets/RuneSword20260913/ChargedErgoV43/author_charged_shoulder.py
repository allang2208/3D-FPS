"""Author V44: carry the charged attack's left-arm twist at the shoulder.

Rebuilds only ``upperarm_l`` (a roll about its own axis, solved per frame) and
``lowerarm_l`` (whose local rotation changes to keep its world pose), so the
forearm, wrist, grip, sword, right arm, timing and every bone position stay as
authored while the elbow's axial difference goes to zero.
"""
import bpy, json, math, sys
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
sys.path.insert(0, str(P.parent / 'CompactRecoveryV8'))
import shoulder_transport as st
import rhythm_clock

SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'ExportV44'
OUT.mkdir(exist_ok=True)
FPS = 480.0
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')
EDITED = (st.UP, st.LO, st.HAND)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n] for n in rest}

report = {'source': str(SOURCE), 'fps': FPS, 'edited_bones': list(EDITED), 'clips': []}

for clip in CLIPS:
    source = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    start, end = map(int, source.frame_range)

    targets = {}
    roll_cap = 95.0
    previous = None
    stats = {'roll_deg_abs_max': 0.0, 'elbow_before_abs_max': 0.0,
             'elbow_after_abs_max': 0.0, 'residual_deg_max': 0.0, 'roll_first': 0.0,
             'roll_last': 0.0}
    for f in range(start, end + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        weight = st.envelope(clip, f / FPS, rhythm_clock.source_time)
        before = st.elbow_roll(pose, rest)
        solved, residual, _ = st.solve_roll(pose, rest, cap=roll_cap, previous=previous)
        previous = solved
        applied = solved * weight
        humerus = st.rolled_humerus(pose, rest, applied)
        entry = {st.UP: humerus}
        for name in (st.LO, st.HAND):
            entry[name] = pose[name]
        targets[f] = entry
        stats['roll_deg_abs_max'] = max(stats['roll_deg_abs_max'], abs(applied))
        stats['elbow_before_abs_max'] = max(stats['elbow_before_abs_max'], abs(before))
        stats['residual_deg_max'] = max(stats['residual_deg_max'], abs(residual))
        if f == start:
            stats['roll_first'] = applied
        stats['roll_last'] = applied
        # Residual after the applied (envelope-weighted) roll.
        modified = dict(pose)
        modified[st.UP] = humerus
        stats['elbow_after_abs_max'] = max(stats['elbow_after_abs_max'],
                                           abs(st.elbow_roll(modified, rest)))

    source.name = 'REF_V44_' + source.name
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
    print('V44_EXPORTED', clip, json.dumps(stats), flush=True)

target = bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action = target
rig.animation_data.action_slot = target.slots[0]
scene.frame_start, scene.frame_end = 0, 960
scene.frame_set(960)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_ChargedShoulderV44.blend'))
report['method'] = ('Per-frame secant solve rolls upperarm_l about its own axis until the '
                    'elbow axial difference is zero; the twist is carried by the shoulder. '
                    'Forearm, wrist, grip, sword, right arm, bone positions and timing unchanged.')
report['envelopes'] = {'HeavyCharge': 'ramp in over 100 ms, held to the end',
                       'HeavyRelease': 'held to 850 ms, ramp out to 1000 ms',
                       'Slash1': 'charge clock from the early release, out over 650-850 ms'}
(P / 'authoring_v44.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RUNESWORD_V44_AUTHORED', flush=True)
