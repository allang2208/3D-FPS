"""Name the support-arm vertices that sit closest to the camera in a given clip.

Reads a blend + armature action, evaluates the actual skinned surface and prints the
on-screen vertices with the smallest camera depth together with the bones that drive
them, so a remaining near-camera offender is identified instead of guessed.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
BLEND = ARGS[0]
ACTION = ARGS[1]
FRAMES = [int(v) for v in ARGS[2:]]
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883

bpy.ops.wm.open_mainfile(filepath=BLEND, use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
act = bpy.data.actions[ACTION]
scene = bpy.context.scene
armour = {b.name: b.matrix_local.copy() for b in rig.data.bones}
left = {arms.vertex_groups[n].index: n for n in (g.name for g in arms.vertex_groups) if n.endswith('_l')}
mesh_left = {}
for v in arms.data.vertices:
    pairs = [(left[g.group], g.weight) for g in v.groups if g.group in left and g.weight > 1e-6]
    if pairs:
        total = sum(w for _, w in pairs)
        mesh_left[v.index] = sorted(((n, w / total) for n, w in pairs), key=lambda p: -p[1])

for f in FRAMES:
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arms.evaluated_get(dg)
    mw = ev.matrix_world
    rows = []
    for i, weights in mesh_left.items():
        p = (mw @ ev.data.vertices[i].co) - CAM
        if p.y <= 0.006 or abs(p.x) > TH75 * p.y or abs(p.z) > TV75 * p.y:
            continue
        rows.append((p.y, i, p, weights))
    rows.sort()
    print('FRAME', f, 'onscreen_left_vertices', len(rows), flush=True)
    for depth, i, p, weights in rows[:12]:
        print(f'   v{i:6d} depth_mm {depth*1000:7.1f} pos_cm '
              f'{[round(v*100,1) for v in p]} weights {[(n, round(w,3)) for n, w in weights[:4]]}', flush=True)
