"""Verify every ASH-12 camera-guard clip against its source in one table."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
BONDS = {
    'reload_empty': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn', 198),
    'quick_melee': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base', 54),
}
JOBS = {
    'base/reload_empty': (BONDS['reload_empty'],
                          HERE / 'Blends/ASH12_ReloadEmpty_OriginalArm_GuardedArm.blend'),
    'base/quick_melee': (BONDS['quick_melee'],
                         HERE / 'Blends/ASH12_QuickCombat_Base_PlaneArm.blend'),
}
for family in ('vertical', 'canted', 'prism', 'angled'):
    JOBS[f'{family}/reload_empty'] = (
        (S / f'ASH12UniversalAttachments20260919/ASH12_{family}_Grips_Editable.blend',
         f'ASH12_{family}_reload_empty', 198),
        HERE / f'Blends/ASH12_{family}_ReloadEmpty_OriginalArm_GuardedArm.blend')
    JOBS[f'{family}/quick_melee'] = (
        (S / f'ASH12UniversalAttachments20260919/ASH12_{family}_Grips_Editable.blend',
         f'ASH12_{family}_QuickCombat', 54),
        HERE / f'Blends/ASH12_{family}_QuickCombat_PlaneArm.blend')
# Superseded rounds (camera-guard, straight-arm, connected-arm) are retired to
# trash/ash12-reload-melee-superseded-20260925/; this table always checks what ships.


def sample(blend, action_name, frames):
    bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    act = bpy.data.actions[action_name]
    poses = []
    for f in range(frames + 1):
        rig.animation_data.action = act
        rig.animation_data.action_slot = act.slots[0]
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        poses.append({b.name: b.matrix.copy() for b in rig.pose.bones})
    return poses, SkinSurface(rig, arms)


def probe(surface, pose, rows):
    pts = surface.positions(pose)[rows] - np.array([CAM.x, CAM.y, CAM.z])
    fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
    on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    return float(fwd[on].min()) if on.any() else None


summary = {}
for key, ((src_blend, action, frames), fixed_blend) in JOBS.items():
    src, _ = sample(src_blend, action, frames)
    dst, surface = sample(fixed_blend, action, frames)
    rows_r = np.flatnonzero(surface.sides == 'r')
    rows_l = np.flatnonzero(surface.sides == 'l')
    before_r = min((probe(surface, p, rows_r) or 9.9) for p in src)
    after_r = min((probe(surface, p, rows_r) or 9.9) for p in dst)
    after_l = min((probe(surface, p, rows_l) or 9.9) for p in dst)
    before_l = min((probe(surface, p, rows_l) or 9.9) for p in src)
    worst_len = max(max(abs((dst[f][f'lowerarm_{s}'].translation - dst[f][f'upperarm_{s}'].translation).length
                           - (src[f][f'lowerarm_{s}'].translation - src[f][f'upperarm_{s}'].translation).length),
                       abs((dst[f][f'hand_{s}'].translation - dst[f][f'lowerarm_{s}'].translation).length
                           - (src[f][f'hand_{s}'].translation - src[f][f'lowerarm_{s}'].translation).length))
                   for f in range(frames + 1) for s in ('l', 'r'))
    worst_hand = max(max((dst[f][f'hand_{s}'].translation - src[f][f'hand_{s}'].translation).length
                         for s in ('l', 'r')) for f in range(frames + 1))
    # Weapon-relative grip check: the melee family repair moves weapon and hands
    # together, so the grips must be identical in the receiver's own space.
    worst_grip = 0.0
    for f in range(frames + 1):
        for s in ('l', 'r'):
            a = src[f]['WPN_root'].inverted() @ src[f][f'hand_{s}'].translation
            b = dst[f]['WPN_root'].inverted() @ dst[f][f'hand_{s}'].translation
            worst_grip = max(worst_grip, (a - b).length)
    # Right-elbow bend during the window: 0 deg = straight limb.
    bend_src, bend_dst = [], []
    for f in range(frames + 1):
        for pose, store in ((src[f], bend_src), (dst[f], bend_dst)):
            A = pose['upperarm_r'].translation
            E = pose['lowerarm_r'].translation
            T = pose['hand_r'].translation
            store.append(math.degrees(math.acos(max(-1.0, min(1.0,
                (E - A).normalized().dot((T - E).normalized()))))))
    summary[key] = dict(frames=frames,
                        before_right_cm=round(before_r * 100, 1), after_right_cm=round(after_r * 100, 1),
                        before_left_cm=round(before_l * 100, 1), after_left_cm=round(after_l * 100, 1),
                        hand_delta_mm=round(worst_hand * 1000, 4),
                        grip_delta_mm=round(worst_grip * 1000, 4),
                        bone_delta_mm=round(worst_len * 1000, 6),
                        elbow_min_deg_src=round(min(bend_src), 1),
                        elbow_min_deg_dst=round(min(bend_dst), 1))
    print('QA', key, json.dumps(summary[key]), flush=True)
(HERE / 'verify_all.json').write_text(json.dumps(summary, indent=2))
print('QA_DONE', len(summary), flush=True)
