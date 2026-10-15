"""User-requested scoped compatibility/source check. Does not simulate combat."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
D=ROOT/'Content/ColdSteelData'
def data(name):return json.loads((D/name).read_text(encoding='utf-8-sig'))
def src(name):return (ROOT/'Source/FPSGAME'/name).read_text(encoding='utf-8-sig')
checks=[]
def check(label,passed):checks.append({'check':label,'pass':bool(passed)})
cat=data('melee-gunsmith.json')
opts=next(c['options'] for c in cat['columns'] if c['key']=='blade_2')
matches=[o for o in opts if o['id']=='strength_rune']
check('one shared strength rune option',len(matches)==1)
opt=matches[0]
check('physical damage +10 percent',opt['stats']=={'physical_damage_mult':1.1})
check('unrestricted sword compatibility',not opt.get('weapons'))
hammer=data('warhammer-gunsmith.json')
column=next(c for c in hammer['columns'] if c['key']=='rune')
check('hammer references the same sword rune column',column['options_library']=='melee-gunsmith.json' and column['options_column']=='blade_2')
check('strength accepted by common-rune normalization','Rune==TEXT("strength_rune")' in src('Weapons/FrostSwordRunes.h'))
for path in ['Weapons/MeleeGunsmith.cpp','Weapons/WarhammerGunsmith.cpp']:
    check(path+' reads physical multiplier','TryGetNumberField(TEXT("physical_damage_mult"),Part.Melee.PhysicalDamage)' in src(path))
check('multiplier accumulated in common evaluator','R.Melee.PhysicalDamage*=M.PhysicalDamage' in src('Weapons/GunsmithSystem.cpp'))
damage=src('Weapons/WeaponDamagePanel.cpp')
check('physical multiplier consumed by base and added physical damage','R.BasePhysical*=Melee->PhysicalDamage' in damage and 'R.AddedPhysical*=Melee->PhysicalDamage' in damage)
check('sword gameplay evaluator passes modifiers','ColdSteelWeaponDamage::Evaluate(Item,Profile,BaseDamage,&R.Modifiers)' in src('Weapons/MeleeWeaponStats.cpp'))
check('hammer gameplay evaluator passes modifiers','ColdSteelWeaponDamage::Evaluate(Item,Profile,Processed,Blunt?&BluntModifiers:nullptr)' in src('Production/ProductionToolStats.cpp'))
visual=src('Weapons/MeleeRuneVisual.cpp')
check('rune visual mode recognized','VisualRune==TEXT("strength_rune"))?2:-1' in visual)
check('red core and glow palette','FLinearColor(.82f,.012f,.018f,1.f)' in visual and 'FLinearColor(1.f,.025f,.032f,1.f)' in visual)
check('palette applied to native and overlay materials','ApplyCommonRunePalette(SurfaceMID,VisualRune)' in visual and 'ApplyCommonRunePalette(MID,VisualRune)' in visual)
check('palette restored when switching away','Material->Parent->GetVectorParameterValue' in visual)
check('hammer shaft application','ColdSteelMeleeRune::Apply(Module,SelectedRune,Item.Definition)' in src('Weapons/ModularSwordVisual.cpp'))
icon=src('UI/M4GunsmithLayout.cpp')
check('hammer shared icon alias','Weapon==TEXT("ue_steel_warhammer")&&SlotKey==TEXT("rune")' in icon and 'TEXT("blade_2"):TacticalDeviceVariants::IconSlot' in icon)
items=data('items.json')
ids=[w['id'] if isinstance(w,dict) else w for w in cat['weapons']]+[hammer['weapon']]
rows=[]
for ident in ids:
    item=items[ident]
    is_hammer=ident==hammer['weapon']
    check(ident+' two-handed classification',bool(item.get('isTwoHanded')) and item.get('weaponType')==('blunt' if is_hammer else 'sword'))
    module_file=item.get('modular_melee_catalog') or item.get('modular_sword_catalog') or {
        'ue_rune_sword':'rune-sword-modules.json','ue_frost_crystal_sword':'frost-sword-modules.json',
        'ue_steel_warhammer':'warhammer-modules.json'}.get(ident)
    module=data(module_file)
    slot='shaft' if is_hammer else 'blade_1'
    variants=[{'variant':key,**value} for key,value in module['slots'][slot].items() if 'mesh' in value]
    rows.append({'id':ident,'name':item.get('name',ident),'slot':'rune' if is_hammer else 'blade_2',
        'module_catalog':module_file,'rune_mesh_slot':slot,'variants':variants,'physical_multiplier':opt['stats']['physical_damage_mult']})
    if is_hammer:check('hammer appearance registered','strength_rune' in module['slots']['rune'])
    check(ident+' factory rune carrier mesh','factory' in module['slots'][slot])
mask=P.parent/'T_Mask_strength_rune.png'
icon_src=P.parent/'blade_2_strength_rune.png'
icon_dst=D/'AttachmentIcons20260913/blade_2_strength_rune.png'
check('deployed shared icon equals produced icon',hashlib.sha256(icon_src.read_bytes()).digest()==hashlib.sha256(icon_dst.read_bytes()).digest())
sources=['Weapons/FrostSwordRunes.h','Weapons/MeleeRuneVisual.cpp','Weapons/ModularSwordVisual.cpp']
dll=ROOT/'Binaries/Win64/UnrealEditor-FPSGAME.dll'
check('disk Editor binary newer than rune source edits',dll.stat().st_mtime>=max((ROOT/'Source/FPSGAME'/p).stat().st_mtime for p in sources))
report={'scope':'source and catalogue contracts; no native gameplay execution','checks':checks,'weapons':rows,
        'passed':all(c['pass'] for c in checks),'checks_total':len(checks),
        'native_combat_tested':False,'inventory_or_saves_modified':False}
(P/'source_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'checks':len(checks),'weapons':[(w['id'],w['name']) for w in rows],
    'failed':[c['check'] for c in checks if not c['pass']]},ensure_ascii=False))
