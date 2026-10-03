"""Left-forearm wring across every PKM clip, measured on the shipped FBX.

The visible defect is a band of skin whose surface rolls backwards because
neighbouring bones that share that band disagree.  The camera-independent
measure of it is the pairwise angle between the world rotation deltas of the
bones that skin the forearm band:

    d_lo_vs_lo02   lowerarm_l          vs lowerarm_twist_02_l
    d_lo02_vs_lo01 lowerarm_twist_02_l vs lowerarm_twist_01_l
    d_up02_vs_lo   upperarm_twist_02_l vs lowerarm_l

A rigid forearm reads ~0.  Large values mean the band between those two bones
is being wrung.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'

CLIPS = {
    'idle': ROOT / 'Elbow39' / 'Exports' / 'A_PKM_idle.fbx',
    'reload': ROOT / 'Elbow39' / 'Exports' / 'A_PKM_reload.fbx',
    'reload_empty': ROOT / 'Elbow39' / 'Exports' / 'A_PKM_reload_empty.fbx',
    'aim': ROOT / 'Wrist12' / 'Exports' / 'A_PKM_aim.fbx',
    'aim_fire': ROOT / 'Feed13' / 'Exports' / 'A_PKM_aim_fire.fbx',
    'fire': ROOT / 'Feed13' / 'Exports' / 'A_PKM_fire.fbx',
    'inspect': ROOT / 'Wrist12' / 'Exports' / 'A_PKM_inspect.fbx',
    'equip': ROOT / 'EquipCharge31' / 'Animations' / 'base' / 'A_PKM_equip.fbx',
    'quick_melee': ROOT / 'Melee24' / 'Animations' / 'base' / 'A_PKM_quick_melee.fbx',
    'sprint_enter': ROOT / 'Combat17' / 'Animations' / 'base' / 'A_PKM_sprint_enter.fbx',
    'sprint_loop': ROOT / 'Combat17' / 'Animations' / 'base' / 'A_PKM_sprint_loop.fbx',
    'sprint_exit': ROOT / 'Combat17' / 'Animations' / 'base' / 'A_PKM_sprint_exit.fbx',
}

WATCH = ['upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l']


def angle_between(q1, q2):
    d = q1.rotation_difference(q2).angle
    return math.degrees(min(d, 2 * math.pi - d))


def measure(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type == 'ARMATURE')
    missing = [n for n in WATCH if n not in rig.pose.bones]
    if missing:
        return {'error': 'missing bones %s' % missing}
    act = rig.animation_data.action if rig.animation_data else None
    if act is None:
        return {'error': 'no action'}
    fps = scene.render.fps
    start, end = map(int, act.frame_range)
    step = max(1, int(round(fps / 15.0)))

    rest = {n: rig.data.bones[n].matrix_local.copy() for n in WATCH}
    rows = []
    for frame in range(start, end + 1, step):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pb = rig.pose.bones
        quats = {}
        for n in WATCH:
            m = pb[n].matrix @ rest[n].inverted()
            q = m.to_3x3().to_quaternion()
            if q.w < 0:
                q.negate()
            quats[n] = q
        s = pb['upperarm_l'].matrix.translation
        e = pb['lowerarm_l'].matrix.translation
        w = pb['hand_l'].matrix.translation if 'hand_l' in pb else e
        axis = (w - e).normalized() if (w - e).length > 1e-9 else Vector((0, 0, 1))

        def twist(n):
            q = quats[n]
            v = Vector((q.x, q.y, q.z))
            return math.degrees(2 * math.atan2(v.dot(axis), q.w))

        rows.append({
            'frame': frame,
            'seconds': round(frame / fps, 3),
            'bend_deg': round(math.degrees((e - s).normalized().angle(
                (w - e).normalized())) if (w - e).length > 1e-9 else 0.0, 1),
            'd_lo_vs_lo02': round(angle_between(quats['lowerarm_l'],
                                                quats['lowerarm_twist_02_l']), 1),
            'd_lo02_vs_lo01': round(angle_between(quats['lowerarm_twist_02_l'],
                                                  quats['lowerarm_twist_01_l']), 1),
            'd_up02_vs_lo': round(angle_between(quats['upperarm_twist_02_l'],
                                                quats['lowerarm_l']), 1),
            'd_up_vs_up02': round(angle_between(quats['upperarm_l'],
                                                quats['upperarm_twist_02_l']), 1),
            'twist_lowerarm_l': round(twist('lowerarm_l'), 1),
            'twist_lo_tw02': round(twist('lowerarm_twist_02_l'), 1),
            'twist_lo_tw01': round(twist('lowerarm_twist_01_l'), 1),
        })
    return {'fps': fps, 'frames': [start, end], 'samples': len(rows), 'rows': rows}


report = {}
for key, path in CLIPS.items():
    if not path.exists():
        report[key] = {'error': 'missing %s' % path}
        print('%-13s MISSING %s' % (key, path))
        continue
    res = measure(path)
    report[key] = res
    if 'error' in res:
        print('%-13s ERROR %s' % (key, res['error']))
        continue
    rows = res['rows']

    def worst(field):
        r = max(rows, key=lambda x: x[field])
        return r[field], r['seconds']

    w1, t1 = worst('d_lo_vs_lo02')
    w2, t2 = worst('d_lo02_vs_lo01')
    w3, t3 = worst('d_up02_vs_lo')
    wring = max(rows, key=lambda x: x['d_lo_vs_lo02'] + x['d_lo02_vs_lo01'])
    res['summary'] = {
        'worst_d_lo_vs_lo02': [w1, t1],
        'worst_d_lo02_vs_lo01': [w2, t2],
        'worst_d_up02_vs_lo': [w3, t3],
        'worst_wring_sum': [round(wring['d_lo_vs_lo02'] + wring['d_lo02_vs_lo01'], 1),
                            wring['seconds']],
        'mean_wring_sum': round(sum(r['d_lo_vs_lo02'] + r['d_lo02_vs_lo01']
                                    for r in rows) / len(rows), 1),
    }
    print('%-13s %2d..%-4d %3d samples | lo-lo02 max %5.1f@%5.2fs | '
          'lo02-lo01 max %5.1f@%5.2fs | up02-lo max %5.1f | wring mean %5.1f  worst %5.1f@%5.2fs'
          % (key, res['frames'][0], res['frames'][1], res['samples'],
             w1, t1, w2, t2, w3, res['summary']['mean_wring_sum'],
             res['summary']['worst_wring_sum'][0], res['summary']['worst_wring_sum'][1]))

(HERE / 'left_wring_all_clips.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nWRING_SCAN_DONE')