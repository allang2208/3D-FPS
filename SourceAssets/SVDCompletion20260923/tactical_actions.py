"""SVD tactical sprint and stock bash, fitted to its own authored idle.

Reuses the rifle sprint release/regrip and the M4 N / QBZ O motion method.
Only animation is authored. No rendering or runtime acceptance is performed.
"""
import ast
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

O = Path(__file__).resolve().parent
S = O.parent
OUT = O / 'TacticalActions'
STOCK = Vector((0., .348, -.035))  # Same surface anchor as QuickCombatRifleMotion.h.
sys.path[:0] = [str(S / 'M4QuickMeleeRefine20260919K'),
               str(S / 'M4QuickMeleeRefine20260919N'),
               str(S / 'QBZ191QuickMeleeGrip20260919O')]
from arm_support import ArmSupport
from natural_wrist import NaturalWrist, smooth
from grip_solver import GripBearing


class LockedWrist(NaturalWrist):
    def target(self, pose, angle):
        return pose['hand_r'].copy()


def functions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(path), 'exec'), namespace)


def sprint_generator(rig, idle):
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    barrel = idle['WPN_SOCKET_Muzzle'].translation - idle['WPN_root'].translation
    settings = {
        'right_wrist_offset_m': [.115, .105, -.015],
        'left_wrist_relax': {'released_share': .55, 'withdrawn_share': .40},
        'left_wrist_hang': {'reach': .98, 'side_offset': [-.055, .03],
                            'swing': [-.006, -.050]},
        'finger_relax': .68,
    }
    ns = dict(math=math, Matrix=Matrix, Vector=Vector, Euler=Euler, Quaternion=Quaternion,
              names=list(rest), rest=rest, parent=parents, idle=idle, settings=settings,
              lr={n: rest[parents[n]].inverted() @ m if parents[n] else m for n, m in rest.items()},
              raise_pitch=76. - math.degrees(math.atan2(barrel.z, math.hypot(barrel.x, barrel.y))))
    functions(S / 'DanWesson71520260913/author_weapon.py', {'hand_at'}, ns)
    functions(S / 'RifleTacticalSprint20260915/author_sprint.py', {'smooth', 'turn', 'make_pose'}, ns)
    return ns['make_pose'], settings


def donor_motion(rig):
    """Load only the donor armature/action; never replace the target scene or mesh."""
    path = S / 'M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend'
    action_name = 'M4_QuickCombatRefineN_Base'
    previous_action = rig.animation_data.action
    previous_slot = rig.animation_data.action_slot
    with bpy.data.libraries.load(str(path), link=False) as (available, loaded):
        loaded.objects = ['SK_M4_Infima']
        loaded.actions = [action_name]
    donor = loaded.objects[0]
    bpy.context.scene.collection.objects.link(donor)
    donor.animation_data.action = loaded.actions[0]
    donor.animation_data.action_slot = loaded.actions[0].slots[0]
    poses = []
    for frame in range(109):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        poses.append({n: donor.pose.bones[n].matrix.copy() for n in ('WPN_root', 'hand_r')})
    bpy.data.objects.remove(donor, do_unlink=True)
    rig.animation_data.action = previous_action
    rig.animation_data.action_slot = previous_slot
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    root = poses[0]['WPN_root']
    return [p['WPN_root'] @ root.inverted() for p in poses], poses[0], str(path)


def melee_poses(rig, idle):
    donor, source_idle, source_path = donor_motion(rig)
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    support = ArmSupport(rig, idle)
    # Fit support from SVD shoulders, rather than copying M4's absolute anchors.
    for side in ('r', 'l'):
        support.parameters['shoulder_anchors_m'][side] = list(
            idle['upperarm_' + side].translation + Vector((0., -.035, -.01)))
    bearing = GripBearing(idle, rest, STOCK)
    natural = LockedWrist(idle, rest, support.stations)
    shift = idle['hand_r'].translation - source_idle['hand_r'].translation
    source_stock = source_idle['WPN_root'] @ Vector((0., .235, .025))
    own_stock = idle['WPN_root'] @ STOCK
    roots, adjustments = [], []
    for frame in range(109):
        time = frame / 120.
        weight = smooth(time / .1) * (1. - smooth((time - .72) / (.866666667 - .72)))
        delta = Matrix.Identity(4)
        if 0 < frame < 104:
            delta = Matrix.Translation(shift) @ donor[frame] @ Matrix.Translation(-shift)
            stock_target = donor[frame] @ source_stock + (own_stock - source_stock) * (1. - weight)
            delta.translation += (stock_target - delta @ own_stock) * weight
            delta = support.fit_group(delta, weight)
        root = delta @ idle['WPN_root']
        roots.append(root)
        if weight > 1e-7:
            bearing.fit(root, {s: support.shoulder(s, weight) for s in ('r', 'l')}, weight)
            adjustments.append(list(bearing.previous) + list(bearing.translation))
        else:
            adjustments.append([0.] * 6)
    # Smooth the offline bearing solution, preserving a single contact/recovery.
    for _ in range(3):
        adjustments = [[sum(adjustments[min(108, max(0, f + k - 2))][j] * w
                            for k, w in enumerate((1, 4, 6, 4, 1))) / 16.
                        for j in range(6)] for f in range(109)]
    result = []
    for frame, root in enumerate(roots):
        time = frame / 120.
        weight = smooth(time / .1) * (1. - smooth((time - .72) / (.866666667 - .72)))
        pose = {n: m.copy() for n, m in idle.items()}
        if 0 < frame < 104:
            values = adjustments[frame]
            rotation, offset = Vector(values[:3]), Vector(values[3:])
            cap = math.radians(100.) * weight
            if rotation.length > cap:
                rotation = rotation.normalized() * cap
            if offset.length > .16 * weight:
                offset = offset.normalized() * (.16 * weight)
            q = Quaternion(rotation.normalized(), rotation.length) if rotation.length > 1e-8 else Quaternion()
            pivot = (root @ bearing.hands['r']).translation
            gun = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ root
            gun.translation += offset
            delta = support.fit_group(gun @ idle['WPN_root'].inverted(), weight)
            for name in pose:
                if name.startswith('WPN_'):
                    pose[name] = delta @ idle[name]
            for side in ('r', 'l'):
                support.apply(pose, side, delta @ idle['hand_' + side], weight)
            pose.update(natural.apply(pose, time))
        result.append(pose)
    return result, {'source': source_path, 'method': 'own-grip locked bearing and complete arm support',
                    'duration': .9, 'contact_seconds': 1. / 6.,
                    'stock_root_m': list(STOCK), 'arm_support': support.parameters}


def author_actions(rig, idle, bake):
    OUT.mkdir(exist_ok=True)
    report = {'status': 'Authored only; runtime testing remains manual', 'clips': {}}
    make_sprint, settings = sprint_generator(rig, idle)
    # A slightly longer transition suits SVD's long barrel; stride phase is supplied
    # by the existing runtime component, not a second free-running animation clock.
    for key, count in [('sprint_enter', 48), ('sprint_loop', 120), ('sprint_exit', 48)]:
        poses = []
        for frame in range(count + 1):
            fraction = frame / count
            progress = 1. if key == 'sprint_loop' else 1. - fraction if key == 'sprint_exit' else fraction
            phase = 2. * math.pi * fraction if key == 'sprint_loop' else None
            poses.append(make_sprint(progress, phase))
        bake(rig, poses, key, 120)
        report['clips'][key] = {'source': 'RifleTacticalSprint20260915 fitted to A_SVD_idle',
                                'frames': count, 'fps': 120, 'duration': count / 120.,
                                'settings': settings}
        print('SVD_TACTICAL_AUTHORED', key, flush=True)
    # Sampling a donor after sprint baking must start from the target's true idle.
    action = bpy.data.actions['A_SVD_idle']
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    poses, info = melee_poses(rig, idle)
    bake(rig, poses, 'quick_melee', 120)
    report['clips']['quick_melee'] = dict(info, frames=108, fps=120)
    (OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('SVD_TACTICAL_AUTHORED quick_melee', flush=True)
    return report['clips']
