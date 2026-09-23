"""Headless inventory of the authored WorkbenchKit blend: objects, bounds, materials, triangles.

Run:
  "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --python-exit-code 1 \
      --python SourceAssets/WorkbenchBuildable20260924/Scripts/inspect_kit_blend.py
"""
from pathlib import Path
import bpy, json, sys

ROOT = Path(__file__).resolve().parents[1]
KIT = Path("D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonWorkbenchKit.blend")

bpy.ops.wm.open_mainfile(filepath=str(KIT))

rows = []
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        rows.append(dict(name=ob.name, type=ob.type))
        continue
    me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh() if ob.modifiers else ob.data
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    try:
        bb = [ev.matrix_world @ __import__('mathutils').Vector(c) for c in ob.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]
        mx = [max(v[i] for v in bb) for i in range(3)]
    except Exception:
        mn = mx = [None, None, None]
    rows.append(dict(
        name=ob.name, type='MESH', visible=not ob.hide_get() and not ob.hide_render,
        loc=[round(v, 2) for v in ob.location],
        size_cm=[round((mx[i] - mn[i]) * 100, 1) if mn[i] is not None else None for i in range(3)],
        world_min_cm=[round(v * 100, 1) if v is not None else None for v in mn],
        tris=tris,
        materials=[m.name if m else None for m in me.materials],
        uv_layers=[l.name for l in me.uv_layers],
        verts=len(me.vertices),
    ))
    ev.to_mesh_clear()

out = ROOT / 'Receipts'
out.mkdir(exist_ok=True)
(out / 'kit-blend-inventory.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
print('KIT_INVENTORY_OBJECTS', len(rows))
for r in rows:
    if r.get('type') == 'MESH':
        print('%-34s tris=%-8d size=%s mats=%s' % (r['name'], r['tris'], r['size_cm'], r['materials']))
