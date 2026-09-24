"""Measure Highland blade and guard sections around the ricasso. No exports."""
import json
from pathlib import Path
import bpy
import numpy as np

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'Integration' / 'HighlandClaymore_Modular_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

names = [
    'SM_Highland_Blade_factory',
    'SM_Highland_Blade_extended_edge',
    'SM_Highland_Blade_heavy_spine',
    'SM_Highland_Blade_feather_edge',
    'SM_Highland_Guard_factory',
    'SM_Highland_Guard_bastion_guard',
    'SM_Highland_Guard_riposte_guard',
    'SM_Highland_Guard_light_guard',
]
stations = np.round(np.linspace(-0.04, 0.12, 17), 4)
report = {}
for name in names:
    obj = bpy.data.objects[name]
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = np.array([tuple(obj.matrix_world @ v.co) for v in mesh.vertices], dtype=np.float64)
    tris = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    a, b = points[edges[:, 0]], points[edges[:, 1]]
    rows = []
    for z in stations:
        selected = (np.minimum(a[:, 2], b[:, 2]) <= z) & (np.maximum(a[:, 2], b[:, 2]) > z)
        if not np.any(selected):
            rows.append({'z_cm': round(float(z) * 100, 2), 'hits': 0})
            continue
        aa, bb = a[selected], b[selected]
        t = (z - aa[:, 2]) / np.maximum(bb[:, 2] - aa[:, 2], 1e-9)
        hit = aa + (bb - aa) * t[:, None]
        center = hit[np.abs(hit[:, 0]) < 0.012]
        rows.append({
            'z_cm': round(float(z) * 100, 2),
            'hits': int(len(hit)),
            'x_cm': [round(float(hit[:, 0].min()) * 100, 2), round(float(hit[:, 0].max()) * 100, 2)],
            'y_cm': [round(float(hit[:, 1].min()) * 100, 2), round(float(hit[:, 1].max()) * 100, 2)],
            'center_y_cm': [round(float(center[:, 1].min()) * 100, 2), round(float(center[:, 1].max()) * 100, 2)] if len(center) else None,
        })
    report[name] = {
        'verts': len(mesh.vertices),
        'faces': len(mesh.polygons),
        'z_cm': [round(float(points[:, 2].min()) * 100, 2), round(float(points[:, 2].max()) * 100, 2)],
        'sections': rows,
    }

out = P / 'probe_sections.json'
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PROBE_SECTIONS ' + str(out))
