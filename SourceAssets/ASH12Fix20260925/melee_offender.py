"""Point at the skin that comes closest to the eye: which bone owns it, and where it is.

The dominant-bone probe decides the fix: geometry owned by the hand/wrist cannot be moved
by touching the shoulder or the elbow pole, and shoulder-region skin cannot be moved by
moving the weapon.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
ARCHIVE = HERE.parents[1] / 'trash/ash12-reload-melee-superseded-20260925'
CAM = Vector((0.0, -0.10, 0.05))
CASES = {
    'src_base': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
                 'ASH12_QuickCombat_N_Base'),
    'cur_base': (HERE / 'Blends/ASH12_QuickCombat_Base_PlaneArm.blend', 'ASH12_QuickCombat_N_Base'),
    'old_base': (ARCHIVE / 'Blends/ASH12_QuickCombat_Base_CameraGuard.blend',
                 'ASH12_QuickCombat_N_Base'),
}
for family in ('vertical', 'canted', 'prism', 'angled'):
    CASES[f'src_{family}'] = (S / f'ASH12UniversalAttachments20260919/ASH12_{family}_Grips_Editable.blend',
                              f'ASH12_{family}_QuickCombat')
    CASES[f'cur_{family}'] = (HERE / f'Blends/ASH12_{family}_QuickCombat_PlaneArm.blend',
                              f'ASH12_{family}_QuickCombat')
    CASES[f'old_{family}'] = (ARCHIVE / f'Blends/ASH12_{family}_QuickCombat_CameraGuard.blend',
                              f'ASH12_{family}_QuickCombat')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KEY = ARGS[0]
FRAMES = [int(v) for v in ARGS[1:] if v.lstrip('-').isdigit()]
SIDE = next((a for a in ARGS[1:] if a in ('r', 'l')), 'l')

blend, action = CASES[KEY]
bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[action]
for ob in list(bpy.context.scene.objects):
    if ob.type == 'MESH' and ob is not arms:
        ob.hide_viewport = True
        ob.hide_render = True
surface = SkinSurface(rig, arms)
rows = np.flatnonzero(surface.sides == SIDE)

for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    pts = surface.positions(pose) - np.array([CAM.x, CAM.y, CAM.z])
    sub = pts[rows]
    fwd = sub[:, 1]
    on = fwd > 0.006
    dist = np.linalg.norm(sub, axis=1)
    dist = np.where(on, dist, 1e9)
    order = np.argsort(dist)[:12]
    print('OFFENDER', KEY, f, 'side', SIDE, flush=True)
    for i in order:
        v = int(rows[i])
        group, side = surface.group_of(i)
        weights = []
        for name, (ids, coords, w) in surface.by_bone.items():
            hit = np.flatnonzero(ids == v)
            if hit.size:
                weights.append((name, round(float(w[hit[0]]), 3)))
        weights.sort(key=lambda kv: -kv[1])
        print('PT', f, 'vert', v, 'group', group, 'cam_cm', [round(float(x) * 100, 1) for x in sub[i]],
              'dist_cm', round(float(dist[i]) * 100, 1), 'weights', weights[:3], flush=True)
