"""Read the current factory source and precise installation surfaces for authoring."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'ModulesV1/RuneboundWarhammer_Modular_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.name.startswith('SM_RuneboundWarhammer_'):
        continue
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lower = [min(p[i] for p in points) for i in range(3)]
    upper = [max(p[i] for p in points) for i in range(3)]
    rows.append({'object': obj.name, 'location_m': list(obj.location),
                 'bounds_min_m': lower, 'bounds_max_m': upper,
                 'materials': [m.name for m in obj.data.materials if m]})
material = bpy.data.objects['SM_RuneboundWarhammer_head_mount_factory'].data.materials[0]
images = [{'node': node.name, 'image': node.image.name, 'path': bpy.path.abspath(node.image.filepath),
           'packed': bool(node.image.packed_file)}
          for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image]
interfaces = json.loads((P.parent/'ModulesV1/interfaces.json').read_text(encoding='utf-8'))
mounts = interfaces['parts']['hammer_heads']
result = {'source_blend': str(SOURCE), 'parts': rows, 'images': images,
          'interface': interfaces['interface'], 'cuts': interfaces['cuts'],
          'head_interfaces': mounts, 'scene_units': bpy.context.scene.unit_settings.scale_length}
(P/'host_contract.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('AUTHOR_HOST_CONTRACT', json.dumps({'parts': rows, 'images': images,
      'interface_summary': [{'cut': x['cut'], 'segments': len(x['segments_m'])} for x in mounts['interfaces']]}, ensure_ascii=False), flush=True)
