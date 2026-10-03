"""Correct axial (twist) decomposition across the PKM left arm.

For bones a and b the relative rotation is taken in armature space and split
into the component about the live limb axis (twist) and the rest (swing).
Also prints the literal per-bone local channels the clip contains.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 60, [0.0]),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120, [0.0, 0.8, 1.6, 2.4, 3.2, 4.35, 5.72, 6.4]),
    'reload_empty': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
                     'PKM34_base_reload_empty', 120, [0.0, 1.2, 2.65, 3.45, 5.13, 6.5]),
}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_BONES = list(mesh_data['bones'])
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_REST_M = [__import__('mathutils').Matrix(m.tolist()) for m in AU_REST]

CHAIN = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l']


def split(q, axis):
    """signed twist about axis, and the remaining swing angle"""
    if q.angle < 1e-9:
        return 0.0, 0.0
    a = Vector(q.axis)
    if q.w < 0:
        a = -a
    dot = max(-1.0, min(1.0, a.dot(axis)))
    twist = math.degrees(q.angle) * dot
    swing = math.degrees(q.angle) * math.sqrt(max(0.0, 1.0 - dot * dot))
    return twist, swing


rows = {}
literal = {}
for key, (blend, action_name, fps, times) in CLIPS.items():
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = fps
    rows[key] = []
    literal[key] = []
    for sec in times:
        frame = int(round(sec * fps))
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        d = {}
        for n in AU_BONES:
            d[n] = rig.pose.bones[n].matrix @ AU_REST_M[AU_BONES.index(n)].inverted()
        s = rig.pose.bones['upperarm_l'].matrix.translation
        e = rig.pose.bones['lowerarm_l'].matrix.translation
        w = rig.pose.bones['hand_l'].matrix.translation
        u = (e - s).normalized()
        f = (w - e).normalized()
        bend = math.degrees(u.angle(f))

        def rel(a, b, axis):
            q = (d[a].to_3x3().inverted() @ d[b].to_3x3()).to_quaternion()
            if q.w < 0:
                q.negate()
            return split(q, axis)

        row = {'seconds': sec, 'frame': frame, 'bend_deg': round(bend, 1)}
        pairs = [
            ('up_up01', 'upperarm_l', 'upperarm_twist_01_l', u),
            ('up01_up02', 'upperarm_twist_01_l', 'upperarm_twist_02_l', u),
            ('up_up02', 'upperarm_l', 'upperarm_twist_02_l', u),
            ('up02_lo', 'upperarm_twist_02_l', 'lowerarm_l', f),
            ('lo_lo02', 'lowerarm_l', 'lowerarm_twist_02_l', f),
            ('lo02_lo01', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', f),
            ('lo01_hand', 'lowerarm_twist_01_l', 'hand_l', f),
            ('up_lo', 'upperarm_l', 'lowerarm_l', f),
            ('up02_lo01', 'upperarm_twist_02_l', 'lowerarm_twist_01_l', f),
        ]
        for name, a, b, axis in pairs:
            tw, sw = rel(a, b, axis)
            row[name + '_twist'] = round(tw, 1)
            row[name + '_swing'] = round(sw, 1)
        rows[key].append(row)

        lit = {'seconds': sec}
        for n in CHAIN:
            q = rig.pose.bones[n].rotation_quaternion.copy()
            eul = q.to_euler('XYZ')
            lit[n] = {'quat': [round(v, 4) for v in q],
                      'euler_deg': [round(math.degrees(v), 1) for v in eul],
                      'loc': [round(v, 5) for v in rig.pose.bones[n].location]}
        literal[key].append(lit)

(HERE / 'elbow_axial.json').write_text(
    json.dumps({'relative': rows, 'literal': literal}, indent=2, ensure_ascii=False),
    encoding='utf-8')

for key in CLIPS:
    print('\n===== %s =====' % key)
    print('%6s %5s | %8s %9s | %9s %10s | %9s' % (
        'sec', 'bend', 'up02-lo', 'lo-lo02', 'lo02-lo01', 'lo01-hand', 'up02-lo01'))
    for r in rows[key]:
        print('%6.2f %5.1f | %8.1f %9.1f | %9.1f %10.1f | %9.1f' % (
            r['seconds'], r['bend_deg'], r['up02_lo_twist'], r['lo_lo02_twist'],
            r['lo02_lo01_twist'], r['lo01_hand_twist'], r['up02_lo01_twist']))
    print('-- swing components (should be ~0 for same-limb pairs) --')
    for r in rows[key][:4]:
        print('%6.2f  up02-lo %5.1f  lo-lo02 %5.1f  lo02-lo01 %5.1f  lo01-hand %5.1f' % (
            r['seconds'], r['up02_lo_swing'], r['lo_lo02_swing'],
            r['lo02_lo01_swing'], r['lo01_hand_swing']))
    print('-- literal local channels, first sample --')
    for n, v in literal[key][0].items():
        if n == 'seconds':
            continue
        print('   %-22s euler %s  loc %s' % (n, v['euler_deg'], v['loc']))
print('\nAXIAL_DONE')