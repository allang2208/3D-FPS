from pathlib import Path
import json
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
items=json.loads((DATA/'items.json').read_text(encoding='utf-8-sig'))
weapons=[key for key,item in items.items() if item.get('isTwoHanded') and item.get('category')=='weapon_melee' and item.get('weaponType') in ['sword','blunt']]
common=['folded_steel','dark_iron','mithril','damascus_steel','meteoric_iron']
for filename in ['melee-gunsmith.json','warhammer-gunsmith.json','runebound-warhammer-gunsmith.json','thunder-god-hammer-gunsmith.json']:
    path=DATA/filename;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if filename=='melee-gunsmith.json':
        column=next(c for c in data['columns'] if c['key']=='blade_material')
        column['description']='选择刃部材质，保留符文与原有部件结构。'
        column['weapons']=weapons
        for option in column['options']:
            if option['id'] in common:option['weapons']=[w for w in weapons if w!='ue_frost_crystal_sword']
            elif option['id'] in ['frost_crystal','time_sand_gold']:
                option['weapons']=['ue_rune_sword'];option['tier']='legendary'
    else:
        column={'key':'blade_material','name':'锤部材质','default':'原装锤部材质',
                'description':'选择锤部材质，保留锤座、握持结构及符文。',
                'options_library':'melee-gunsmith.json','options_column':'blade_material',
                'excluded_options':['frost_crystal','time_sand_gold'],'options':[]}
        previous=next((c for c in data['columns'] if c['key']=='blade_material'),None)
        if previous:previous.update(column)
        else:data['columns'].insert(1,column)
    backup=P/'BeforeCatalog'/filename;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge '+filename)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'catalog-receipt.json').write_text(json.dumps({'weapons':weapons,'common':common,
    'rune_sword_legendary':['frost_crystal','time_sand_gold']},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('SHARED_MATERIAL_CATALOG_SAVED',len(weapons))
