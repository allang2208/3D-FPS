"""Publish saved fresh assets and merge only Beiwei's owned catalog entries."""
import json,shutil,runpy,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
file=P/'import_receipt.json';receipt=json.loads(file.read_text(encoding='utf-8'))
if not receipt.get('staged_assets_saved'):raise RuntimeError('Save the isolated assets first')
for asset in receipt['assets']:
    package=asset.split('.')[0]
    if not(package.startswith('/Game/Weapons/Zhanmadao20261018/BeiweiRuneV1/') or
           package=='/Game/ColdSteelData/AttachmentIcons20260913/ue_zhanmadao_blade_2_beiwei_rune'):
        raise RuntimeError('Unexpected package '+package)
    relative=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    source=P/'AssetHost/Content'/relative;target=ROOT/'Content'/relative
    if target.exists():
        if hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest():continue
        raise RuntimeError('Preserved existing differing asset '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ['.uexp','.ubulk','.uptnl']:
        extra=source.with_suffix(suffix)
        if extra.exists():shutil.copy2(extra,target.with_suffix(suffix))
    tmp=target.with_suffix('.uasset.beiwei');shutil.copy2(source,tmp);tmp.rename(target)
receipt['assets_saved']=True;file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
icon='ue_zhanmadao_blade_2_beiwei_rune.png'
shutil.copy2(P/'Artwork/Beiwei_Icon_V1.png',DATA/'AttachmentIcons20260913'/icon)
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,data):
    path=DATA/name;backup=P/'Before'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    temp=path.with_suffix('.beiwei.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
catalog=runpy.run_path(str(P/'catalog_extension.py'))['extend'](read('zhanmadao-modules.json'))
write('zhanmadao-modules.json',catalog)
mapping=read('whirlwind-temporal-materials.json');mapping.update(receipt['temporal_bindings']);write('whirlwind-temporal-materials.json',mapping)
gunsmith=read('melee-gunsmith.json')
entry={'id':'beiwei_rune','name':'背嵬符文','tier':'legendary','weapons':['ue_zhanmadao'],
       'description':'斩马刀专属传说符文。精忠报国四字以秀雅行书鎏入刀身，笔锋顺着长刃微弧延展，暗金字底间游过暖金光。',
       'stats':{'martial_damage_mult':1.5,'martial_range_mult':1.25},
       'effects':[{'text':'武技伤害 +50%','benefit':1},{'text':'武技判定范围 +25%','benefit':1}],
       'special_effects':['释放武技时，金色剑气沿刀刃实际挥过的轨迹展开并渐隐。','伤害与范围加成仅作用于武技，普通攻击与普通连段不受影响。']}
options=next(c['options'] for c in gunsmith['columns'] if c['key']=='blade_2')
index=next((i for i,v in enumerate(options) if v['id']=='beiwei_rune'),None)
if index is None:options.append(entry)
else:options[index]=entry
write('melee-gunsmith.json',gunsmith)
receipt.update(complete=True,catalog_saved=True,icon_key=icon[:-4],game_tested=False)
file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BEIWEI_ASSETS_AND_CATALOG_PUBLISHED',len(receipt['assets']))
