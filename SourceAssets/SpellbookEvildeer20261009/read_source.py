"""Read the downloaded author's FBX to plan the selected book adaptation."""
import bpy, json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT / 'Original/source/books set.fbx'))
result = {'objects': [], 'materials': [], 'actions': [a.name for a in bpy.data.actions]}
for obj in bpy.data.objects:
    row = {'name': obj.name, 'type': obj.type, 'location': list(obj.location), 'rotation': list(obj.rotation_euler), 'scale': list(obj.scale)}
    if obj.type == 'MESH':
        points = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        row.update(vertices=len(obj.data.vertices), polygons=len(obj.data.polygons), materials=[m.name if m else None for m in obj.data.materials], uv_layers=[u.name for u in obj.data.uv_layers], bounds=[[min(v[i] for v in points) for i in range(3)], [max(v[i] for v in points) for i in range(3)]])
    result['objects'].append(row)
for mat in bpy.data.materials:
    nodes=[]
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                nodes.append({'node':node.name,'image':node.image.name if node.image else None,'filepath':node.image.filepath if node.image else None,'size':list(node.image.size) if node.image else None, 'links': [(link.to_node.name,link.to_socket.name) for output in node.outputs for link in output.links]})
    result['materials'].append({'name':mat.name,'images':nodes})
(ROOT/'source-structure.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source-import.blend'))
print('SOURCE_STRUCTURE '+json.dumps(result,ensure_ascii=True))
