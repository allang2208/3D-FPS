"""Read-only: where does the PSO body still stick out past the tube silhouette?"""
import bpy
from mathutils import Matrix, Vector
from pathlib import Path

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OLD = Vector((0.075, 0.035, 0.035))
bpy.ops.wm.open_mainfile(filepath=str(O / 'before-topmount/PSO1_PKM_Editable.blend'))
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH' or ob.name not in ('PSO_ScopeBody', 'PSO_ScopeLens'):
        continue
    for v in ob.data.vertices:
        p = (ob.matrix_world @ v.co) - OLD
        v.co = p
    ob.matrix_world = Matrix.Identity(4)
    out = [v for v in ob.data.vertices if v.co.x > 0.0205]
    print('OBJ', ob.name, 'verts', len(ob.data.vertices), 'left_over', len(out))
    bins = {}
    for v in out:
        k = round(v.co.y * 50) / 50.0
        b = bins.setdefault(k, [v.co.x, v.co.x, v.co.z, v.co.z, 0])
        b[0] = min(b[0], v.co.x); b[1] = max(b[1], v.co.x)
        b[2] = min(b[2], v.co.z); b[3] = max(b[3], v.co.z); b[4] += 1
    for k in sorted(bins):
        b = bins[k]
        print('  ybin %.2f x %.4f..%.4f z %.4f..%.4f n %d' % (k, b[0], b[1], b[2], b[3], b[4]))
print('NOTE_DONE')
