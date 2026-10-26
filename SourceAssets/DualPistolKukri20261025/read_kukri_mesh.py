"""Read the accepted kukri mesh and material from Kukri_Editable.blend (background Blender, read-only).

Output: kukri_mesh.npz in the UE static-mesh grip frame (cm, +Z blade, +X edge, origin = fist grip centre).
"""
import bpy, json
import numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
SOURCE = ROOT / 'SourceAssets/Kukri20261020/Kukri_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
obj = bpy.data.objects['SM_Kukri']
deps = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(deps)
mesh = ev.to_mesh()
mesh.calc_loop_triangles()
xf = ev.matrix_world
X = np.array([list(xf @ v.co) for v in mesh.vertices])
T = np.array([list(t.vertices) for t in mesh.loop_triangles])
UV = np.array([[list(mesh.uv_layers.active.data[i].uv) for i in t.loops] for t in mesh.loop_triangles])
slots = np.array([t.material_index for t in mesh.loop_triangles])
materials = [m.name for m in mesh.materials]
ev.to_mesh_clear()
print('BLENDER_BOUNDS', X.min(0).round(4).tolist(), X.max(0).round(4).tolist(), flush=True)
# FBX export to UE: Blender metres -> UE centimetres, Y mirrored.
model = json.loads((ROOT / 'SourceAssets/Kukri20261020/model.json').read_text('utf-8'))
scale = 100.0 if np.abs(X).max() < 2 else 1.0
U = X * scale * np.array([1, -1, 1])
print('UE_BOUNDS', U.min(0).round(3).tolist(), U.max(0).round(3).tolist(), 'model', model['bounds_cm'], flush=True)
np.savez_compressed(P / 'kukri_mesh.npz', X=U, T=T, UV=UV, slots=slots)
(P / 'kukri_mesh.json').write_text(json.dumps({'source': str(SOURCE), 'object': 'SM_Kukri', 'materials': materials,
    'frame': model['frame'], 'scale_to_cm': scale}, indent=2), encoding='utf-8')
print('KUKRI_MESH_SAVED', len(U), len(T), materials, flush=True)
