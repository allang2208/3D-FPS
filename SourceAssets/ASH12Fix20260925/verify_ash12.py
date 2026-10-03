"""Verify an authored ASH-12 clip against its source: lengths, hands, camera clearance."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

CLIP = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'reload_empty'
ARCHIVE = HERE.parents[1] / 'trash/ash12-reload-melee-superseded-20260925'
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
SPEC = {
    'reload_empty': (HERE.parent / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn',
                     HERE / 'Blends/ASH12_ReloadEmpty_OriginalArm_GuardedArm.blend', 198),
    'quick_melee': (HERE.parent / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                    'ASH12_QuickCombat_N_Base',
                    HERE / 'Blends/ASH12_QuickCombat_Base_PlaneArm.blend', 54),
    'reload_empty_v1': (HERE.parent / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                        'ASH12_EmptyReload_RightEdgeReachPullReturn',
                        ARCHIVE / 'Blends/ASH12_ReloadEmpty_CameraGuard.blend', 198),
    'quick_melee_v1': (HERE.parent / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                       'ASH12_QuickCombat_N_Base',
                       ARCHIVE / 'Blends/ASH12_QuickCombat_Base_CameraGuard.blend', 54),
}
src_blend, action, fixed_blend, frames = SPEC[CLIP]


def sample(blend, action_name):
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
    surface = SkinSurface(rig, arms)
    return poses, surface


src, _ = sample(src_blend, action)
dst, surface = sample(fixed_blend, action)
rows_r = np.flatnonzero(surface.sides == 'r')
rows_l = np.flatnonzero(surface.sides == 'l')


def probe(pose, rows):
    pts = surface.positions(pose)[rows] - np.array([CAM.x, CAM.y, CAM.z])
    fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
    on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    return (float(fwd[on].min()) if on.any() else None,
            int(((fwd > 0.006) & (fwd < 0.20) & on).sum()))


worst_len = 0.0
worst_hand = 0.0
for f in range(frames + 1):
    for side in ('l', 'r'):
        un, fn, hn = f'upperarm_{side}', f'lowerarm_{side}', f'hand_{side}'
        worst_len = max(worst_len,
                        abs((dst[f][fn].translation - dst[f][un].translation).length - 0.27771),
                        abs((dst[f][hn].translation - dst[f][fn].translation).length - 0.27251))
    worst_hand = max(worst_hand,
                     (dst[f]['hand_l'].translation - src[f]['hand_l'].translation).length,
                     (dst[f]['hand_r'].translation - src[f]['hand_r'].translation).length)

print('VERIFY', CLIP, 'max_bone_len_error_mm', round(worst_len * 1000, 4),
      'max_hand_delta_mm', round(worst_hand * 1000, 4), flush=True)
out = []
for f in range(frames + 1):
    if f % 2 and f not in (0, frames):
        continue
    a = probe(src[f], rows_r)
    b = probe(dst[f], rows_r)
    c = probe(dst[f], rows_l)
    out.append(dict(frame=f, src_r=None if a[0] is None else round(a[0] * 100, 1),
                    dst_r=None if b[0] is None else round(b[0] * 100, 1),
                    dst_l=None if c[0] is None else round(c[0] * 100, 1),
                    under20=b[1]))
    if (a[0] or 9.9) < 0.16 or (b[0] or 9.9) < 0.13:
        print('  frame', f, 'src_r', out[-1]['src_r'], 'dst_r', out[-1]['dst_r'],
              'dst_l', out[-1]['dst_l'], 'under20', b[1], flush=True)
(HERE / f'verify_{CLIP}.json').write_text(json.dumps(out, indent=1))
mins_src = min(v['src_r'] for v in out if v['src_r'] is not None)
mins_dst = min(v['dst_r'] for v in out if v['dst_r'] is not None)
mins_dst_l = min(v['dst_l'] for v in out if v['dst_l'] is not None)
print('VERIFY_MIN', CLIP, 'src_right_cm', mins_src, 'dst_right_cm', mins_dst,
      'dst_left_cm', mins_dst_l, flush=True)
