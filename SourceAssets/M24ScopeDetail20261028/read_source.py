"""Read source UV triangles and connected shells for material authoring only."""
import bpy, json
from pathlib import Path

O = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent / 'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'), use_scripts=False)
ob = bpy.data.objects['M24_MainScope_Lowpoly']
mesh = ob.data
parents = list(range(len(mesh.vertices)))
def root(i):
    while parents[i] != i:
        parents[i] = parents[parents[i]]
        i = parents[i]
    return i
for edge in mesh.edges:
    a, b = map(root, edge.vertices)
    parents[a] = b
groups = {}
for v in mesh.vertices:
    groups.setdefault(root(v.index), []).append(v.index)
shells = []
for key, ids in groups.items():
    points = [ob.matrix_world @ mesh.vertices[i].co for i in ids]
    shells.append({'id': key, 'count': len(ids), 'min': [min(p[i] for p in points) for i in range(3)], 'max': [max(p[i] for p in points) for i in range(3)]})
mesh.calc_loop_triangles()
uv = mesh.uv_layers[0].data
triangles = []
for tri in mesh.loop_triangles:
    ids = tri.vertices
    points = [ob.matrix_world @ mesh.vertices[i].co for i in ids]
    triangles.append({'shell': root(ids[0]), 'center': [sum(p[i] for p in points) / 3 for i in range(3)],
                      'normal': list(tri.normal), 'uv': [list(uv[i].uv) for i in tri.loops]})
(O / 'scope_geometry.json').write_text(json.dumps({'shells': shells, 'triangles': triangles}), encoding='utf-8')
print('M24_SCOPE_MATERIAL_SHELLS', json.dumps(sorted(shells, key=lambda s: -s['count'])[:24]), flush=True)
