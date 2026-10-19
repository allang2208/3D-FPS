"""Run under the existing UE batch gate; publish this new material and two option updates."""
import hashlib,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
receipt=json.loads((P/'asset-save.json').read_text(encoding='utf-8'))
if not receipt.get('saved'):raise RuntimeError('Cyan material was not saved')
package='/Game/Weapons/Zhanmadao20261018/ZhufengCyanTrailV1/Materials/M_ZhufengSwordTrail'
if receipt['asset']!=package+'.M_ZhufengSwordTrail':raise RuntimeError('Unexpected staged material')
rel=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
source=P/'AssetHost/Content'/rel
target=ROOT/'Content'/rel
if target.exists() and source.read_bytes()!=target.read_bytes():
    raise RuntimeError('Preserved differing production material: '+str(target))
target.parent.mkdir(parents=True,exist_ok=True)
for suffix in ['.uexp','.ubulk','.uptnl','.uasset']:
    extra=source.with_suffix(suffix)
    if extra.exists():shutil.copy2(extra,target.with_suffix(suffix))

catalog=ROOT/'Content/ColdSteelData/melee-gunsmith.json'
before=catalog.read_bytes()
data=json.loads(before.decode('utf-8-sig'))
options=next(c['options'] for c in data['columns'] if c['key']=='blade_1')
updates={}
for option_id,folder in [('zhufeng','ZhufengBladeV1'),('chixiao','ChixiaoLegendaryV1')]:
    option=next(x for x in options if x['id']==option_id)
    runpy.run_path(str(P.parent/folder/'catalog_extension.py'))['extend_option'](option)
    updates[option_id]=option['stats']
backup=P/'melee-gunsmith-before.json'
if not backup.exists():backup.write_bytes(before)
if catalog.read_bytes()!=before:raise RuntimeError('Catalog changed during merge; retained material and staged catalog')
temporary=catalog.with_suffix('.zhufeng-cyan.tmp')
temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
temporary.replace(catalog)
(P/'publication.json').write_text(json.dumps({
    'material_saved':True,'asset':receipt['asset'],
    'material_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'catalog_saved':True,'stats':updates,'game_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_CYAN_AND_PASSIVES_PUBLISHED',json.dumps(updates))
