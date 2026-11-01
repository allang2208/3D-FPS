from pathlib import Path
import json, datetime, shutil, os
P=Path(__file__).resolve().parent
R=P.parents[3]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Assets not saved')
backup=P/'Backups'/('Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
changes=[]
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
    path=R/'Content/ColdSteelData'/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    if 'modules' in file:
        item=data['slots']['head_mount']['guan_lei_seat'];before=dict(item)
        item.update(mesh=receipt['models'][0]['asset'],model_revision='GuanLeiClosedCrownV12',
            appearance='原厂雷纹圆徽 · 连体闭合顶冠 · 双侧流线嵌银回环',design_reference='GuanLeiClosedCrownV12/GuanLei_V12_Editable.blend')
    else:
        item=next(o for c in data['columns'] if c['key']=='head_mount' for o in c['options'] if o['id']=='guan_lei_seat');before=dict(item)
        item['appearance']='原厂雷纹圆徽 · 连体闭合顶冠 · 双侧流线嵌银回环'
        item['description']='雷神之锤专属。双侧流线锻肩在顶部连续闭合，嵌银回环与北欧编结护住原厂雷纹圆徽；将蓄满重击化为可召回的旋转飞锤。'
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent edit: '+file)
    shutil.copy2(path,backup/file);pending=path.with_name(file+'.guanlei-v12-pending')
    pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(pending,path)
    changes.append(dict(file=str(path),before=before,after=item))
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,revision='GuanLeiClosedCrownV12',changes=changes,gameplay_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_V12_CATALOG_PUBLISHED')
