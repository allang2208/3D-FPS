from pathlib import Path
import json,shutil,datetime,hashlib
P=Path(__file__).resolve().parent;R=P.parents[2];receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
assert receipt['complete'] and len(receipt['models'])==5 and len(receipt['textures'])==15
for row in receipt['models']:
 name=row['mesh'].rsplit('.',1)[-1]
 assert hashlib.sha256((P/'Export'/(name+'.fbx')).read_bytes()).hexdigest()==row['fbx_sha256'],'Saved mesh belongs to an older export: '+row['id']
for row in receipt['textures']:
 assert hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()==row['sha256'],'Saved texture belongs to an older bake: '+row['id']
path=R/'Content/ColdSteelData/thunder-god-hammer-modules.json';raw=path.read_bytes();d=json.loads(raw.decode('utf-8-sig'))
B=P/'Backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');B.mkdir(parents=True);shutil.copy2(path,B/path.name)
changed=[]
for row in receipt['models']:
 entry=d['slots']['head_mount'][row['id']];before=dict(entry)
 if '/SeatRefineV3/' not in entry['mesh'] and '/SeatPrecisionV4/' not in entry['mesh']:raise RuntimeError('Active seat changed independently: '+row['id'])
 entry.update(mesh=row['mesh'],model_revision='ThorSeatsPrecisionV4')
 changed.append({'id':row['id'],'before':before,'after':entry})
assert path.read_bytes()==raw,'Recipe changed during publication'
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'publication_receipt.json').write_text(json.dumps({'changes':changed,'file':str(path),'backup':str(B/path.name),'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('PUBLISHED_PRECISION_SEATS_V4')
