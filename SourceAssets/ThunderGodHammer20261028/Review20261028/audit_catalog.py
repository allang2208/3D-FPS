"""User-requested offline checks against the live catalogs and on-disk dependencies."""
import json,hashlib,struct
from pathlib import Path
from PIL import Image
P=Path(__file__).resolve().parent;TASK=P.parent;ROOT=TASK.parents[1];DATA=ROOT/'Content/ColdSteelData'
ID='ue_thunder_god_hammer';rows=[];refs=set()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def check(label,ok,detail=None):rows.append({'check':label,'pass':bool(ok),'detail':detail})
def collect(v):
    if isinstance(v,str) and v.startswith('/Game/'):refs.add(v)
    elif isinstance(v,dict):
        for x in v.values():collect(x)
    elif isinstance(v,list):
        for x in v:collect(x)
items=read(DATA/'items.json');item=items[ID];base=items['ue_steel_warhammer']
catalog=read(DATA/item['modular_melee_catalog']);bench=read(DATA/'thunder-god-hammer-gunsmith.json')
check('live item equals published author definition',item==read(TASK/'item_definition.json'))
check('module author base equals runtime',catalog==read(TASK/'ModulesV1/catalog_base.json'))
check('gunsmith author base equals runtime',bench==read(TASK/'ModulesV1/workbench.json'))
check('weapon identity, two-handed type and runtime dispatcher',item['id']==ID and catalog['weapon']==ID and bench['weapon']==ID and item['isTwoHanded'] and item['tool_kind']=='warhammer')
check('no equipment rarity',not any(k in item for k in ('rarity','grade')))
for key in ('tool_viewmodel','viewmodel_mesh','tool_animation_prefix','tool_swing_sound','tool_sound','hit_sound'):
    check('shared dependency '+key,item[key]==base[key],item[key])
formula=read(DATA/'combat-weapon-formulas.json');a=formula[ID].copy();b=formula['ue_steel_warhammer'].copy();a.pop('source',None);b.pop('source',None)
check('independent formula retains current steel baseline',a==b)
check('six distinct original module slots',len(catalog['module_slots'])==len(set(catalog['module_slots']))==6)
check('five distinct gunsmith columns',len(bench['columns'])==len({c['key'] for c in bench['columns']})==5)
common_runes={'strength_rune','haste_rune','resonance_rune','erosion_rune','conduction_rune'}
for col in bench['columns']:
    slot=col['key'];lib=read(DATA/col['options_library']);options=col.get('options',[])
    if 'options_column' in col:options+=next(c['options'] for c in lib['columns'] if c['key']==col['options_column'])
    else:options+=lib['options']
    if slot=='rune':options=[o for o in options if o['id'] in common_runes]
    ids=[o['id'] for o in options]
    check('no duplicate options '+slot,len(ids)==len(set(ids)))
    expected=set(ids)|{'factory'};actual=set(catalog['slots'][slot])
    check('every live workbench option has fitted recipe '+slot,expected==actual,{'expected':sorted(expected),'actual':sorted(actual)})
    for key in (f'{ID}_category_{slot}',f'{ID}_{slot}_false'):
        f=DATA/'AttachmentIcons20260913'/(key+'.png')
        with Image.open(f) as im:
            im.load();check('factory icon '+key,im.width==im.height and im.width>=1024,list(im.size))
    for option in options:
        # Shared icon resolver uses slot_option, then bare option in the common directory.
        icon_slot='blade_2' if slot=='rune' else slot
        candidates=[DATA/'AttachmentIcons20260913'/(f'{icon_slot}_{option["id"]}.png')]
        check('shared icon exists '+slot+'/'+option['id'],any(p.exists() for p in candidates))
for row in read(TASK/'ModulesV1/exports.json')['parts']+read(TASK/'ModulesV1/adapted_exports.json')['parts']:
    spec=catalog['slots'][row['slot']][row['id']]
    check('module pivot agrees with export '+row['mesh'],spec['location_cm']==row['location_cm'])
collect(item);collect(catalog);collect(read(TASK/'animation_manifest.json')['first_person']);collect(read(TASK/'animation_manifest.json')['shared_grip_profile']);collect(read(TASK/'animation_manifest.json')['third_person']['shared_roles'])
refs.discard(item['tool_animation_prefix'])
for name in ('Idle','Equip','Swing','HitRecover'):refs.add(item['tool_animation_prefix']+name)
refs.add('/Game/Weapons/ThunderGodHammer20261028/ModulesV1/Runes/M_SilverRuneSurface_ThunderGodHammerShaftV1')
for ref in sorted(refs):
    f=ROOT/'Content'/(ref[6:].split('.')[0]+'.uasset');check('package exists '+ref,f.is_file())
with Image.open(DATA/item['ue_icon']) as im:
    im.load();check('inventory PNG has transparent background',im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255),{'size':list(im.size),'mode':im.mode})
source=TASK/'Original/Meshy_AI_Stormbreaker_Runehamm_1028015020_texture.glb'
check('archived source hash',hashlib.sha256(source.read_bytes()).hexdigest()==read(TASK/'authored.json')['source_sha256'])
check('cook directory registered','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/ThunderGodHammer20261028")' in (ROOT/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig'))
result={'count':len(rows),'failures':[r for r in rows if not r['pass']],'checks':rows,'asset_references':sorted(refs),'scope':'live catalogs, authorship, files; not asset deserialization or gameplay'}
(P/'catalog-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(rows),'failures':result['failures'],'asset_references':len(refs)},ensure_ascii=False))
