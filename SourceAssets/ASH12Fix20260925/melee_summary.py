"""Compact per-clip diagnostic table for the ASH-12 quick-melee clips.

For every clip it prints the worst eye-to-skin distances, the largest one-frame arm-root
jump (flicker), the reach ratio |shoulder->wrist| / (upperarm+forearm) with the frames it
saturates (the arm is then locked straight and the wrist is pulled off the solved chain),
and the elbow ranges. Source and shipped versions are printed side by side.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
FRAMES = 54
CASES = {
    'src_base': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                 'ASH12_QuickCombat_N_Base'),
    'cur_base': (HERE / 'Blends/ASH12_QuickCombat_Base_PlaneArm.blend', 'ASH12_QuickCombat_N_Base'),
}
for family in ('vertical', 'canted', 'prism', 'angled'):
    CASES[f'src_{family}'] = (S / f'ASH12UniversalAttachments20260919/ASH12_{family}_Grips_Editable.blend',
                              f'ASH12_{family}_QuickCombat')
    CASES[f'cur_{family}'] = (HERE / f'Blends/ASH12_{family}_QuickCombat_PlaneArm.blend',
                              f'ASH12_{family}_QuickCombat')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KEYS = [a for a in ARGS if a in CASES] or list(CASES)


def rows_of(pose):
    return {}


for key in KEYS:
    blend, action = CASES[key]
    bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    act = bpy.data.actions[action]
    for ob in list(bpy.context.scene.objects):
        if ob.type == 'MESH' and ob is not arms:
            ob.hide_viewport = True
            ob.hide_render = True
    surface = SkinSurface(rig, arms)
    rr = {s: np.flatnonzero(surface.sides == s) for s in ('r', 'l')}
    eye = {s: [] for s in ('r', 'l')}
    depth = {s: [] for s in ('r', 'l')}
    near20 = {s: [] for s in ('r', 'l')}
    elbow = {s: [] for s in ('r', 'l')}
    ratio = {s: [] for s in ('r', 'l')}
    root, gun = [], []
    for f in range(FRAMES + 1):
        rig.animation_data.action = act
        rig.animation_data.action_slot = act.slots[0]
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        pts = surface.positions(pose) - np.array([CAM.x, CAM.y, CAM.z])
        fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
        on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
        for s in ('r', 'l'):
            m = on[rr[s]]
            sub = pts[rr[s]][m]
            eye[s].append(None if not m.any() else float(np.linalg.norm(sub, axis=1).min()))
            depth[s].append(None if not m.any() else float(sub[:, 1].min()))
            near20[s].append(int(((fwd[rr[s]] > 0.006) & (fwd[rr[s]] < 0.20) & on[rr[s]]).sum()))
            A = pose[f'upperarm_{s}'].translation
            E = pose[f'lowerarm_{s}'].translation
            T = pose[f'hand_{s}'].translation
            l1 = (E - A).length
            l2 = (T - E).length
            elbow[s].append(math.degrees(math.acos(max(-1.0, min(1.0, (E - A).normalized().dot((T - E).normalized()))))))
            ratio[s].append((T - A).length / (l1 + l2))
        root.append(pose['upperarm_r'].translation.copy())
        gun.append(pose['WPN_root'].translation.copy())
    jump_r = max((root[i] - root[i - 1]).length for i in range(1, FRAMES + 1)) * 100
    jump_g = max((gun[i] - gun[i - 1]).length for i in range(1, FRAMES + 1)) * 100
    jf = max(range(1, FRAMES + 1), key=lambda i: (root[i] - root[i - 1]).length)
    clamped = {s: [f for f in range(FRAMES + 1) if ratio[s][f] > 0.985] for s in ('r', 'l')}
    frozen = {s: [f for f in range(FRAMES + 1) if elbow[s][f] < 15] for s in ('r', 'l')}
    bad = {s: [(f, round(eye[s][f] * 100, 1)) for f in range(FRAMES + 1)
               if eye[s][f] is not None and eye[s][f] < 0.15] for s in ('r', 'l')}
    print('SUM', key,
          'bad_r_eye_cm', bad['r'], flush=True)
    print('SUM', key,
          'bad_l_eye_cm', bad['l'], flush=True)
    print('SUM', key,
          'eye_r', round(min(v for v in eye['r'] if v is not None) * 100, 1),
          'eye_l', round(min(v for v in eye['l'] if v is not None) * 100, 1),
          'depth_r', round(min(v for v in depth['r'] if v is not None) * 100, 1),
          'depth_l', round(min(v for v in depth['l'] if v is not None) * 100, 1),
          'near20_r', max(near20['r']), 'near20_l', max(near20['l']),
          'elbow_r', [round(min(elbow['r']), 1), round(max(elbow['r']), 1)],
          'elbow_l', [round(min(elbow['l']), 1), round(max(elbow['l']), 1)],
          'ratio_max', [round(max(ratio['r']), 3), round(max(ratio['l']), 3)],
          'clamped_r', clamped['r'][:12], 'clamped_l', clamped['l'][:12],
          'straight_frames_r', frozen['r'][:12], 'straight_frames_l', frozen['l'][:12],
          'root_jump_cm', round(jump_r, 2), '@f', jf, 'gun_jump_cm', round(jump_g, 2), flush=True)
