"""Requested offline workbench-copy audit; no editor or gameplay execution."""
import ast
import copy
import json
import re
from pathlib import Path
from apply_copy import without_copy
from copy_rules import apply_catalog, options

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DATA=ROOT/'Content/ColdSteelData'
items=json.loads((DATA/'items.json').read_text(encoding='utf-8-sig'))
catalogs={p.name:json.loads((DATA/p.name).read_text(encoding='utf-8-sig')) for p in (HERE/'before').glob('*.json')}
issues=[]
changes=[]
source_records=0
for name,current in catalogs.items():
    before=json.loads((HERE/'before'/name).read_text(encoding='utf-8-sig'))
    if without_copy(before)!=without_copy(current):issues.append(f'{name}: non-copy fields changed')
    if apply_catalog(name,copy.deepcopy(current),items)!=current:issues.append(f'{name}: copy rules not applied or not idempotent')
    def compare(a,b,path=''):
        if isinstance(a,dict) and isinstance(b,dict):
            for key in set(a)|set(b):
                if key in ('description','appearance','special_effects') or (key=='effects' and isinstance(b.get(key),list)):
                    if a.get(key)!=b.get(key):changes.append({'catalog':name,'path':path+'/'+key,'before':a.get(key),'after':b.get(key)})
                elif key in a and key in b:compare(a[key],b[key],path+'/'+key)
        elif isinstance(a,list) and isinstance(b,list):
            for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
    compare(before,current)
    for slot,option,weapon in options(current):
        source_records+=1
        where=f'{name}:{weapon}:{slot}:{option["id"]}'
        if not option.get('description','').strip():issues.append(where+': empty description')
        if 'special_effects' not in option:issues.append(where+': missing explicit mechanism field')
        for line in option['special_effects']:
            if '｜' not in line:issues.append(where+': missing mechanism title')
            if re.search(r'\s[+−-]\s*\d+(?:\.\d+)?%',line):issues.append(where+': percentage spacing')
        if any(x in option.get('appearance','') for x in ['流程接入前','数值改造已生效']):issues.append(where+': authoring status in player copy')

inventory=[]
secondary_source=(ROOT/'Source/FPSGAME/Weapons/TacticalDeviceVariants.h').read_text(encoding='utf-8-sig')
secondary=set(re.findall(r'TEXT\("(ue_[^"]+)"\)',secondary_source.split('inline bool SupportsSecondary')[1].split('inline FString')[0]))
common_runes={'strength_rune','haste_rune','resonance_rune','erosion_rune','conduction_rune'}


def add_inventory(weapon,groups,family):
    rows=[{'slot':slot,'id':o['id'],'name':o['name']} for slot,entries in groups.items() for o in entries]
    identity=[(r['slot'],r['id']) for r in rows]
    if len(identity)!=len(set(identity)):issues.append(weapon+': duplicate slot/id')
    item=items.get(weapon,{})
    inventory.append({'weapon':weapon,'name':item.get('name',weapon),'family':family,
                      'including_factory':len(rows),'modifications':sum(r['id']!='false' for r in rows),'options':rows})


guns=catalogs['gunsmith.json']
for weapon in guns['weapons']:
    wid=weapon['id'];allowed=list(weapon['allowed']);groups=copy.deepcopy(weapon['options'])
    if weapon.get('inherit_common_options',True):
        for slot,entries in guns.get('common_options',{}).items():
            if slot not in allowed:allowed.append(slot)
            existing=groups.setdefault(slot,[])
            existing.extend(o for o in entries if o['id'] not in {x['id'] for x in existing})
    binding=weapon.get('pistol_grip_surface',{})
    if binding.get('mesh'):
        groups['reargrip']=guns['pistol_grip_surface_options']+binding.get('exclusive_options',[])
        if 'reargrip' not in allowed:allowed.append('reargrip')
    if wid in secondary:
        groups['tactical_secondary']=groups['tactical']
        if 'tactical_secondary' not in allowed:allowed.append('tactical_secondary')
    add_inventory(wid,{k:v for k,v in groups.items() if k in allowed},'firearm')

for name in ['melee-gunsmith.json','bow-gunsmith.json','staff-gunsmith.json','tool-gunsmith.json',
             'warhammer-gunsmith.json','runebound-warhammer-gunsmith.json','thunder-god-hammer-gunsmith.json','kukri-gunsmith.json']:
    catalog=catalogs[name]
    family='tool' if name=='tool-gunsmith.json' else 'bow' if name=='bow-gunsmith.json' else 'staff' if name=='staff-gunsmith.json' else 'melee'
    for weapon in catalog.get('weapons',[{'id':catalog.get('weapon')}]):
        wid=weapon['id'];groups={}
        for col in catalog['columns']:
            slot=col['key'];entries=[]
            if not col.get('weapons') or wid in col['weapons']:
                entries=[{'id':'false','name':col['default']}]
            candidates=list(col.get('options',[]))
            if library:=col.get('options_library'):
                data=catalogs[library]
                candidates+=next(c['options'] for c in data['columns'] if c['key']==col['options_column']) if col.get('options_column') else data['options']
            for option in candidates:
                if option['id'] in col.get('excluded_options',[]):continue
                if slot=='rune':
                    permitted=common_runes|({'swift_mana_rune','destruction_mana_rune'} if wid=='ue_runebound_warhammer' else {'lei_ming_rune','hui_xiang_rune'} if wid=='ue_thunder_god_hammer' else set())
                    if option['id'] not in permitted:continue
                elif option.get('weapons') and wid not in option['weapons']:continue
                entries.append(option)
            groups[slot]=entries
        add_inventory(wid,groups,family)

melee={o['id']:o for _,o,_ in options(catalogs['melee-gunsmith.json'])}
for oid,words in {'frost_crystal':['智力×50%','精神×50%','不占用符文栏'],
                  'spirit_burst_rune':['智力×100%','精神×100%'],
                  'time_sand_gold':['0.6秒','30%','0.5秒','1秒']}.items():
    text=' '.join(melee[oid]['special_effects'])
    for word in words:
        if word not in text:issues.append(oid+': missing '+word)
for oid in ['frost_crystal','time_sand_gold']:
    if melee[oid].get('tier')!='legendary':issues.append(oid+': lost legendary tier')
    if melee[oid].get('weapons')!=['ue_rune_sword']:issues.append(oid+': changed exclusivity')
authors=json.loads((HERE/'author-sync.json').read_text(encoding='utf-8'))
for entry in authors:
    ast.parse((ROOT/entry['path']).read_text(encoding='utf-8-sig'))
ast.parse((ROOT/'SourceAssets/ApprenticeStaff20260927/attachment_copy.py').read_text(encoding='utf-8-sig'))
report={'scope':'offline catalog copy and display-source review; no gameplay execution',
        'catalogs':len(catalogs),'source_option_records':source_records,
        'weapons':sum(w['family']!='tool' for w in inventory),'tools':sum(w['family']=='tool' for w in inventory),
        'resolved_options_including_factory':sum(w['including_factory'] for w in inventory),
        'resolved_modifications':sum(w['modifications'] for w in inventory),
        'changed_copy_fields':len(changes),'non_copy_fields_preserved':not any('non-copy' in x for x in issues),
        'issues':issues,'inventory':inventory}
(HERE/'copy-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(HERE/'copy-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='inventory'},ensure_ascii=False))
for w in inventory:print(w['weapon'],w['modifications'])
raise SystemExit(bool(issues))
