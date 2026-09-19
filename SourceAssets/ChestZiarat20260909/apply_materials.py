import json
from pathlib import Path
root=Path(__file__).parent
manifest=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json')
before=json.loads((root/'Before/warehouse_assets.json').read_text())
data=json.loads(manifest.read_text())
marble=json.loads((root/'material_report.json').read_text())['material']
metal=json.loads((root/'dirty_metal_report.json').read_text())['material']
updates={'White_Marble_PBR':marble,**dict.fromkeys(['Gold_PBR','Brass_Frame','Brass_Hardware','Brass_Strap'],metal)}
for slot,path in updates.items():
 assert data['materials'][slot] in [before['materials'][slot],path],f'Concurrent edit in {slot}; inspect before replacing'
 asset=Path('D:/FPS3D/FPSGAME/Content')/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
 assert asset.is_file(),asset
 data['materials'][slot]=path
temporary=manifest.with_suffix('.ziarat-tmp')
temporary.write_text(json.dumps(data,indent=2)+'\n')
temporary.replace(manifest)
(root/'applied_slots.json').write_text(json.dumps(updates,indent=2))
print('CHEST_MATERIALS_APPLIED slots='+str(len(updates)))
