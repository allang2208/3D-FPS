from pathlib import Path
import json,shutil,datetime
P=Path(__file__).resolve().parent;R=P.parents[2]
r=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not r['complete'] or len(r['models'])!=1:raise RuntimeError('Asset not saved')
row=r['models'][0];path=R/'Content/ColdSteelData/thunder-god-hammer-modules.json'
raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
entry=data['slots']['head_mount']['ribbed_light'];before=dict(entry)
if '/CommonSeatsStructuralV7/' not in entry['mesh'] and '/LightSeatWindowFixV8/' not in entry['mesh']:
 raise RuntimeError('Light-seat reference changed independently')
backup=P/'BeforePublication'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
shutil.copy2(path,backup/path.name)
entry.update(mesh=row['mesh'],model_revision='LightSeatWindowFixV8',appearance=row['appearance'])
if path.read_bytes()!=raw:raise RuntimeError('Recipe changed during publication')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,before=before,after=entry,backup=str(backup/path.name),runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('LIGHT_SEAT_V8_PUBLISHED')
