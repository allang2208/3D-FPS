"""Measure the current warehouse chest (RitualV8 source) for the tier crate reference. No renders/tests."""
import bpy, json
from pathlib import Path

HERE = Path(__file__).parent
GLB = HERE.parent / 'ChestRitual20260909' / 'warehouse_chest_ritual_v8.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))

report = {'source': str(GLB), 'objects': []}
mins = [1e9] * 3
maxs = [-1e9] * 3
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    me = obj.data
    lmin = [1e9] * 3
    lmax = [-1e9] * 3
    for v in me.vertices:
        world = obj.matrix_world @ v.co
        for i in range(3):
            mins[i] = min(mins[i], world[i])
            maxs[i] = max(maxs[i], world[i])
            lmin[i] = min(lmin[i], v.co[i])
            lmax[i] = max(lmax[i], v.co[i])
    report['objects'].append({
        'name': obj.name,
        'polys': len(me.polygons),
        'verts': len(me.vertices),
        'materials': [m.name if m else None for m in me.materials],
        'local_dims': [round(lmax[i] - lmin[i], 2) for i in range(3)],
    })
report['bounds_min'] = [round(v, 2) for v in mins]
report['bounds_max'] = [round(v, 2) for v in maxs]
report['dims_cm'] = [round(maxs[i] - mins[i], 2) for i in range(3)]
total = sum(o['polys'] for o in report['objects'])
report['total_polys'] = total
(HERE / 'reference_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REFERENCE_MEASURED ' + json.dumps({'dims_cm': report['dims_cm'], 'objects': len(report['objects']), 'polys': total}))
