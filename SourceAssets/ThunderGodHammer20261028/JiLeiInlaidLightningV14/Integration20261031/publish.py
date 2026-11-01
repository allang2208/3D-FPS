"""Publish only JiLei's visual fields after the new packages have been saved."""
from pathlib import Path
import datetime, json, os, shutil
P = Path(__file__).resolve().parent
R = P.parents[3]
receipt = json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('JiLei assets are not fully saved')
backup = P/'Backups'/('Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=True)
changes = []
appearance = '原厂雷纹圆徽 · 连体折肩与短冠 · 内嵌聚雷纹路'
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
    path = R/'Content/ColdSteelData'/file
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    if 'modules' in file:
        item = data['slots']['head_mount']['ji_lei_seat']
        before = json.loads(json.dumps(item))
        item.update(mesh=receipt['models'][0]['asset'],model_revision='JiLeiInlaidLightningV14',appearance=appearance,design_reference='JiLeiInlaidLightningV14/JiLei_V14_Editable.blend')
    else:
        column = next(c for c in data['columns'] if c['key']=='head_mount')
        item = next(o for o in column['options'] if o['id']=='ji_lei_seat')
        before = json.loads(json.dumps(item))
        item['appearance'] = appearance
        item['description'] = '雷神之锤专属。连体折肩承接低矮锻冠，内嵌银线与聚雷刻纹收束至原厂圆徽；单手举锤蓄力，指向地面召下疾雷。'
    if path.read_bytes() != raw:
        raise RuntimeError('Concurrent edit: '+file)
    shutil.copy2(path,backup/file)
    pending = path.with_name(file+'.jilei-v14-pending')
    pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(pending,path)
    changes.append(dict(file=str(path),before=before,after=item,backup=str(backup/file)))
result = dict(complete=True,revision='JiLeiInlaidLightningV14',scope='JiLei seat model, materials, icon and appearance text only',changes=changes,runtime_tested=False)
(P/'publication_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('JILEI_V14_CATALOG_PUBLISHED')
