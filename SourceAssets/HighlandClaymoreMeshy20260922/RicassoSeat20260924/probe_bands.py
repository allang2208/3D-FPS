"""Vertex bands around the Highland ricasso. No exports."""
import json
from pathlib import Path
import bpy
import numpy as np

P = Path(__file__).resolve().parent
SOURCE = P.parent / "Integration" / "HighlandClaymore_Modular_Editable.blend"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
names = ["SM_Highland_Blade_factory", "SM_Highland_Guard_factory"]
stations = [-0.04, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
report = {}
for name in names:
    obj = bpy.data.objects[name]
    points = np.array([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices], dtype=np.float64)
    rows = []
    for z in stations:
        band = points[np.abs(points[:, 2] - z) <= 0.004]
        band = band[(np.abs(band[:, 0]) < 0.12) & (np.abs(band[:, 1]) < 0.06)]
        if len(band) == 0:
            rows.append({"z_cm": round(z * 100, 2), "n": 0})
            continue
        rows.append({
            "z_cm": round(float(z) * 100, 2),
            "n": int(len(band)),
            "x_cm": [round(float(band[:, 0].min()) * 100, 2), round(float(band[:, 0].max()) * 100, 2)],
            "y_cm": [round(float(band[:, 1].min()) * 100, 2), round(float(band[:, 1].max()) * 100, 2)],
        })
    report[name] = rows
out = P / "probe_bands.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("PROBE_BANDS", out)
