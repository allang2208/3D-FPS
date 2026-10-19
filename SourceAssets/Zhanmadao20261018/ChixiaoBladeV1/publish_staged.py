"""Publish fresh Chixiao assets, then merge its appearance-only option."""
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
receipt['assets_saved']=True;file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(P/'Export/Chixiao_Icon_Framed.png',DATA/'AttachmentIcons20260913/ue_zhanmadao_blade_1_chixiao.png')
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,data):
    path=DATA/name;backup=P/'Before'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    tmp=path.with_suffix('.chixiao.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
catalog=runpy.run_path(str(P/'catalog_extension.py'))['extend'](read('zhanmadao-modules.json'));write('zhanmadao-modules.json',catalog)
mapping=read('whirlwind-temporal-materials.json');mapping.update(receipt['temporal_bindings']);write('whirlwind-temporal-materials.json',mapping)
gunsmith=read('melee-gunsmith.json')
options=next(c['options'] for c in gunsmith['columns'] if c['key']=='blade_1')
entry={'id':'chixiao','name':'赤霄','tier':'legendary','weapons':['ue_zhanmadao'],
       'description':'玄钢锻成的宽腹长刃，厚脊渐收至修长刀尖。暗红嵌线沿刀脊延伸，刀根浮现金色云纹，中央钢面留给可替换符文。',
       'stats':{},'effects':[]}
index=next((i for i,v in enumerate(options) if v['id']=='chixiao'),None)
if index is None:options.append(entry)
else:
    # Later approved gameplay tuning belongs to its own task; reimport preserves it.
    old=options[index]
    for key in ['stats','effects','special_effects']:
        if key in old:entry[key]=old[key]
    options[index]=entry
runpy.run_path(str(P.parent/'ChixiaoLegendaryV1/catalog_extension.py'))['extend_option'](entry)
write('melee-gunsmith.json',gunsmith)
designfile=P.parent/'ChixiaoBladeConceptV1/design.json';design=json.loads(designfile.read_text(encoding='utf-8'))
effects_applied=bool(design.get('effect_proposal',{}).get('game_integrated',False))
receipt.update(complete=True,catalog_saved=True,effects_applied=effects_applied,game_tested=False)
file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design.update(user_approved=True,game_integrated=True,status='appearance_and_effect_integrated' if effects_applied else 'appearance_integrated');design['model_delivery']='../ChixiaoBladeV1/import_receipt.json'
designfile.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_ASSETS_AND_CATALOG_PUBLISHED',len(receipt['assets']),flush=True)
