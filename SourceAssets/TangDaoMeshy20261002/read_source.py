"""Read the user supplied saber's authoring geometry and extract embedded PBR."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix

P = Path(__file__).resolve().parent
SOURCE = P / 'Original/Meshy_AI_Dragonforged_Saber_1002040045_texture.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rows = []
for obj in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    points = [v.co for v in obj.data.vertices]
    bounds = [[min(p[a] for p in points), max(p[a] for p in points)] for a in range(3)]
    axis = max(range(3), key=lambda a: bounds[a][1]-bounds[a][0])
    lo, hi = bounds[axis]
    slices = []
    for i in range(81):
        z = lo + (hi-lo)*i/80
        section = [p for p in points if abs(p[axis]-z) < (hi-lo)/220]
        if section:
            slices.append({'longitudinal': z, 'bounds': [[min(p[a] for p in section), max(p[a] for p in section)] for a in range(3)]})
    rows.append({'name': obj.name, 'vertices': len(points), 'triangles': len(obj.data.polygons),
                 'bounds': bounds, 'longitudinal_axis': axis, 'slices': slices})
texture_dir = P / 'Textures'
texture_dir.mkdir(exist_ok=True)
materials = []
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    info = {'name': mat.name, 'textures': [], 'inputs': {}}
    for node in mat.node_tree.nodes:
        if node.type != 'TEX_IMAGE' or not node.image:
            continue
        img = node.image
        filename = texture_dir / (img.name.rsplit('.', 1)[0] + '.png')
        img.filepath_raw = str(filename)
        img.file_format = 'PNG'
        img.save()
        info['textures'].append({'image': img.name, 'file': filename.name, 'size': list(img.size),
                                 'color_space': img.colorspace_settings.name,
                                 'links': [l.to_node.name + ':' + l.to_socket.name for l in node.outputs['Color'].links]})
    if principled:
        for key in ['Metallic', 'Roughness', 'Base Color', 'Emission Color', 'Emission Strength']:
            socket = principled.inputs.get(key)
            if socket:
                value = socket.default_value
                info['inputs'][key] = float(value) if isinstance(value, (int, float)) else list(value)
    materials.append(info)
(P / 'source_coordinates.json').write_text(json.dumps({'meshes': rows, 'materials': materials}, indent=2), encoding='utf-8')
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'TangDao_Original_Editable.blend'))
print('TANGDAO_SOURCE ' + json.dumps({'meshes': [{k: v for k, v in r.items() if k != 'slices'} for r in rows], 'materials': materials}), flush=True)
