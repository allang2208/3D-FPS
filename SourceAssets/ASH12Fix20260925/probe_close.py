"""Name the closest on-screen arm vertices (either side) in an authored clip."""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
BLEND, ACTION, SIDE = ARGS[0], ARGS[1], ARGS[2]
FRAMES = [int(v) for v in ARGS[3:]]
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883

bpy.ops.wm.open_mainfile(filepath=BLEND, use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[ACTION]
surface = SkinSurface(rig, arms)
rows = np.flatnonzero(surface.sides == SIDE)
for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    pts = surface.positions({b.name: b.matrix.copy() for b in rig.pose.bones})[rows]
    rel = pts - np.array([CAM.x, CAM.y, CAM.z])
    fwd, right, up = rel[:, 1], rel[:, 0], rel[:, 2]
    on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    order = np.flatnonzero(on)[np.argsort(fwd[on])][:8]
    print('CLOSE', SIDE, f, 'min_cm', round(float(fwd[on].min()) * 100, 1) if on.any() else None, flush=True)
    for i in order:
        print('   ', round(float(fwd[i]) * 100, 1), 'cm  pos', [round(float(v) * 100, 1) for v in rel[i]],
              'group', str(surface.groups[rows[i]]), flush=True)
