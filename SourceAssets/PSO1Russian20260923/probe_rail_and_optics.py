"""Read-only: bounds of the PKM rail and a working optic in their authoring blends."""
import bpy
from pathlib import Path

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Accessories14')
for name in ('SM_PKM_optic_rail', 'SM_PKM_panoramic_red_dot', 'SM_PKM_prism_scope_2x', 'PKM_Modular_Editable'):
    p = O / (name + '.blend')
    if not p.exists():
        print('MISS', name)
        continue
    bpy.ops.wm.open_mainfile(filepath=str(p))
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        lo = [round(min(q[k] for q in pts), 4) for k in range(3)]
        hi = [round(max(q[k] for q in pts), 4) for k in range(3)]
        print('BOUNDS', name, '|', ob.name, '| lo', lo, '| hi', hi, '| tris', len(ob.data.polygons))
print('NOTE_DONE')
