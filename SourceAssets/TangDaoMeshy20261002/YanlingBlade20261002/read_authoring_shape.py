"""Read the fitted blade cross sections used to construct its new body."""
import bpy, json
from pathlib import Path
import numpy as np
P = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'SurfaceV2/TangDao_SurfaceV2_Editable.blend'))
obj = bpy.data.objects['SM_TangDao_Blade_factory']
xyz = np.array([tuple(v.co) for v in obj.data.vertices])
sections = []
for z in [.014, .12, .22, .30, .34, .4, .55, .7, .78, .82, .86, .88]:
    points = xyz[np.abs(xyz[:, 2] - z) < .005]
    if len(points):
        sections.append({'z_m': z, 'min': points.min(axis=0).tolist(), 'max': points.max(axis=0).tolist()})
data = {'sections': sections, 'root_interface_m': .014, 'body_join_m': .34,
        'material_slots': [m.name for m in obj.data.materials],
        'source_object_location': list(obj.location)}
(P / 'authoring_shape.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data), flush=True)
