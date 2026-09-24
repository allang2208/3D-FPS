"""Inspect the warehouse chest GLB: per-slot poly counts/bounds (role inference) and rest pose.
Background Blender run. No renders/tests.
"""
import bpy, json
from pathlib import Path

HERE = Path(__file__).parent
GLB = HERE.parent / 'ChestRitual20260909' / 'warehouse_chest_ritual_v8.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))

report = {'objects': [], 'animations': [a.name for a in bpy.data.actions]}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)  # armature applied, world-evaluated
    slots = []
    for index, mat in enumerate(me.materials):
        polys = [p for p in me.polygons if p.material_index == index]
        if not polys:
            slots.append({'slot': mat.name if mat else None, 'polys': 0})
            continue
        mins = [1e9] * 3; maxs = [-1e9] * 3
        for p in polys:
            world_cos = [ev.matrix_world @ me.vertices[v].co for v in p.vertices]
            for i in range(3):
                mins[i] = min(mins[i], min(c[i] for c in world_cos))
                maxs[i] = max(maxs[i], max(c[i] for c in world_cos))
        slots.append({'slot': mat.name if mat else None, 'polys': len(polys),
                      'center': [round((mins[i] + maxs[i]) / 2, 3) for i in range(3)],
                      'size': [round(maxs[i] - mins[i], 3) for i in range(3)]})
    report['objects'].append({'name': obj.name, 'polys': len(me.polygons), 'slots': slots})
    bpy.data.meshes.remove(me)
(HERE / 'chest_source_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CHEST_INSPECTED ' + json.dumps({'objects': len(report['objects']), 'anims': report['animations']}))
