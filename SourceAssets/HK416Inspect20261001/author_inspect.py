"""Shared rifle inspection, fitted to HK416's existing six held-pose families.

Use the AKM/SVD inspection's weapon trajectory, with a smaller rotation and
travel. Both complete arm chains and the assembled gun move together. Existing
finger, wrist, elbow and mechanical-part relationships remain the held pose.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

O = Path(__file__).parent
S = O.parent
FAMILIES = ('base', 'vertical', 'canted', 'prism', 'angled', 'drum')
FPS = 60
END = 252
ROTATION_GAIN = .42
TRAVEL_GAIN = .55


def sample(rig, action, frame):
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def smooth(a, b, x):
    t = max(0., min(1., (x-a)/(b-a)))
    return t*t*(3.-2.*t)


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    donor_file = S/'AKMIntegration20260910/Native/AKM_MannyNative_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(donor_file))
    rig = bpy.data.objects['SK_M4_Infima']
    donor_action = bpy.data.actions['AKM_Native_inspect']
    start, stop = donor_action.frame_range
    origin = sample(rig, donor_action, start)['WPN_root']
    trajectory = []
    for index in range(END*2+1):
        frame = index*.5
        raw = origin.inverted() @ sample(rig, donor_action, start+(stop-start)*frame/END)['WPN_root']
        ease = smooth(0., 15., frame)*(1.-smooth(END-30., END, frame))
        q = raw.to_quaternion()
        if q.w < 0:
            q.negate()
        trajectory.append(Matrix.LocRotScale(raw.translation*(TRAVEL_GAIN*ease),
            Quaternion().slerp(q, ROTATION_GAIN*ease), Vector((1, 1, 1))))

    native_file = S/'HK416Reworked20260930/HK416_Gameplay_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(native_file))
    rig = bpy.data.objects['SK_M4_Infima']
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1.
    rig.data.pose_position = 'POSE'
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n: rest[parents[n]].inverted() @ m if parents[n] else m for n, m in rest.items()}
    held = {family: sample(rig, bpy.data.actions['HK416_'+family+'_idle'], 0)
            for family in ('base', 'vertical')}
    for family in ('canted', 'prism', 'angled', 'drum'):
        file = S/'HK416CommonAttachments20260930'/('HK416_'+family+'_Animations_Editable.blend')
        with bpy.data.libraries.load(str(file), link=False) as (_, dest):
            dest.actions = ['HK416_'+family+'_idle']
        held[family] = sample(rig, dest.actions[0], 0)

    def move_with_gun(name):
        while name:
            if name in ('clavicle_l', 'clavicle_r', 'ik_hand_root', 'WPN_root'):
                return True
            name = parents[name]
        return False

    moved = {n for n in rest if move_with_gun(n)}
    report = {
        'reference': 'AKM_Native_inspect weapon trajectory, also used by SVD; HK416 native held poses',
        'donor': str(donor_file), 'donor_action': 'AKM_Native_inspect',
        'source_frames': [start, stop], 'source_fps': 120,
        'duration': END/FPS, 'rotation_gain': ROTATION_GAIN, 'travel_gain': TRAVEL_GAIN,
        'sample_rate': 120, 'runtime_tested': False, 'clips': {},
    }
    for family in FAMILIES:
        idle = held[family]
        weapon = idle['WPN_root']
        poses = []
        for motion in trajectory:
            delta = weapon @ motion @ weapon.inverted()
            poses.append({n: delta @ m if n in moved else m.copy() for n, m in idle.items()})
        # Exact native grip at both boundaries; no late elbow or finger reset.
        poses[0] = {n: m.copy() for n, m in idle.items()}
        poses[-1] = {n: m.copy() for n, m in idle.items()}
        name = 'HK416_'+family+'_inspect'
        if name in bpy.data.actions:
            bpy.data.actions[name].name = 'REFERENCE_'+name
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        rig.animation_data.action = action
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=0)
        curves = {(c.data_path, c.array_index): c for layer in action.layers
            for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
        for n in rest:
            values = []
            previous = None
            for pose in poses:
                local = pose[parents[n]].inverted() @ pose[n] if parents[n] else pose[n]
                loc, q, scale = (local_rest[n].inverted() @ local).decompose()
                if previous is not None and q.dot(previous) < 0:
                    q.negate()
                previous = q.copy()
                values.append((loc, q, scale))
            for prop, column, width in (('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)):
                for axis in range(width):
                    curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(values))
                    curve.keyframe_points.foreach_set('co', [v for i, row in enumerate(values)
                        for v in (i*.5, row[column][axis])])
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
                    curve.update()
        scene.frame_start = 0
        scene.frame_end = END
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        folder = output/'Animations'/family
        folder.mkdir(parents=True, exist_ok=True)
        file = folder/('A_'+name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(file), use_selection=True, object_types={'ARMATURE'},
            axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_step=.5, bake_anim_simplify_factor=0)
        report['clips'][family+'/inspect'] = {'family':family, 'kind':'inspect',
            'name':'A_'+name, 'file':str(file), 'duration':END/FPS, 'source_action':name}
        print('HK416_INSPECT_AUTHORED', family, flush=True)
    sample(rig, bpy.data.actions['HK416_base_inspect'], 0)
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'HK416_Inspect_Editable.blend'))
    (output/'inspect_animations.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-directory', type=Path, default=O)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    result = author(args.output_directory)
    print('HK416_INSPECT_EXPORT_COMPLETE', len(result['clips']), flush=True)
