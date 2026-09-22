"""Read the installed blade's author FBX; export face-corner data for mask baking.

This is production data extraction, with no scene changes, renders or game tests.
"""
from pathlib import Path
import json
import bpy
import numpy as np

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'RuneSwordModules20260919/Export/SM_RuneSword_Blade_factory.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE))
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
mesh.data.calc_loop_triangles()
uv = mesh.data.uv_layers[0]
loops = np.array([list(t.loops) for t in mesh.data.loop_triangles], dtype=np.int32)
corner_uv = np.array([list(v.uv) for v in uv.data], dtype=np.float32)
corner_pos = np.array([list(mesh.matrix_world @ mesh.data.vertices[l.vertex_index].co)
                       for l in mesh.data.loops], dtype=np.float32)
np.savez_compressed(P / 'blade_uv_source.npz', uv=corner_uv[loops], position=corner_pos[loops])
(P / 'source.json').write_text(json.dumps({
    'source_fbx': str(SOURCE), 'object': mesh.name, 'uv_channel': 0,
    'triangles': len(loops), 'position_units': 'metres',
    'bounds': [corner_pos.min(axis=0).tolist(), corner_pos.max(axis=0).tolist()],
}, indent=2), encoding='utf-8')
print('NATIVE_RUNE_UV_SOURCE_WRITTEN', len(loops))
