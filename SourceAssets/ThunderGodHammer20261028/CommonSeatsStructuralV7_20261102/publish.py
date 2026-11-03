"""Publish only the three retained common seat mesh references after asset save."""
from pathlib import Path
import json,shutil,datetime
P=Path(__file__).resolve().parent;R=P.parents[2]
r=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not r['complete'] or len(r['models'])!=3:raise RuntimeError('Assets have not been saved')
path=R/'Content/ColdSteelData/thunder-god-hammer-modules.json'
raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
backup=P/'BeforePublication'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
shutil.copy2(path,backup/path.name)
changes=[]
for row in r['models']:
 entry=data['slots']['head_mount'][row['id']];old=dict(entry)
 if '/SeatInlaidC6/' not in entry['mesh'] and '/CommonSeatsStructuralV7/' not in entry['mesh']:
  raise RuntimeError('Active reference changed independently: '+row['id'])
 entry.update(mesh=row['mesh'],model_revision='CommonSeatsStructuralV7',appearance=row['appearance'],
              design_reference='CommonSeatsStructuralV7_20261102/CommonSeats_Structural_Concept.png')
 changes.append(dict(id=row['id'],before=old,after=dict(entry)))
if path.read_bytes()!=raw:raise RuntimeError('Recipe changed during publication')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,changes=changes,file=str(path),backup=str(backup/path.name),icons='Existing shared common-melee icons preserved',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('THREE_COMMON_SEAT_REFERENCES_PUBLISHED')
