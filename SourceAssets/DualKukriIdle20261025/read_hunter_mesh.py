"""Read the hunter blade module (猎手刀身, KukriHunterBlade20261027) from Kukri_Hunter_Editable.blend (background Blender,
read-only) into Work/hunter_blade_mesh.npz in the UE static-mesh grip frame (cm, +Z blade, +X edge, origin = fist grip
centre), the frame of SM_Kukri and of every kukri module (KukriModules20261026/README.md).  Same conversion as
DualPistolKukri20261025/read_kukri_mesh.py (Blender metres -> UE cm, Y mirrored).
Run:  blender -b --factory-startup --python read_hunter_mesh.py
"""
import bpy
import numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'KukriHunterBlade20261027' / 'Kukri_Hunter_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
obj = bpy.data.objects['SM_Kukri_Blade_Hunter']
deps = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(deps)
mesh = ev.to_mesh()
mesh.calc_loop_triangles()
xf = ev.matrix_world
X = np.array([list(xf @ v.co) for v in mesh.vertices])
T = np.array([list(t.vertices) for t in mesh.loop_triangles])
ev.to_mesh_clear()
scale = 100.0 if np.abs(X).max() < 2 else 1.0
U = X * scale * np.array([1, -1, 1])
print('HUNTER_UE_BOUNDS', U.min(0).round(3).tolist(), U.max(0).round(3).tolist(), len(U), len(T), flush=True)
(P / 'Work').mkdir(exist_ok=True)
np.savez_compressed(P / 'Work' / 'hunter_blade_mesh.npz', X=U, T=T)
