"""Compact M4 N motion fitted to the HK416's six native held poses.

Production only: no render, game launch or acceptance probes. The 0.6 second
source already includes M4's current 1.5x playback; HK416 plays it at 1x.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

O = Path(__file__).parent
S = O.parent
sys.path.insert(0, str(S/'M4QuickMeleeRefine20260919K'))
from arm_support import ArmSupport

FAMILIES = ('base', 'drum', 'angled', 'vertical', 'canted', 'prism')
END = 108
FPS = 180
TRAVEL_GAIN = .70
ROTATION_GAIN = .90


def sample(rig, action, frame):
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def smooth(t):
    t = max(0., min(1., t))
    return t*t*t*(10.+t*(-15.+6.*t))


def author():
    O.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    donors = {}
    for family in FAMILIES:
        title = family.title()
        file = S/'M4QuickMeleeRefine20260919N'/title/f'M4_QuickCombat_{title}_Editable.blend'
        bpy.ops.wm.open_mainfile(filepath=str(file))
        rig = bpy.data.objects['SK_M4_Infima']
        action = bpy.data.actions['M4_QuickCombatRefineN_'+title]
        first, last = action.frame_range
        donors[family] = [sample(rig, action, first+(last-first)*i/END) for i in range(END+1)]

    native = S/'HK416Reworked20260930/HK416_Gameplay_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(native))
    rig = bpy.data.objects['SK_M4_Infima']
    rig.data.pose_position = 'POSE'
    scene = bpy.context.scene
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    local_rest = {n: rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
    held_actions = {f: bpy.data.actions['HK416_'+f+'_idle'] for f in ('base', 'vertical')}
    for family in FAMILIES:
        if family in held_actions:
            continue
        file = S/'HK416CommonAttachments20260930'/f'HK416_{family}_Animations_Editable.blend'
        with bpy.data.libraries.load(str(file), link=False) as (_, dest):
            dest.actions = ['HK416_'+family+'_idle']
        held_actions[family] = dest.actions[0]

    report = dict(reference='M4QuickMeleeRefine20260919N', source_fps=120,
                  playback_fps=FPS, duration=END/FPS, contact=(END/FPS)*5/27,
                  travel_gain=TRAVEL_GAIN, rotation_gain=ROTATION_GAIN,
                  native_source=str(native), runtime_tested=False, clips={})
    for family in FAMILIES:
        idle = sample(rig, held_actions[family], 0)
        reference = donors[family]
        origin = reference[0]['WPN_root']
        native_root = idle['WPN_root']
        reference_grip = origin.inverted()@reference[0]['hand_r']
        native_grip = native_root.inverted()@idle['hand_r']
        axes = native_root.to_quaternion()@origin.to_quaternion().inverted()
        support = ArmSupport(rig, idle)
        # Transfer only the donor's shoulder displacement, never an absolute
        # M4 shoulder or rear-grip anchor. Both HK hands keep their own contact.
        for side in ('r', 'l'):
            n = 'upperarm_'+side
            offset = axes@(reference[20][n].translation-reference[0][n].translation)
            support.parameters['shoulder_anchors_m'][side] = list(idle[n].translation+offset*TRAVEL_GAIN)
        poses = []
        for i, ref in enumerate(reference):
            p = {n:m.copy() for n,m in idle.items()}
            source_time = .9*i/END
            weight = smooth(source_time/.10)*(1.-smooth((source_time-.72)/.146666667))
            rotation = (origin.inverted()@ref['WPN_root']).to_quaternion()
            if rotation.w < 0:
                rotation.negate()
            root_rotation = native_root.to_quaternion()@Quaternion().slerp(rotation, ROTATION_GAIN)
            donor_grip = (ref['WPN_root']@reference_grip).translation
            grip_goal = idle['hand_r'].translation+axes@(donor_grip-reference[0]['hand_r'].translation)*TRAVEL_GAIN
            root = Matrix.LocRotScale(Vector(), root_rotation, native_root.to_scale())
            root.translation = grip_goal-(root@native_grip).translation
            delta = support.fit_group(root@native_root.inverted(), weight)
            for n in rest:
                if n.startswith('WPN_'):
                    p[n] = delta@idle[n]
            if 0 < i < END:
                for side in ('r', 'l'):
                    support.apply(p, side, delta@idle['hand_'+side], weight)
            else:
                p = {n:m.copy() for n,m in idle.items()}
            poses.append(p)

        name = 'HK416_'+family+'_quick_melee'
        if name in bpy.data.actions:
            bpy.data.actions[name].name = 'REFERENCE_'+name
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        rig.animation_data.action = action
        for b in rig.pose.bones:
            b.rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'):
                b.keyframe_insert(prop, frame=0)
        curves = {(c.data_path,c.array_index):c for layer in action.layers
                  for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
        for n in rest:
            values = []
            previous = None
            for p in poses:
                local = p[parents[n]].inverted()@p[n] if parents[n] else p[n]
                loc,q,scale = (local_rest[n].inverted()@local).decompose()
                if previous is not None and q.dot(previous) < 0:
                    q.negate()
                previous = q.copy()
                values.append((loc,q,scale))
            for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
                for axis in range(count):
                    curve = curves[(f'pose.bones["{n}"].{prop}',axis)]
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(values))
                    curve.keyframe_points.foreach_set('co', [v for i,row in enumerate(values) for v in (i,row[field][axis])])
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
                    curve.update()
        scene.render.fps = FPS
        scene.render.fps_base = 1.
        scene.frame_start = 0
        scene.frame_end = END
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        folder = O/'Animations'/family
        folder.mkdir(parents=True, exist_ok=True)
        file = folder/('A_'+name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(file), use_selection=True, object_types={'ARMATURE'},
            axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_step=1., bake_anim_simplify_factor=0)
        report['clips'][family] = dict(family=family, name='A_'+name, file=str(file),
            duration=END/FPS, source_action=name, support=support.parameters)
        (O/'animations.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('HK416_QUICK_MELEE_AUTHORED', family, flush=True)
    sample(rig, bpy.data.actions['HK416_base_quick_melee'], 0)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'HK416_QuickMelee_Editable.blend'))
    return report


if __name__ == '__main__':
    author()
