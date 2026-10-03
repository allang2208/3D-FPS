"""Closest on-screen arm surface for the accepted M4 N quick melee (reference target)."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ASH12Fix20260925')
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
FRAMES = list(range(0, 55, 3))
BLEND = S / 'M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend'
ACTION = 'M4_QuickCombatRefineN_Base'
CAM = dict(eye=Vector((0.0, -0.10, 0.05)), right=Vector((1, 0, 0)),
           forward=Vector((0, 1, 0)), up=Vector((0, 0, 1)))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883

bpy.ops.wm.open_mainfile(filepath=str(BLEND), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[ACTION]
scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.type == 'MESH' and ob is not arms:
        ob.hide_viewport = True
        ob.hide_render = True
surface = SkinSurface(rig, arms)
eye = np.array([CAM['eye'].x, CAM['eye'].y, CAM['eye'].z])
right = np.array([1.0, 0, 0])
up = np.array([0, 0, 1.0])

rows = []
for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pts = surface.positions({b.name: b.matrix.copy() for b in rig.pose.bones})
    rel = pts - eye
    fwd, r, u = rel[:, 1], rel[:, 0], rel[:, 2]
    on = (fwd > 0.006) & (np.abs(r) <= TH75 * fwd) & (np.abs(u) <= TV75 * fwd)
    row = dict(frame=f, under15=int(((fwd > 0.006) & (fwd < 0.15) & on).sum()),
               under20=int(((fwd > 0.006) & (fwd < 0.20) & on).sum()))
    if on.any():
        i = int(np.flatnonzero(on)[int(np.argmin(fwd[on]))])
        row['closest'] = dict(forward_cm=round(float(fwd[i]) * 100, 1),
                              right_cm=round(float(r[i]) * 100, 1),
                              up_cm=round(float(u[i]) * 100, 1),
                              group=[str(surface.groups[i]), str(surface.sides[i])])
    else:
        row['closest'] = None
    rows.append(row)
(HERE / 'probe_m4_n.json').write_text(json.dumps(rows, indent=1))
for r in rows:
    print('M4N_CLOSE', r['frame'], r['closest'], 'under15', r['under15'], 'under20', r['under20'], flush=True)
