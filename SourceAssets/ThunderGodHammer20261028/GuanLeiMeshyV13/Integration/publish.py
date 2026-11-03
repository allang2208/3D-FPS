"""Publish only GuanLei's visual fields after the new packages have been saved."""
# Apply the shared workbench copy standard when publishing catalogs.
from pathlib import Path as _WorkbenchCopyPath
import runpy as _workbench_copy_runpy
_workbench_copy_root = next(p for p in _WorkbenchCopyPath(__file__).resolve().parents if (p / 'FPSGAME.uproject').exists())
_apply_workbench_copy = _workbench_copy_runpy.run_path(str(_workbench_copy_root / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))['apply_for_target']

from pathlib import Path
import datetime, json, os, shutil
P = Path(__file__).resolve().parent
R = P.parents[3]
receipt = json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('GuanLei assets are not fully saved')
backup = P/'Backups'/('Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=True)
changes = []
appearance = '北境三结圆徽 · 圆弧闭冠 · 双侧回环导雷纹'
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
    path = R/'Content/ColdSteelData'/file
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    if 'modules' in file:
        item = data['slots']['head_mount']['guan_lei_seat']
        before = json.loads(json.dumps(item))
        item.update(mesh=receipt['models'][0]['asset'],model_revision='GuanLeiMeshyV13',appearance=appearance,design_reference='GuanLeiMeshyV13/GuanLei_V13_Editable.blend')
    else:
        column = next(c for c in data['columns'] if c['key']=='head_mount')
        item = next(o for o in column['options'] if o['id']=='guan_lei_seat')
        before = json.loads(json.dumps(item))
        item['appearance'] = appearance
        item['description'] = '雷神之锤专属。圆弧锻冠与双侧回环连续收束，北欧编结和蓝色导雷纹护住三结圆徽。'
    if path.read_bytes() != raw:
        raise RuntimeError('Concurrent edit: '+file)
    shutil.copy2(path,backup/file)
    pending = path.with_name(file+'.guanlei-v13-pending')
    pending.write_text(json.dumps(_apply_workbench_copy(pending, data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(pending,path)
    changes.append(dict(file=str(path),before=before,after=item,backup=str(backup/file)))
result = dict(complete=True,revision='GuanLeiMeshyV13',scope='GuanLei seat model, materials, icon and appearance text only',changes=changes,runtime_tested=False)
(P/'publication_receipt.json').write_text(json.dumps(_apply_workbench_copy(P/'publication_receipt.json', result),ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_V13_CATALOG_PUBLISHED')
