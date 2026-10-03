"""Where is everything, really. Read-only debug dump."""
import json
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow39'

SRC = ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SRC))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
rig.animation_data.action = bpy.data.actions['PKM_Game_idle_Wrist12']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()

report = {'rig_world': [[round(v, 5) for v in r] for r in rig.matrix_world],
          'rig_scale': [round(v, 6) for v in rig.matrix_world.to_scale()]}

report['pose_world'] = {}
for n in ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'):
    w = rig.matrix_world @ rig.pose.bones[n].matrix.translation
    report['pose_world'][n] = [round(v, 4) for v in w]

report['cameras'] = []
for ob in bpy.data.objects:
    if ob.type == 'CAMERA':
        report['cameras'].append({
            'name': ob.name,
            'lib': ob.library.filepath if ob.library else None,
            'loc': [round(v, 4) for v in ob.matrix_world.translation],
            'in_view_layer': ob.name in [o.name for o in bpy.context.view_layer.objects],
        })

report['arm_meshes'] = []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.library is not None:
        continue
    if len(ob.data.vertices) not in (20326, 48705):
        continue
    bb = [ob.matrix_world @ __import__('mathutils').Vector(c) for c in ob.bound_box]
    xs = [v.x for v in bb]
    ys = [v.y for v in bb]
    zs = [v.z for v in bb]
    report['arm_meshes'].append({
        'name': ob.name,
        'lib': None,
        'bounds': [[round(min(xs), 3), round(max(xs), 3)],
                   [round(min(ys), 3), round(max(ys), 3)],
                   [round(min(zs), 3), round(max(zs), 3)]],
        'scale': [round(s, 5) for s in ob.matrix_world.to_scale()],
        'mods': [(m.type, m.object.name if getattr(m, 'object', None) else None)
                 for m in ob.modifiers],
    })

for ob in bpy.data.objects:
    if ob.type == 'MESH':
        continue
    if ob.name in ('Camera',):
        continue

weapon = []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or 'PKM' not in ob.name:
        continue
    from mathutils import Vector
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [v.x for v in bb]
    zs = [v.z for v in bb]
    if 'Belt' in ob.name or 'Round' in ob.name:
        continue
    weapon.append([ob.name, round(min(xs), 3), round(max(xs), 3),
                   round(min(zs), 3), round(max(zs), 3)])
report['weapon_count'] = len(weapon)
report['weapon_sample'] = weapon[:8]

(OUT / 'scene_debug.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, indent=2, ensure_ascii=False))