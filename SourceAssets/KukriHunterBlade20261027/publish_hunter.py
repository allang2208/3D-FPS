"""Publish the imported Hunter option without replacing unrelated catalog entries."""
import json, shutil
from pathlib import Path

P=Path(__file__).resolve().parent;PROJECT=P.parents[1]
receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Asset import has not completed')
entry=json.loads((P/'hunter.json').read_text(encoding='utf-8'))
option={'id':'hunter_blade','name':'猎手刀身',
    'description':'加长弧形刀身，石墨灰缎面钢材配细磨银色刃口。',
    'appearance':'加长弧形刀身，石墨灰缎面钢材配细磨银色刃口。',
    'effects':[{'text':'攻击距离+25%','benefit':1},{'text':'物理伤害+10%','benefit':1},{'text':'攻击体力消耗+25%','benefit':-1}],
    'stats':{'range_mult':1.25,'physical_damage_mult':1.10,'stamina_mult':1.25}}
def save(path,data):
    relative=path.relative_to(PROJECT);before=P/'Before'/relative
    if path.exists() and not before.exists():before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,before)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for directory in (PROJECT/'Content/ColdSteelData',P.parent/'KukriComponentVariants20261026'):
    path=directory/'kukri-gunsmith.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    column=next(c for c in data['columns'] if c['key']=='blade_1')
    column['options']=[o for o in column.get('options',[]) if o['id']!='hunter_blade']+[option]
    save(path,data)
    path=directory/'kukri-modules.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    data['slots']['blade_1']['hunter_blade']={
        'mesh':receipt['mesh'],'location_cm':[0,0,0],'appearance':option['appearance'],
        'trace_base_cm':entry['trace_base_cm'],'trace_tip_cm':entry['trace_tip_cm'],
        'rune_dimensions_cm':[10,2.5,entry['bounds'][2][1]*100],
        'material_slot_names':['M_Kukri_Hunter'],'materials':{'M_Kukri_Hunter':receipt['material']}}
    for rune,surfaces in receipt['rune_surfaces'].items():
        data['slots']['blade_2'][rune].setdefault('surface_materials',{}).update(surfaces)
    save(path,data)

icon=PROJECT/'Content/ColdSteelData/AttachmentIcons20260913/ue_kukri_blade_1_hunter_blade.png'
if icon.exists():
    before=P/'Before'/icon.relative_to(PROJECT)
    if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(icon,before)
shutil.copy2(P/'Icons/ue_kukri_blade_1_hunter_blade.png',icon)
(P/'publication-receipt.json').write_text(json.dumps({'complete':True,'option':option,'icon_png':str(icon),
    'length_scale':1.5,'saved_assets':receipt['saved_assets'],'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('HUNTER_OPTION_PUBLISHED')
