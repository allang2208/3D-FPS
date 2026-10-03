"""Identify which arm mesh the authoring blend actually binds, and whether it
is a linked library object. Read-only."""
import json
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow39'
OUT.mkdir(parents=True, exist_ok=True)

SRC = ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend'
ARM_BONES = {'upperarm_l', 'lowerarm_l', 'hand_l', 'lowerarm_twist_01_l'}

bpy.ops.wm.open_mainfile(filepath=str(SRC))
rows = []
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    names = {g.name for g in ob.vertex_groups}
    if len(names & ARM_BONES) < 3:
        continue
    mods = [(m.type, getattr(m, 'object', None).name if getattr(m, 'object', None) else None)
            for m in ob.modifiers]
    rows.append({
        'name': ob.name,
        'lib': ob.library.filepath if ob.library else None,
        'mods': mods,
        'mats': [m.name if m else None for m in ob.data.materials],
        'verts': len(ob.data.vertices),
        'visible': not ob.hide_get() if ob.name in bpy.context.view_layer.objects else None,
        'hide_viewport': ob.hide_viewport,
        'hide_render': ob.hide_render,
        'collections': [c.name for c in ob.users_collection],
        'world_scale': [round(s, 5) for s in ob.matrix_world.to_scale()],
    })

cameras = []
for ob in bpy.data.objects:
    if ob.type == 'CAMERA':
        cameras.append({
            'name': ob.name,
            'world': [[round(v, 4) for v in r] for r in ob.matrix_world],
            'lens': ob.data.lens,
            'sensor': ob.data.sensor_width,
        })

scene = bpy.context.scene
report = {
    'arm_objects': rows,
    'cameras': cameras,
    'render': {
        'resolution': [scene.render.resolution_x, scene.render.resolution_y],
        'fps': scene.render.fps,
        'engine': scene.render.engine,
        'frame_range': [scene.frame_start, scene.frame_end],
    },
}
(OUT / 'arm_objects.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, indent=2, ensure_ascii=False))