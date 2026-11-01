"""Switch the grip visual only, leaving combat data and item identities untouched."""
from pathlib import Path
import json,os,shutil,datetime
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('V2 import not fully saved')
path=R/'Content/ColdSteelData/thunder-god-hammer-modules.json'
raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
item=data['slots']['grip']['static_field_grip'];before=dict(item)
item.update(mesh=receipt['models'][0]['asset'],model_revision='StaticFieldGripV2',design_reference='StaticFieldGripV2/StaticField_Editable.blend')
if path.read_bytes()!=raw:raise RuntimeError('Concurrent edit; preserved current catalog')
backup=P/'Backups'/('Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/path.name)
tmp=path.with_suffix('.static-field-v2-pending');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path)
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,revision='StaticFieldGripV2',file=str(path),before=before,after=item,backup=str(backup/path.name),runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('STATIC_FIELD_V2_VISUAL_PUBLISHED')
