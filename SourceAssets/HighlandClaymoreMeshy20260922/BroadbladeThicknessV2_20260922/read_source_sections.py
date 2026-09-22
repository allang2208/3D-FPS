"""Read installed V1 sections to set the thickness authoring dimensions."""
import bpy
import json
import numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'Broadblade20260922/HighlandClaymore_Broadblade_Editable.blend'))
mesh = bpy.data.objects['SM_Highland_Blade_Broadblade_V1'].data
mesh.calc_loop_triangles()
points = np.array([tuple(v.co) for v in mesh.vertices])
tri = np.array([t.vertices[:] for t in mesh.loop_triangles])
edges = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
a, b = points[edges[:, 0]], points[edges[:, 1]]
rows = []
for z in [.08, .14, .22, .35, .50, .65, .75, .82]:
    selected = (np.minimum(a[:, 2], b[:, 2]) <= z) & (np.maximum(a[:, 2], b[:, 2]) > z)
    aa, bb = a[selected], b[selected]
    t = (z - aa[:, 2]) / (bb[:, 2] - aa[:, 2])
    p = aa + (bb - aa) * t[:, None]
    row = {'z_cm': z * 100, 'width_mm': float(np.ptp(p[:, 0]) * 1000), 'sections': []}
    for lo, hi in [(0, .005), (.008, .015), (.020, .033), (.039, .048)]:
        part = p[(np.abs(p[:, 0]) >= lo) & (np.abs(p[:, 0]) <= hi)]
        if len(part):
            row['sections'].append({'abs_x_mm': [lo * 1000, hi * 1000],
                                    'front_mm': float(part[:, 1].min() * 1000),
                                    'back_mm': float(part[:, 1].max() * 1000)})
    rows.append(row)
(P / 'source_sections.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('SOURCE_SECTIONS ' + json.dumps(rows))
