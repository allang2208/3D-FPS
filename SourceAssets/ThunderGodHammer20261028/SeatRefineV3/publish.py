"""Publish only the five requested Thor seat mesh/appearance entries after saved import."""
from pathlib import Path
import json,shutil,datetime,hashlib
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
assert receipt['complete'] and len(receipt['models'])==5
source=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'));models={x['id']:x for x in receipt['models']}
path=R/'Content/ColdSteelData/thunder-god-hammer-modules.json';raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
B=P/'Backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-publish');B.mkdir(parents=True);shutil.copy2(path,B/path.name)
changes=[]
for row in source['parts']:
 slot=data['slots']['head_mount'][row['id']];before=dict(slot)
 slot.update(mesh=models[row['id']]['mesh'],appearance=row['appearance'],model_revision='ThorFactoryDerivedSeatsV3',source_mesh='SM_ThunderGodHammer_head_mount_factory')
 changes.append(dict(id=row['id'],before=before,after=slot))
assert path.read_bytes()==raw,'Recipe changed while publishing; rerun against current file.'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'publication_receipt.json').write_text(json.dumps(dict(changes=changes,backup=str(B/path.name),file=str(path),before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cpp_changed=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('PUBLISHED_FIVE_FACTORY_DERIVED_SEATS')
