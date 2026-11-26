"""Persist the exact joined icon material order without rerendering."""
import json
from pathlib import Path
import bpy
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/Integration')
p=json.loads((R/'prepared.json').read_text(encoding='utf-8-sig'))
for row in p['rows']:
    if not row['key']:continue
    bpy.ops.wm.open_mainfile(filepath=str(R/'Icons'/(row['key']+'-icon.blend')))
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render)
    slots=[m.name.split('.')[0] for m in ob.data.materials]
    f=Path(row['icon']['display']);d=json.loads(f.read_text(encoding='utf-8-sig'));d['material_slots']=slots;f.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
print('TS01_DISPLAY_MATERIAL_ORDER_SAVED',flush=True)
