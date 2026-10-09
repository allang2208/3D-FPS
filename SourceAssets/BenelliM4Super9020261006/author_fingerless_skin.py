from pathlib import Path
import json
O=Path(__file__).parent
scope={'__file__':str(O/'author_equipment_family.py')}
exec(compile((O/'author_equipment_family.py').read_text(encoding='utf-8-sig').split('# First transport')[0],str(O/'author_equipment_family.py'),'exec'),scope)
source=json.loads((O/'EquipmentSources/skin_ue_field_gloves.json').read_text());binding=json.loads((O/'EquipmentSources/source_bare.json').read_text());scope['fit'](source,scope['warp'],lambda n:scope['target_name'](n,binding['bones']),binding,'Super90','skin_ue_field_gloves')
(O/'equipment_skin_manifest.json').write_text(json.dumps(scope['manifest'],indent=2))
