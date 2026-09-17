"""Per-frame motion profile of the authored clip.

The reference video can be measured frame by frame (mean absolute difference),
so the authored clip needs the same shape to be compared with it: how much the
hands, the magazine and the receiver actually move each frame. A clip whose
motion comes in short bursts separated by holds reads as "too fast" even when
its total length matches, because the eye compares the bursts, not the total.

Run: blender --background --factory-startup --python-exit-code 1 --python measure_pacing.py
"""
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
WATCH = ("hand_l", "hand_r", "WPN_root", "WPN_SOCKET_Magazine", "WPN_ChargingHandle", "WPN_bolt")

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
if not rig.animation_data:
    rig.animation_data_create()
action = bpy.data.actions["ASH12_reload_empty"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]


def sample(frame):
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {name: rig.pose.bones[name].matrix.translation.copy() for name in WATCH}


steps = [i * 0.5 for i in range(325)]
previous = sample(0.0)
rows = []
for frame in steps[1:]:
    pose = sample(frame)
    moved = sum((pose[name] - previous[name]).length for name in WATCH)
    rows.append((frame, moved))
    previous = pose

peak = max(m for _, m in rows)
print("\n=== ASH12_reload_empty motion profile (peak %.4f m/frame) ===" % peak)
for index in range(0, len(rows), 4):          # every 2 frames
    frame, moved = rows[index]
    bar = "#" * int(40.0 * moved / peak)
    print("  f=%5.1f %5.1f%%  %.4f  %s" % (frame, 100.0 * moved / peak, moved, bar))

# Where the quiet stretches are: frames under a tenth of the peak.
quiet = [frame for frame, moved in rows if moved < 0.10 * peak]
if quiet:
    runs = []
    start = quiet[0]
    for a, b in zip(quiet, quiet[1:]):
        if b - a > 1.0:
            runs.append((start, a))
            start = b
    runs.append((start, quiet[-1]))
    print("\n  quiet stretches (under 10%% of peak): %s"
          % ", ".join("f%.0f-f%.0f (%.2f s)" % (a, b, (b - a) / 60.0) for a, b in runs if b - a > 2.0))

print("\nASH12_PACING_COMPLETE")
