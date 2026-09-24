import bpy
import json
from pathlib import Path

root = Path('D:/FPS3D/FPSGAME/SourceAssets/GamedevPortal20260922')
source = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev/tools/ai-gen/_settlement_building_pack_20260821/portal/portal_model.blend')
bpy.ops.wm.open_mainfile(filepath=str(source))
data = {'source': str(source), 'units': bpy.context.scene.unit_settings.scale_length, 'objects': []}
for obj in bpy.context.scene.objects:
    if obj.type not in {'MESH', 'CURVE'}:
        continue
    data['objects'].append({'name': obj.name, 'type': obj.type,
        'location': list(obj.location), 'dimensions': list(obj.dimensions),
        'materials': [s.material.name if s.material else None for s in obj.material_slots],
        'vertices': len(obj.data.vertices) if obj.type == 'MESH' else None,
        'modifiers': [{'name': m.name, 'type': m.type} for m in obj.modifiers],
        'parent': obj.parent.name if obj.parent else None})
(root/'source_inventory.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('PORTAL_SOURCE_READ ' + str(root/'source_inventory.json'))
