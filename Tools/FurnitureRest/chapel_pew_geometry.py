"""Read the authored chapel pew's contact surfaces in UE centimetres; no renders."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ChapelFurniture20261116'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT / 'SourceAssets/TemperateHillsOldChapel/Concept01/Authored/SM_ChapelPew.fbx'))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = []
surfaces = []
for obj in objects:
    points.extend([[v.x * 100, -v.y * 100, v.z * 100]
                   for v in (obj.matrix_world @ v.co for v in obj.data.vertices)])
    for y in (-60, 0, 60):
        for x in (-23, -18, -12, -6, 0, 6, 12, 18, 23):
            origin = obj.matrix_world.inverted() @ Vector((x / 100, -y / 100, 1.2))
            direction = obj.matrix_world.inverted().to_3x3() @ Vector((0, 0, -1))
            hit, p, n, _ = obj.ray_cast(origin, direction)
            if hit:
                p = obj.matrix_world @ p
                surfaces.append({'x': x, 'y': y, 'z': round(p.z * 100, 3),
                                 'normal_z': round(n.z, 3)})
lo = [min(p[i] for p in points) for i in range(3)]
hi = [max(p[i] for p in points) for i in range(3)]
result = {'source': 'SM_ChapelPew.fbx', 'bounds_cm': [lo, hi],
          'assembly_scale': 1.25, 'top_surfaces_cm': surfaces}
(OUT / 'pew_geometry.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('CHAPEL_PEW_GEOMETRY', json.dumps(result), flush=True)
