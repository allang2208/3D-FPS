"""Merge this batch's 12 choices, retaining their authored gameplay modifiers."""
import copy,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
DATA=P.parents[1]/'Content/ColdSteelData'
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Import and save before catalog publication')
components=json.loads((P/'components.json').read_text(encoding='utf-8'))['variants']
runes=json.loads((P/'runes.json').read_text(encoding='utf-8'))['runes']
entries=components+runes
descriptions={
 'knife_grip_checkered':'石墨灰胶质握面布满细密棱纹，保留金属铆钉。',
 'knife_grip_leather':'深栗色皮革斜向包覆握面，浅缝衔接原有轮廓。',
 'knife_grip_laminate':'深浅木层形成流动纹理，表面呈细腻缎光。',
 'knife_pommel_steel':'包钢尾座衔接银灰边缘，保留原有穿绳孔。',
 'knife_pommel_faceted':'古铜色尾座采用宽阔棱面，保留原有穿绳孔。',
 'knife_pommel_ringed':'深灰尾座下沿环绕三道浅纹，银灰边缘清晰分层。',
 'knife_lanyard_braid':'深橄榄色短绳呈交错编织纹理。',
 'knife_lanyard_tassel':'短绳连接古铜环，下垂四条短皮穗。',
 'knife_lanyard_tag':'短绳与金属扣环连接方牌，两道细银纹装饰牌面。',
 'knife_mark_wing':'暖金色折翼纹样沿刀面展开。',
 'knife_mark_knot':'银灰环结纹样交错排列，保留通透留白。',
 'knife_mark_peaks':'深灰三峰纹样与小菱形印记点缀刀面。'}
library_name='shared-knife-component-options.json'
authored={o['id']:o for c in json.loads((P/library_name).read_text(encoding='utf-8-sig'))['columns'] for o in c['options']}
library_path=DATA/library_name
library=json.loads(library_path.read_text(encoding='utf-8-sig')) if library_path.exists() else {'version':1,'family':'knife_components','columns':[]}
for slot in ('grip','pommel','lanyard','blade_2'):
    column=next((c for c in library['columns'] if c['key']==slot),None)
    if column is None:column={'key':slot,'options':[]};library['columns'].append(column)
    owned={e['id'] for e in entries if e['slot']==slot}
    column['options']=[o for o in column.get('options',[]) if o.get('id') not in owned]
    for e in entries:
        if e['slot']==slot:column['options'].append({'id':e['id'],'name':e['name'],'description':descriptions[e['id']],
            'appearance':descriptions[e['id']],'stats':copy.deepcopy(authored[e['id']].get('stats',{})),
            'effects':copy.deepcopy(authored[e['id']].get('effects',[])),
            'special_effects':copy.deepcopy(authored[e['id']].get('special_effects',[]))})
menu_path=DATA/'kukri-gunsmith.json';assembly_path=DATA/'kukri-modules.json'
menu=json.loads(menu_path.read_text(encoding='utf-8-sig'))
assembly=json.loads(assembly_path.read_text(encoding='utf-8-sig'))
for slot in ('grip','pommel','lanyard','blade_2'):
    column=next(c for c in menu['columns'] if c['key']==slot)
    source=next(c for c in library['columns'] if c['key']==slot)
    if column.get('options_library') not in (None,library_name):
        owned={e['id'] for e in entries if e['slot']==slot}
        column['options']=[o for o in column.get('options',[]) if o.get('id') not in owned]+source['options']
    else:column['options_library']=library_name;column['options_column']=slot
for entry in components:
    spec=copy.deepcopy(assembly['slots'][entry['slot']]['factory'])
    spec['mesh']=entry['mesh'];spec['appearance']=descriptions[entry['id']]
    assembly['slots'][entry['slot']][entry['id']]=spec
for entry in runes:
    assembly['slots']['blade_2'][entry['id']]={'appearance':descriptions[entry['id']],
        'surface_materials':receipt['rune_surfaces'][entry['id']]}
for part_id,metadata in receipt['root_materials'].items():
    # Explicit base binding restores each blade when the surface ornament is removed.
    assembly['slots']['blade_1'][part_id].update(metadata)
before=P/'Before';before.mkdir(exist_ok=True)
for name,value in [(library_name,library),('kukri-gunsmith.json',menu),('kukri-modules.json',assembly)]:
    target=DATA/name
    if target.exists() and not (before/name).exists():shutil.copy2(target,before/name)
    text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    (P/name).write_text(text,encoding='utf-8');target.write_text(text,encoding='utf-8')
jobs=[]
for e in entries:
    dest=DATA/'AttachmentIcons20260913'/(e['icon_key']+'.png')
    shutil.copy2(e['icon'],dest);jobs.append({'id':e['id'],'key':e['icon_key'],'source':e['icon'],'destination':str(dest)})
(P/'publication_receipt.json').write_text(json.dumps({'complete':True,'new_choices':12,'retained_blade_choices':3,
    'weapon':'ue_kukri','stats_authored':True,'runtime_tested':False,'icons':jobs},ensure_ascii=False,indent=2),encoding='utf-8')
print('KUKRI_COMPONENT_CHOICES_PUBLISHED 12 new + 3 existing blade choices')
