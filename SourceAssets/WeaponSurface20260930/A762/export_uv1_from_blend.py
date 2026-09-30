"""Blender (background): re-export per-corner UV1 from A762_SurfaceBake.blend.

blender -b A762_SurfaceBake.blend -P export_uv1_from_blend.py
Same output as bake_a762.py's write_uv1 (UE V-down, dump corner order).
"""
import json
from pathlib import Path
import bpy
import numpy as np

HERE = Path(__file__).parent
report = json.loads((HERE / 'Bake' / 'bake_report.json').read_text(encoding='utf-8'))
ob = bpy.data.objects['A762']
me = ob.data
loops = np.empty(len(me.loops) * 2, np.float32)
me.uv_layers['UV1'].data.foreach_get('uv', loops)
loops = loops.astype(np.float64).reshape(-1, 3, 2)[:, np.argsort(report['objects']['A762']['order'])]
bad = ~np.isfinite(loops).all(axis=(1, 2)) | (np.abs(loops) > 4).any(axis=(1, 2))
print('A762_UV1_INVALID_TRIANGLES', int(bad.sum()))
ue = np.stack([loops[..., 0], 1.0 - loops[..., 1]], -1).astype(np.float32)
with open(HERE / 'Bake' / 'A762_uv1.bin', 'wb') as f:
    f.write((json.dumps({'triangles': int(ue.shape[0]),
                         'position_checksum': report['inputs']['A762']['position_checksum']}) + '\n').encode('utf-8'))
    f.write(ue.tobytes())
print('A762_UV1_EXPORTED', ue.shape, float(ue.min()), float(ue.max()))
