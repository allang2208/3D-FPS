"""Left hand lowering pose and trajectory: PKM against the rifle references.

Frame-independent measurements only, so rigs of different sizes are comparable:
where the hand sits relative to the clavicle, and how the upper arm / forearm are
oriented.  That is what "the left hand goes down" means physically.
"""
import json
import math
import re
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
PKM = ROOT / 'PKMLowpoly20260922'

CASES = [
    ('PKM enter', PKM / 'Elbow41' / 'Edit' / 'PKM_sprint_enter_Elbow41.blend',
     'PKM_sprint_enter_Elbow41'),
    ('PKM loop', PKM / 'Elbow41' / 'Edit' / 'PKM_sprint_loop_Elbow41.blend',
     'PKM_sprint_loop_Elbow41'),
    ('PKM exit', PKM / 'Elbow41' / 'Edit' / 'PKM_sprint_exit_Elbow41.blend',
     'PKM_sprint_exit_Elbow41'),
    ('M4 enter', ROOT / 'M4TacticalSprint20260915' / 'Base' / 'M4_TacticalSprint_Base_Editable.blend',
     'M4_TacticalSprint_Base_Enter'),
    ('M4 loop', ROOT / 'M4TacticalSprint20260915' / 'Base' / 'M4_TacticalSprint_Base_Editable.blend',
     'M4_TacticalSprint_Base_Loop'),
    ('M4 exit', ROOT / 'M4TacticalSprint20260915' / 'Base' / 'M4_TacticalSprint_Base_Editable.blend',
     'M4_TacticalSprint_Base_Exit'),
    ('AKM enter', ROOT / 'RifleTacticalSprint20260915' / 'AKM' / 'Base' / 'AKM_TacticalSprint_Base_Editable.blend',
     'AKM_TacticalSprint_Base_Enter'),
    ('AKM loop', ROOT / 'RifleTacticalSprint20260915' / 'AKM' / 'Base' / 'AKM_TacticalSprint_Base_Editable.blend',
     'AKM_TacticalSprint_Base_Loop'),
    ('ASH12 enter', ROOT / 'ASH12TacticalSprint20260919' / 'ASH12_TacticalSprint_Editable.blend',
     'ASH12_TacticalSprint_Enter'),
    ('ASH12 loop', ROOT / 'ASH12TacticalSprint20260919' / 'ASH12_TacticalSprint_Editable.blend',
     'ASH12_TacticalSprint_Loop'),
]


def action_bones(act):
    """Bone names the action actually keys."""
    names = set()
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    m = re.match(r'pose\.bones\["([^"]+)"\]', fc.data_path)
                    if m:
                        names.add(m.group(1))
    return names


def pick_rig(act):
    """The armature the action was authored on, by fcurve path match."""
    keyed = action_bones(act)
    best, score = None, -1
    for o in bpy.data.objects:
        if o.type != 'ARMATURE':
            continue
        names = {b.name for b in o.data.bones}
        s = len(keyed & names)
        if s > score:
            best, score = o, s
    return best, score, len(keyed)


rows = {}
current = None
for tag, blend, action_name in CASES:
    if current != blend:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        current = blend
    scene = bpy.context.scene
    act = bpy.data.actions[action_name]
    rig, score, nkeys = pick_rig(act)
    print('\n=== %-12s %s ===' % (tag, action_name))
    print('  rig %s  matched %d/%d keyed bones' % (rig.name, score, nkeys))
    rig.animation_data_create()
    rig.animation_data.action = act
    if act.slots:
        rig.animation_data.action_slot = act.slots[0]
    start, end = map(int, act.frame_range)
    fps = scene.render.fps

    samples = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pb = rig.pose.bones
        clav = np.array(pb['clavicle_l'].matrix.translation)
        sh = np.array(pb['upperarm_l'].matrix.translation)
        el = np.array(pb['lowerarm_l'].matrix.translation)
        wr = np.array(pb['hand_l'].matrix.translation)
        hand_r = np.array(pb['hand_r'].matrix.translation)
        u = el - sh
        f = wr - el
        bend = math.degrees(math.acos(max(-1, min(1, float(
            (u / np.linalg.norm(u)) @ (f / np.linalg.norm(f)))))))
        fwd = np.array([0.0, 1.0, 0.0])
        ua = math.degrees(math.acos(max(-1, min(1, float(
            (u / np.linalg.norm(u)) @ fwd)))))
        fa = math.degrees(math.acos(max(-1, min(1, float(
            (f / np.linalg.norm(f)) @ fwd)))))
        samples.append({
            'frame': frame, 't': (frame - start) / max(1, (end - start)),
            'reach': float(np.linalg.norm(wr - clav)),
            'hand_rel': (wr - clav).tolist(),
            'bend': bend, 'upper_vs_fwd': ua, 'fore_vs_fwd': fa,
            'hand_l_y_hand_r': float(wr[1] - hand_r[1]),
        })
    rows[tag] = {'blend': blend.name, 'action': action_name, 'fps': fps,
                 'rig': rig.name, 'frames': end - start + 1, 'samples': samples}

    moved = max(float(np.abs(np.array(s['hand_rel']) - np.array(samples[0]['hand_rel'])).max())
                for s in samples)
    print('  %d frames @ %d fps (%.2f s)  max hand travel %.1f cm'
          % (end - start + 1, fps, (end - start) / fps, moved * 100))
    print('   t     reach_cm   bend    upper/fwd  fore/fwd   hand rel clavicle (cm)')
    step = max(1, (end - start) // 8)
    for s in samples[::step] + [samples[-1]]:
        h = [v * 100 for v in s['hand_rel']]
        print('  %.2f   %7.1f  %6.1f    %6.1f    %6.1f    (%6.1f, %6.1f, %6.1f)'
              % (s['t'], s['reach'] * 100, s['bend'], s['upper_vs_fwd'],
                 s['fore_vs_fwd'], h[0], h[1], h[2]))

out = PKM / 'Sprint43'
out.mkdir(parents=True, exist_ok=True)
(out / 'sprint_pose.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')

print('\n=== summary: start -> end of the lowering ===')
print('  %-12s  reach_cm        bend          upper/fwd     fore/fwd' % 'clip')
for tag, r in rows.items():
    s0, s1 = r['samples'][0], r['samples'][-1]
    mid = r['samples'][len(r['samples']) // 2]
    print('  %-12s  %5.1f->%5.1f (%5.1f)  %5.1f->%5.1f  %5.1f->%5.1f  %5.1f->%5.1f'
          % (tag, s0['reach'] * 100, s1['reach'] * 100, mid['reach'] * 100,
             s0['bend'], s1['bend'], s0['upper_vs_fwd'], s1['upper_vs_fwd'],
             s0['fore_vs_fwd'], s1['fore_vs_fwd']))
print('\nSPRINT_POSE_DONE')