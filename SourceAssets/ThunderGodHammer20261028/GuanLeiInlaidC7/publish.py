"""Publish GuanLei's saved appearance and current legendary passive attributes."""
from pathlib import Path
import datetime,hashlib,json,os,shutil
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete'] or len(receipt['models'])!=1 or len(receipt['textures'])!=3:
    raise RuntimeError('GuanLei model/material import is incomplete')
if not json.loads((P/'icon_import_receipt.json').read_text(encoding='utf-8'))['saved']:
    raise RuntimeError('Save the revised production icon before publication')
row=receipt['models'][0];key='guan_lei_seat'
if row['id']!=key:raise RuntimeError('Unexpected modification')
backup=P/'Backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
changes=[]
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
    path=R/'Content/ColdSteelData'/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    if 'modules' in file:
        entry=data['slots']['head_mount'][key];before=dict(entry)
        entry.update(mesh=row['mesh'],model_revision='GuanLeiInlaidC7',appearance=row['appearance'],
                     source_mesh='SM_ThunderGodHammer_head_mount_factory',
                     design_reference='SeatNorseConceptV5/C_InlaidThunder.png')
    else:
        entry=next(o for c in data['columns'] if c['key']=='head_mount' for o in c['options'] if o['id']==key)
        before=dict(entry)
        entry['tier']='legendary'
        entry.setdefault('stats',{})['physical_damage_mult']=1.1
        effects=entry.setdefault('effects',[])
        effects[:]=[e for e in effects if not e.get('text','').replace(' ','').startswith('物理伤害')]
        effects.append({'text':'物理伤害+10%','benefit':1})
        entry['appearance']=row['appearance']
        entry['description']='雷神之锤专属。双向银纹嵌入一体锻肩，沿原厂雷纹圆徽回折收束，将蓄满的重击化为可召回的旋转飞锤。'
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalogue edit: '+file)
    shutil.copy2(path,backup/file)
    pending=path.with_name(path.name+'.guanlei-c7-pending')
    pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(pending,path)
    changes.append({'file':str(path),'before':before,'after':dict(entry),'backup':str(backup/file)})
(P/'publication_receipt.json').write_text(json.dumps({'complete':True,'changes':changes,
    'option_id':key,'tier':'legendary','gameplay_changed':True,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_C7_LEGENDARY_MODIFICATION_PUBLISHED')
