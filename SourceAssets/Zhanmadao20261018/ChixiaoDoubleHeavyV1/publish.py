"""Publish only new double-heavy animations and merge the selected attachment."""
import hashlib,json,runpy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
receipt=json.loads((P/'assets-saved.json').read_text('utf-8'))
for asset in receipt['assets']:
    package=asset.split('.')[0]
    if not package.startswith('/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1/'):
        raise RuntimeError('Unexpected publication package '+package)
    rel=Path(package[6:]).with_suffix('.uasset');source=P/'AssetHost/Content'/rel;target=ROOT/'Content'/rel
    if target.exists():
        if hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest():continue
        raise RuntimeError('Preserving different existing package '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ('.uexp','.ubulk','.uptnl'):
        if source.with_suffix(suffix).exists():shutil.copy2(source.with_suffix(suffix),target.with_suffix(suffix))
    shutil.copy2(source,target)
def read(name):return json.loads((DATA/name).read_text('utf-8-sig'))
def write(name,data):
    target=DATA/name;backup=P/'Before'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(target,backup)
    tmp=target.with_suffix('.chixiao-heavy.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(target)
catalog=runpy.run_path(str(P.parent/'ChixiaoBladeV1/catalog_extension.py'))['extend'](read('zhanmadao-modules.json'))
write('zhanmadao-modules.json',catalog)
gunsmith=read('melee-gunsmith.json')
option=next(o for c in gunsmith['columns'] if c['key']=='blade_1' for o in c['options'] if o['id']=='chixiao')
mechanism='重击改为快速二连斩：先下斩，再从落刀处向右上方挑斩。两刀均造成完整重击伤害，属于武技。出手体力消耗翻倍，蓄力期间每秒体力消耗不变。'
runpy.run_path(str(P.parent/'ChixiaoLegendaryV1/catalog_extension.py'))['extend_option'](option)
write('melee-gunsmith.json',gunsmith)
body_path=DATA/'player_body.json';body_bytes=body_path.read_bytes();body=json.loads(body_bytes.decode('utf-8-sig'))
body['clips']['Melee.FullBody.ChixiaoHeavy']=receipt['body_asset']
runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    body_path,body_bytes,body,owned_paths=[('clips','Melee.FullBody.ChixiaoHeavy')],producer=__file__)
designfile=P.parent/'ChixiaoBladeConceptV1/design.json';design=json.loads(designfile.read_text('utf-8'))
design['effect_proposal']={'status':'user_confirmed_integrated','revision':5,'effect_name':'赤霄双斩',
 'mechanism':mechanism,'hits':2,'damage_per_hit':'full_heavy_strike','category':'martial',
 'first_cut':'current_heavy_release','second_cut':'from_first_landing_to_upper_right',
 'charge_and_stamina':'one_original_charge_double_release_cost','release_stamina_multiplier':2,
 'attack_speed':'independent_martial_clock',
 'passive_attack_speed_mult':1.15,'heavy_trail':'crimson_blade_path',
 'beiwei':'both_hits_receive_martial_damage_and_range_once','game_integrated':True,
 'source':'../ChixiaoDoubleHeavyV1/','game_tested':False}
design['status']='appearance_and_effect_integrated';design['tier']='legendary';design['stats']={'attack_speed_mult':1.15}
designfile.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(published=True,runtime_tested=False)
(P/'publication.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_DOUBLE_HEAVY_PUBLISHED',len(receipt['assets']),flush=True)
