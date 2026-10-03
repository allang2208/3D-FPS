"""Are any left-arm bones scaled (squash/stretch) during the sprint clips?

Linear-blend rigidity says nothing about a bone that is simply SCALED: a finger vertex
100% on one bone moves perfectly rigidly (metric 0) and still looks stretched if that
bone carries a scale.  Check the actual bone scales, and the axis of the wrist
relative rotation.
"""
import importlib.util
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

CHAIN = ['clavicle_l', 'upperarm_l', 'upperarm_twist_02_l', 'upperarm_twist_01_l',
         'lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l',
         'thumb_01_l', 'thumb_02_l', 'thumb_03_l', 'index_01_l', 'index_02_l',
         'index_03_l', 'middle_01_l', 'middle_02_l', 'middle_03_l',
         'ring_01_l', 'ring_02_l', 'ring_03_l', 'pinky_01_l', 'pinky_02_l', 'pinky_03_l']

CASES = (
    ('idle', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend', 'PKM_Game_idle', 60),
    ('sprint_enter original', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_enter', 120),
    ('sprint_enter s44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
     'PKM_sprint_enter_Sprint44', 120),
    ('sprint_loop s44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_loop_Sprint44.blend',
     'PKM_sprint_loop_Sprint44', 120),
)

for tag, blend, action, fps in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = fps
    start, end = map(int, act.frame_range)
    worst = {}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for n in CHAIN:
            if n not in rig.pose.bones:
                continue
            s = np.array(rig.pose.bones[n].scale)
            dev = float(np.abs(s - 1.0).max())
            if dev > worst.get(n, (0.0, 0))[0]:
                worst[n] = (dev, frame, tuple(round(float(v), 4) for v in s))
    bad = {k: v for k, v in worst.items() if v[0] > 1e-3}
    print('\n%-22s frames %d..%d   bones with scale != 1: %d'
          % (tag, start, end, len(bad)))
    for k in sorted(bad, key=lambda k: -bad[k][0])[:8]:
        print('   %-22s max dev %.4f at f%d  scale %s' % (k, bad[k][0], bad[k][1], bad[k][2]))

# axis of the wrist relative rotation at the spike
print('\n--- wrist relative rotation axis, sprint_enter original ---')
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions['PKM17_base_sprint_enter']
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 120
for frame in (0, 3, 4, 5, 6, 9, 20):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    e = np.array(rig.pose.bones['lowerarm_l'].matrix.translation)
    w = np.array(rig.pose.bones['hand_l'].matrix.translation)
    f = (w - e) / np.linalg.norm(w - e)
    for n in ('lowerarm_l', 'lowerarm_twist_01_l'):
        Rh = np.array(rig.pose.bones['hand_l'].matrix)[:3, :3]
        Rb = np.array(rig.pose.bones[n].matrix)[:3, :3]
        Ua, _, Va = np.linalg.svd(Rh)
        Ub, _, Vb = np.linalg.svd(Rb)
        R = (Ua @ Va).T @ (Ub @ Vb)
        c = max(-1.0, min(1.0, (np.trace(R) - 1.0) / 2.0))
        ang = np.degrees(np.arccos(c))
        ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
        nrm = np.linalg.norm(ax)
        axis = ax / nrm if nrm > 1e-9 else np.zeros(3)
        align = abs(float(axis @ f))
        print('  f%-3d hand vs %-20s angle %6.1f deg  axis·forearm %.3f'
              % (frame, n, ang, align))
print('\nBONE_SCALE_DONE')