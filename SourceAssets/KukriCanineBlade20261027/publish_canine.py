"""Publish only the saved Canine option and its blade/rune/icon mappings."""
import json, shutil
from pathlib import Path

P=Path(__file__).resolve().parent;PROJECT=P.parents[1]
receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Asset import has not completed')
entry=json.loads((P/'canine.json').read_text(encoding='utf-8'))
option={'id':'canine_blade','name':'犬牙刀身',
    'description':'弧形刃口开出连续犬牙锯齿，深灰钢面衬以银色齿刃。',
    'appearance':'弧形刃口开出连续犬牙锯齿，深灰钢面衬以银色齿刃。',
    'effects':[{'text':'物理伤害+20%','benefit':1},{'text':'韧性伤害−50%','benefit':-1}],
    'special_effects':['流血｜本刀每次攻击命中敌人叠加1层流血，适用于普通攻击和武技；同次攻击对同一目标仅触发一次，双持各刀独立结算。',
        '叠层｜每秒按目标当前生命值的1%×流血层数造成伤害；新增层数刷新衰减计时，之后每10秒减少1层。'],
    'stats':{'physical_damage_mult':1.20,'toughness_damage_mult':.50,'melee_hit_bleed_stacks':1}}

def save(path,data):
    relative=path.relative_to(PROJECT);before=P/'Before'/relative
    if path.exists() and not before.exists():before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,before)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for directory in (PROJECT/'Content/ColdSteelData',P.parent/'KukriComponentVariants20261026'):
    path=directory/'kukri-gunsmith.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    column=next(c for c in data['columns'] if c['key']=='blade_1')
    column['options']=[o for o in column.get('options',[]) if o['id']!='canine_blade']+[option]
    save(path,data)
    path=directory/'kukri-modules.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    data['slots']['blade_1']['canine_blade']={
        'mesh':receipt['mesh'],'location_cm':[0,0,0],'appearance':option['appearance'],
        'trace_base_cm':entry['trace_base_cm'],'trace_tip_cm':entry['trace_tip_cm'],
        'rune_dimensions_cm':[10,2.5,entry['bounds'][2][1]*100],
        'material_slot_names':['M_Kukri_Canine'],'materials':{'M_Kukri_Canine':receipt['material']}}
    for rune,surfaces in receipt['rune_surfaces'].items():
        data['slots']['blade_2'][rune].setdefault('surface_materials',{}).update(surfaces)
    save(path,data)

icon=PROJECT/'Content/ColdSteelData/AttachmentIcons20260913/ue_kukri_blade_1_canine_blade.png'
if icon.exists():
    before=P/'Before'/icon.relative_to(PROJECT)
    if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(icon,before)
shutil.copy2(P/'Icons/ue_kukri_blade_1_canine_blade.png',icon)
(P/'publication-receipt.json').write_text(json.dumps({'complete':True,'option':option,'icon_png':str(icon),
    'length_scale':1.,'saved_assets':receipt['saved_assets'],'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('CANINE_OPTION_PUBLISHED')
