"""Publish only new Zhufeng packages, then merge its live recipe and option."""
import json,shutil,runpy,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
file=P/'import_receipt.json';r=json.loads(file.read_text(encoding='utf-8'))
if not r.get('staged_assets_saved'):raise RuntimeError('Staged asset save is incomplete')
for asset in r['assets']:
    package=asset.split('.')[0]
    if not(package.startswith('/Game/Weapons/Zhanmadao20261018/ZhufengBladeV1/') or package=='/Game/ColdSteelData/AttachmentIcons20260913/ue_zhanmadao_blade_1_zhufeng'):
        raise RuntimeError('Unexpected package '+package)
    rel=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    source=P/'AssetHost/Content'/rel;target=ROOT/'Content'/rel
    if target.exists():
        if hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest():continue
        raise RuntimeError('Preserved existing differing package '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ['.uexp','.ubulk','.uptnl']:
        extra=source.with_suffix(suffix)
        if extra.exists():shutil.copy2(extra,target.with_suffix(suffix))
    shutil.copy2(source,target)
r['assets_saved']=True
file.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(P/'Export/Zhufeng_Icon_Framed.png',DATA/'AttachmentIcons20260913/ue_zhanmadao_blade_1_zhufeng.png')
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,data):
    path=DATA/name;backup=P/'Before'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    tmp=path.with_suffix('.zhufeng.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
extension=runpy.run_path(str(P/'catalog_extension.py'))
write('zhanmadao-modules.json',extension['extend'](read('zhanmadao-modules.json')))
mapping=read('whirlwind-temporal-materials.json');mapping.update(r['temporal_bindings']);write('whirlwind-temporal-materials.json',mapping)
gunsmith=read('melee-gunsmith.json');options=next(c['options'] for c in gunsmith['columns'] if c['key']=='blade_1')
entry=next((v for v in options if v['id']=='zhufeng'),None)
if entry is None:entry={};options.append(entry)
extension['extend_option'](entry);write('melee-gunsmith.json',gunsmith)
r.update(complete=True,catalog_saved=True,effects_source_written=True,native_build_pending=True,game_tested=False)
file.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
designfile=P.parent/'ZhufengBladeConceptV1/design.json';design=json.loads(designfile.read_text(encoding='utf-8'))
design.update(user_approved=True,name_status='accepted',game_integrated=True,status='assets_saved_native_build_pending',model_delivery='../ZhufengBladeV1/import_receipt.json')
designfile.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_ASSETS_AND_CATALOG_PUBLISHED',len(r['assets']))
