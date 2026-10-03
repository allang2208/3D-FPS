"""World bounds of A762 PSO joint pieces, millimetres."""
import bpy, json
from pathlib import Path

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
rows = []
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH' or ob.hide_render:
        continue
    mw = ob.matrix_world
    xs, ys, zs = [], [], []
    for v in ob.data.vertices:
        p = mw @ v.co
        xs.append(p.x); ys.append(p.y); zs.append(p.z)
    rows.append({
        'name': ob.name,
        'x': [round(min(xs)*1000, 2), round(max(xs)*1000, 2)],
        'y': [round(min(ys)*1000, 2), round(max(ys)*1000, 2)],
        'z': [round(min(zs)*1000, 2), round(max(zs)*1000, 2)],
    })
print('A762_BOUNDS', json.dumps(rows), flush=True)
