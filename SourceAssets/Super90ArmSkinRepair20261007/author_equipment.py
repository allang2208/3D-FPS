"""Rebuild only Super90 derivatives from the unchanged M4 equipment donors."""
import json
from pathlib import Path
P=Path(r'D:/FPS3D/FPSGAME');O=Path(__file__).parent;S=P/'SourceAssets/BenelliM4Super9020261006'
scope={'__file__':str(S/'author_equipment_family.py')}
code=(S/'author_equipment_family.py').read_text(encoding='utf-8-sig').split('# First transport')[0]
exec(compile(code,str(S/'author_equipment_family.py'),'exec'),scope)
binding=json.loads((S/'EquipmentSources/source_bare.json').read_text())
files=list((S/'EquipmentSources').glob('ue_*.json'))+[S/'EquipmentSources/skin_ue_field_gloves.json']
for file in files:
    data=json.loads(file.read_text())
    scope['fit'](data,scope['warp'],lambda n:scope['target_name'](n,binding['bones']),binding,'Super90',file.stem)
(O/'equipment_manifest.json').write_text(json.dumps(scope['manifest'],indent=2))
print('SUPER90_ARM_EQUIPMENT_AUTHORED',len(scope['manifest']),flush=True)
