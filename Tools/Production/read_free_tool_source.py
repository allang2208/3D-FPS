"""Read source geometry and materials for tool fitting (no rendering or game test)."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
source, output = map(Path, args[:2])
bpy.ops.wm.read_factory_settings(use_empty=True)
if source.suffix.lower() == '.fbx':
    bpy.ops.import_scene.fbx(filepath=str(source))
else:
    bpy.ops.import_scene.gltf(filepath=str(source))
report = {'source': str(source), 'objects': [], 'images': []}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    groups = {}
    for polygon in obj.data.polygons:
        group = groups.setdefault(polygon.material_index, set())
        group.update(polygon.vertices)
    adjacency = {i: set() for i in range(len(points))}
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    remaining = set(adjacency)
    components = []
    while remaining:
        seen = {remaining.pop()}
        todo = list(seen)
        while todo:
            for adjacent in adjacency[todo.pop()]:
                if adjacent in remaining:
                    remaining.remove(adjacent)
                    seen.add(adjacent)
                    todo.append(adjacent)
        components.append({'vertices': len(seen),
            'min': [min(points[v][i] for v in seen) for i in range(3)],
            'max': [max(points[v][i] for v in seen) for i in range(3)]})
    report['objects'].append({
        'name': obj.name, 'vertices': len(points),
        'triangles': sum(len(p.vertices)-2 for p in obj.data.polygons),
        'min': [min(p[i] for p in points) for i in range(3)],
        'max': [max(p[i] for p in points) for i in range(3)],
        'matrix': [list(row) for row in obj.matrix_world],
        'materials': [slot.material.name if slot.material else None for slot in obj.material_slots],
        'components': components,
        'groups': {str(k): {'min': [min(points[v][i] for v in vs) for i in range(3)],
                          'max': [max(points[v][i] for v in vs) for i in range(3)]}
                   for k, vs in groups.items()},
    })
for image in bpy.data.images:
    report['images'].append({'name': image.name, 'path': image.filepath, 'size': list(image.size)})
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
