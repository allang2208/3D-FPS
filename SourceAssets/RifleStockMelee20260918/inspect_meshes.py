"""列出骨架绑定的网格对象（判断预览要保留哪些渲染部件）。"""
import bpy
from pathlib import Path

DIR = Path(__file__).resolve().parent
SRC = DIR.parent / 'M4ContactImpact20260910' / 'M4_Hand_MAT_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SRC))

for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    mods = [m for m in ob.modifiers if m.type == 'ARMATURE']
    targets = [m.object.name if m.object else None for m in mods]
    if targets:
        print('[MESH] %-38s armature=%s hide_render=%s verts=%d parent=%s' % (
            ob.name, targets, ob.hide_render, len(ob.data.vertices), ob.parent.name if ob.parent else None), flush=True)
