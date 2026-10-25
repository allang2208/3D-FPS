"""Merge the approved shared seat into current catalogs, preserving other edits."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved.get('complete'):raise RuntimeError('Save all assets first')
part='ancient_breaking_seal_seat'
option={'id':part,'name':'破势古印座','tier':'special','description':'古铜包覆锻铁的八棱锤座，凹刻古印以暗朱砂嵌底，细银回纹沿铜壳收边。','appearance':'古铜锻铁 · 凹刻古印 · 细银回纹',
    'stats':{'stamina_mult':1.1,'attack_speed_mult':0.95,'toughness_damage_mult':1.05,'physical_damage_mult':1.05},
    'effects':[{'text':'体力消耗 +10%','benefit':-1},{'text':'攻击速度 -5%','benefit':-1},{'text':'韧性伤害 +5%','benefit':1},{'text':'物理伤害 +5%','benefit':1}],
    'special_effects':['破势印｜快速近战有效命中目标后施加破势印，持续8秒。目标受到的物理伤害提高15%，受到的韧性伤害提高25%。重复命中刷新时间，效果不叠加。','共击破势｜印记期间，后续攻击与队友的相应伤害均可受益；原有群体快速近战会分别给实际命中的目标施印。']}
status={'type':'breakingSeal','icon':'印','name':'破势印','color':'#bc8c62','description':'被装有破势古印座的双手锤快速近战命中后，受到的物理伤害提高15%，受到的韧性伤害提高25%，持续8秒。重复命中刷新时间，效果不叠加。','kind':'debuff','group':'combat'}
jobs=[('Content/ColdSteelData/common-hammer-seats.json','options',option),('Content/ColdSteelData/status_effects.json','effects',status)]
for variant,runtime,author,interface in [
 ('Steel','warhammer-modules.json','SteelWarhammer20261014','warhammer_factory_v1'),
 ('Runebound','runebound-warhammer-modules.json','RuneboundWarhammer20261022','runebound_warhammer_modular_v1')]:
    spec=dict(saved['parts'][variant],location_cm=[0,0,0],appearance=option['appearance'],interface=interface,shared_option_library='common-hammer-seats.json',model_revision='AncientSealBuildV1')
    jobs += [('Content/ColdSteelData/'+runtime,'model',spec),('SourceAssets/'+author+'/ModulesV1/catalog_base.json','model',spec)]
written=[]
for relative,kind,entry in jobs:
    file=ROOT/relative;before=file.read_bytes();value=json.loads(before.decode('utf-8-sig'))
    if kind=='model':value['slots']['head_mount'][part]=entry
    else:
        key='type' if kind=='effects' else 'id';value[kind]=[v for v in value[kind] if v.get(key)!=entry[key]]+[entry]
    backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog change '+relative)
    tmp=file.with_suffix('.ancient-seal.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if file.read_bytes()!=before:raise RuntimeError('Concurrent catalog change before commit '+relative)
    os.replace(tmp,file);written.append(relative)
icon='head_mount_'+part+'.png';shutil.copy2(P/icon,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon)
(P/'catalog_option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2),encoding='utf-8')
concept=P.parent/'AncientSealConceptV1/design.json';data=json.loads(concept.read_text('utf-8'))
data.update(status='approved_design_modeled_and_integrated',model_authored=True,runtime_integrated=True,model_revision='AncientSealBuildV1',user_visual_acceptance=False)
concept.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'published.json').write_text(json.dumps({'complete':True,'catalogs':written,'option':option,'saved_assets':saved['assets'],'game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('ANCIENT_SEAL_SHARED_SPECIAL_MODIFICATION_PUBLISHED')
