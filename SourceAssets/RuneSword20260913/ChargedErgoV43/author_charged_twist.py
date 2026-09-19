"""Author V43: redistribute the charged attack's left forearm axial rotation.

Reads the current authoring source (V42 chain, carrying the accepted V22
charged-arm fix) and rebuilds the left forearm track of HeavyCharge,
HeavyRelease and Slash1 so the pronation is spread along the forearm instead
of landing on the elbow. Bone positions, bone directions, the hand's world
orientation (grip), the sword, the right arm and the timing are preserved.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Matrix, Quaternion

P = Path(__file__).parent
sys.path.insert(0, str(P))
sys.path.insert(0, str(P.parent / 'CompactRecoveryV8'))
import twist_distribution as td
import rhythm_clock

SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
FPS = 480.0
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}

edited = (td.LO, td.TWIST_01, td.TWIST_02, td.HAND)
report = {'source': str(SOURCE), 'fps': FPS, 'edited_bones': list(edited), 'clips': []}

for clip in CLIPS:
    source = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    start, end = map(int, source.frame_range)

    targets = {}
    rolls = []
    for f in range(start, end + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        seconds = f / FPS
        weight = td.envelope(clip, seconds, rhythm_clock.source_time)
        rebuilt = td.rebuild(pose, rest, weight)
        info = td.forearm_roll(pose, rest)
        rolls.append({
            'seconds': seconds,
            'weight': weight,
            'authored_roll_deg': __import__('math').degrees(info['roll']),
            'decomposition_error_deg': td.verify_decomposition(pose, rest),
        })
        entry = {'upperarm_l': pose['upperarm_l']}
        for name in edited:
            entry[name] = rebuilt.get(name, pose[name])
        targets[f] = entry

    source.name = 'REF_V43_' + source.name
    source.use_fake_user = True
    action = source.copy()
    action.name = 'A_RuneSword_' + clip
    action.use_fake_user = True

    def edited_curve(curve):
        return any(curve.data_path.startswith('pose.bones["' + n + '"].') for n in edited)

    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if edited_curve(curve):
                        bag.fcurves.remove(curve)

    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_start, scene.frame_end = start, end
    previous = {}
    for f in range(start, end + 1):
        scene.frame_set(f)
        entry = targets[f]
        for name in edited:
            parent_name = parent[name]
            parent_pose = entry.get(parent_name)
            if parent_pose is None:
                parent_pose = rig.pose.bones[parent_name].matrix.copy()
            m = parent_pose.inverted() @ entry[name]
            loc, q, scale = (local_rest[name].inverted() @ m).decompose()
            if name in previous and q.dot(previous[name]) < 0:
                q.negate()
            previous[name] = q.copy()
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
    weights = [r['weight'] for r in rolls]
    report['clips'].append({
        'clip': clip, 'frames': [start, end], 'seconds': (end - start) / FPS,
        'weight_first': weights[0], 'weight_last': weights[-1],
        'weight_max': max(weights),
        'authored_roll_deg_range': [min(r['authored_roll_deg'] for r in rolls),
                                    max(r['authored_roll_deg'] for r in rolls)],
        'decomposition_error_deg_max': max(r['decomposition_error_deg'] for r in rolls),
    })
    print('V43_EXPORTED', clip, flush=True)

target = bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action = target
rig.animation_data.action_slot = target.slots[0]
scene.frame_start, scene.frame_end = 0, 960
scene.frame_set(960)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_ChargedErgoV43.blend'))
report['method'] = ('Left forearm axial rotation moved from lowerarm_l onto a linear '
                    'gradient over lowerarm_twist_02_l / lowerarm_twist_01_l, with the '
                    'hand rebuilt against the new parent so its world orientation and '
                    'the grip are unchanged')
report['envelopes'] = {'HeavyCharge': 'ramp in over 100 ms, held to the end',
                       'HeavyRelease': 'held to 850 ms, ramp out to 1000 ms',
                       'Slash1': 'charge clock from the early release, out over 650-850 ms'}
(P / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RUNESWORD_V43_AUTHORED', flush=True)
print(json.dumps(report, indent=2), flush=True)
