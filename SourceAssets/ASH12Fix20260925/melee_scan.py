"""Scan an ASH-12 quick-melee clip frame by frame from the true action camera anchor.

Reports, per frame: the closest distance from the eye to visible right/left arm skin, the
closest in-frame forward depth, how many arm vertices sit inside 20 cm, the arm-root and
weapon positions in camera space, and the elbow bends. Per-frame jumps of the arm roots and
the weapon are printed separately, because "闪动" (flicker) in a first-person clip is almost
always a one-frame parameter switch rather than bad skinning.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
NEAR = 0.20
CASES = {
    'src_base': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                 'ASH12_QuickCombat_N_Base'),
    'cur_base': (HERE / 'Blends/ASH12_QuickCombat_Base_PlaneArm.blend',
                 'ASH12_QuickCombat_N_Base'),
}
for family in ('vertical', 'canted', 'prism', 'angled'):
    CASES[f'src_{family}'] = (S / f'ASH12UniversalAttachments20260919/ASH12_{family}_Grips_Editable.blend',
                              f'ASH12_{family}_QuickCombat')
    CASES[f'cur_{family}'] = (HERE / f'Blends/ASH12_{family}_QuickCombat_PlaneArm.blend',
                              f'ASH12_{family}_QuickCombat')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KEYS = [a for a in ARGS if a in CASES] or ['src_base', 'cur_base']
FRAMES = 54


def cs(p):
    d = Vector(p) - CAM
    return [round(d.x * 100, 1), round(d.y * 100, 1), round(d.z * 100, 1)]


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
    rows = {'r': np.flatnonzero(surface.sides == 'r'), 'l': np.flatnonzero(surface.sides == 'l')}
    print('====', key, action, flush=True)
    prev = None
    rows_out = []
    for f in range(FRAMES + 1):
        rig.animation_data.action = act
        rig.animation_data.action_slot = act.slots[0]
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        pts = surface.positions(pose) - np.array([CAM.x, CAM.y, CAM.z])
        fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
        on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
        rec = dict(f=f)
        for side in ('r', 'l'):
            m = on[rows[side]]
            sub = pts[rows[side]][m]
            rec[f'{side}_eye'] = None if not m.any() else round(float(np.linalg.norm(sub, axis=1).min()) * 100, 1)
            rec[f'{side}_depth'] = None if not m.any() else round(float(sub[:, 1].min()) * 100, 1)
            rec[f'{side}_near20'] = int(((fwd[rows[side]] > 0.006) & (fwd[rows[side]] < NEAR) & on[rows[side]]).sum())
        for name in ('upperarm_r', 'hand_r', 'upperarm_l', 'hand_l', 'WPN_root'):
            rec[name] = cs(pose[name].translation)
        for side in ('r', 'l'):
            A = pose[f'upperarm_{side}'].translation
            E = pose[f'lowerarm_{side}'].translation
            T = pose[f'hand_{side}'].translation
            rec[f'elbow_{side}'] = round(math.degrees(math.acos(max(-1.0, min(1.0,
                (E - A).normalized().dot((T - E).normalized()))))), 1)
        rec['jump_root_r'] = None if prev is None else round((Vector(rec['upperarm_r']) - Vector(prev['upperarm_r'])).length, 2)
        rec['jump_root_l'] = None if prev is None else round((Vector(rec['upperarm_l']) - Vector(prev['upperarm_l'])).length, 2)
        rec['jump_gun'] = None if prev is None else round((Vector(rec['WPN_root']) - Vector(prev['WPN_root'])).length, 2)
        rows_out.append(rec)
        prev = rec
    for rec in rows_out:
        print('MELEE', key, json.dumps(rec), flush=True)
    worst = sorted((r['r_eye'] if r['r_eye'] is not None else 999, r['f']) for r in rows_out)[:5]
    worstl = sorted((r['l_eye'] if r['l_eye'] is not None else 999, r['f']) for r in rows_out)[:5]
    jumps = sorted(((r['jump_root_r'] or 0), r['f']) for r in rows_out)[-6:]
    jumpsl = sorted(((r['jump_root_l'] or 0), r['f']) for r in rows_out)[-6:]
    jumpsg = sorted(((r['jump_gun'] or 0), r['f']) for r in rows_out)[-6:]
    print('WORST', key, 'right_eye', worst, 'left_eye', worstl, flush=True)
    print('JUMP', key, 'root_r', jumps, 'root_l', jumpsl, 'gun', jumpsg, flush=True)
