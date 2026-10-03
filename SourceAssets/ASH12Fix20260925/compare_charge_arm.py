"""Compare the right arm during the charging phase: pre-modification vs current.

Reports the elbow angle (180 deg = straight), the arm's camera-space placement and
the near-field clearance, so "straight arm, as before the modification" can be
matched deliberately instead of guessed.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
# Superseded rounds (camera-guard, straight-arm, connected-arm, unguarded original-arm) are
# retired to the task archive; see trash/ash12-reload-melee-superseded-20260925/MANIFEST.md.
ARCHIVE = HERE.parents[1] / 'trash/ash12-reload-melee-superseded-20260925'
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
CASES = {
    'pre_reference': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                      'ASH12_Reference_reload_empty'),
    'current_fixed': (ARCHIVE / 'Blends/ASH12_ReloadEmpty_CameraGuard.blend',
                      'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'current_fixed_bak': (HERE / 'Before/Weapons/ASH12/ReloadReference20260919/A_ASH12_reload_empty.uasset',
                          None),
    'straight': (ARCHIVE / 'Blends/ASH12_ReloadEmpty_CameraGuard_StraightArm.blend',
                 'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'connect': (ARCHIVE / 'Blends/ASH12_ReloadEmpty_ConnectedArm.blend',
                'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'rightedge': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                  'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'game_original': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                      'ASH12_reload_empty'),
    'original_arm': (HERE / 'Blends/ASH12_ReloadEmpty_OriginalArm_GuardedArm.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn'),
    'idle': (S / 'ASH1220260917/ASH12_Editable.blend', 'ASH12_idle'),
    'reload': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
               'ASH12_reload'),
    'ref_reload': (S / 'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',
                   'ASH12_Reference_reload'),
}
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KEYS = [c for c in ARGS if c in CASES] or ['pre_reference', 'current_fixed']
FRAMES = [int(v) for v in ARGS if v.lstrip('-').isdigit()]
if not FRAMES:
    FRAMES = list(range(0, 199, 6))


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
    rows_r = np.flatnonzero(surface.sides == 'r')
    print('====', key, action, flush=True)
    for f in FRAMES:
        rig.animation_data.action = act
        rig.animation_data.action_slot = act.slots[0]
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        A = pose['upperarm_r'].translation
        E = pose['lowerarm_r'].translation
        T = pose['hand_r'].translation
        u = (E - A).normalized()
        v = (T - E).normalized()
        elbow = math.degrees(math.acos(max(-1.0, min(1.0, u.dot(v)))))
        reach = (T - A).length * 100
        limit = ((E - A).length + (T - E).length) * 100
        pts = surface.positions(pose)[rows_r] - np.array([CAM.x, CAM.y, CAM.z])
        fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
        on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
        depth = round(float(fwd[on].min()) * 100, 1) if on.any() else None
        eye = round(float(np.linalg.norm(pts[on], axis=1).min()) * 100, 1) if on.any() else None
        print('ARM', key, f, 'elbow_deg', round(elbow, 1), 'shoulder->hand_cm', round(reach, 1),
              'limit_cm', round(limit, 1), 'shoulder', cs(A), 'hand', cs(T), 'elbow', cs(E),
              'gun', cs(pose['ik_hand_gun'].translation) if 'ik_hand_gun' in pose else None,
              'closest_cm', depth, 'eye_cm', eye, flush=True)
