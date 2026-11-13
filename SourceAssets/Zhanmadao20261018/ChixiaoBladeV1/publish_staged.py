"""Publish fresh Chixiao assets, then merge its appearance-only option."""
# Apply the shared workbench copy standard when publishing catalogs.
from pathlib import Path as _WorkbenchCopyPath
import runpy as _workbench_copy_runpy
_workbench_copy_root = next(p for p in _WorkbenchCopyPath(__file__).resolve().parents if (p / 'FPSGAME.uproject').exists())
_apply_workbench_copy = _workbench_copy_runpy.run_path(str(_workbench_copy_root / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))['apply_for_target']

import json,shutil,runpy,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
file=P/'import_receipt.json';receipt=json.loads(file.read_text(encoding='utf-8'))
if not receipt.get('staged_assets_saved'):raise RuntimeError('Save the isolated assets first')
for asset in receipt['assets']:
    package=asset.split('.')[0]
    if not(package.startswith('/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/') or package=='/Game/ColdSteelData/AttachmentIcons20260913/ue_zhanmadao_blade_1_chixiao'):
        raise RuntimeError('Unexpected package '+package)
    rel=Path(package.removeprefix('/Game/')).with_suffix('.uasset');source=P/'AssetHost/Content'/rel;target=ROOT/'Content'/rel
    if target.exists():
        if hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest():continue
        raise RuntimeError('Preserved differing target '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ['.uexp','.ubulk','.uptnl']:
        extra=source.with_suffix(suffix)
        if extra.exists():shutil.copy2(extra,target.with_suffix(suffix))
    tmp=target.with_suffix('.uasset.chixiao');shutil.copy2(source,tmp);tmp.rename(target)
receipt['assets_saved']=True;file.write_text(json.dumps(_apply_workbench_copy(file, receipt),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(P/'Export/Chixiao_Icon_Framed.png',DATA/'AttachmentIcons20260913/ue_zhanmadao_blade_1_chixiao.png')
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,data):
    data = _apply_workbench_copy(name, data)
    path=DATA/name;backup=P/'Before'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    tmp=path.with_suffix('.chixiao.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
catalog=runpy.run_path(str(P/'catalog_extension.py'))['extend'](read('zhanmadao-modules.json'));write('zhanmadao-modules.json',catalog)
mapping=read('whirlwind-temporal-materials.json');mapping.update(receipt['temporal_bindings']);write('whirlwind-temporal-materials.json',mapping)
designfile=P.parent/'ChixiaoBladeConceptV1/design.json';design=json.loads(designfile.read_text(encoding='utf-8'))
effects_applied=bool(design.get('effect_proposal',{}).get('game_integrated',False))
receipt.update(complete=True,catalog_saved=True,effects_applied=effects_applied,game_tested=False)
file.write_text(json.dumps(_apply_workbench_copy(file, receipt),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design.update(user_approved=True,game_integrated=True,status='appearance_and_effect_integrated' if effects_applied else 'appearance_integrated');design['model_delivery']='../ChixiaoBladeV1/import_receipt.json'
designfile.write_text(json.dumps(_apply_workbench_copy(designfile, design),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_ASSETS_AND_CATALOG_PUBLISHED',len(receipt['assets']),flush=True)
