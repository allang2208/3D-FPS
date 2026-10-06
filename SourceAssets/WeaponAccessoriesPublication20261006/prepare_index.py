"""Prepare a scoped Git index without replacing mixed working files or the real index."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parents[2]
O = Path(__file__).parent
SCRATCH = P / 'Saved/WeaponAccessoriesPublication20261006'
SCRATCH.mkdir(parents=True, exist_ok=True)
BASE = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P, text=True).strip()
INDEX = SCRATCH / 'publication.index'
ENV = dict(os.environ, GIT_INDEX_FILE=str(INDEX))

def git(*args, data=None, env=ENV):
    return subprocess.check_output(['git', *args], cwd=P, input=data, env=env)

def head(path):
    return git('show', BASE + ':' + path).decode('utf-8-sig').replace('\r\n', '\n')

def work(path):
    return (P / path).read_text(encoding='utf-8-sig')

contents = {}
selections = {}

def add(path, text=None):
    contents[path] = work(path) if text is None else text

def select(path, predicate):
    before, after = head(path).splitlines(True), work(path).splitlines(True)
    out, chosen = [], []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        old, new = ''.join(before[a:b]), ''.join(after[c:d])
        use = tag != 'equal' and predicate(old, new)
        out.extend(after[c:d] if use else before[a:b])
        if use:
            chosen.append(dict(before_line=a+1, old=old, new=new))
    if not chosen:
        raise RuntimeError('No selected edits: ' + path)
    selections[path] = chosen
    add(path, ''.join(out))

def block(text, start):
    i = text.index(start)
    a = text.index('{', i)
    depth = 0
    for b in range(a, len(text)):
        depth += (text[b] == '{') - (text[b] == '}')
        if depth == 0:
            return text[i:b+1]
    raise RuntimeError(start)

whole = [
 'Source/FPSGAME/FPSGAMEConsumableUse.cpp',
 'Source/FPSGAME/Items/FPSPotionUseComponent.cpp',
 'Source/FPSGAME/Items/FPSPotionUseComponent.h',
 'Source/FPSGAME/Items/FPSConsumableAuditCommandlet.cpp',
 'Source/FPSGAME/Items/FPSConsumableAuditCommandlet.h',
 'Source/FPSGAME/Production/ProductionToolComponent.h',
 'Source/FPSGAME/Weapons/Bow/BowWeaponComponent.h',
 'Source/FPSGAME/Weapons/Staff/StaffWeaponComponent.h',
 'Source/FPSGAME/Weapons/Unarmed/FPSUnarmedIdleComponent.h',
 'Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',
 'Source/FPSGAME/Weapons/PistolDualWieldComponent.h',
 'Source/FPSGAME/Weapons/LegendaryTacticalStock.h',
 'Source/FPSGAME/Weapons/TacticalDeviceVariants.h',
 'Source/FPSGAME/Weapons/TacticalDeviceComponent.h',
 'Source/FPSGAME/Weapons/SkeletonStockVisual.cpp',
 'Source/FPSGAME/UI/ColdSteelUIStyle.h',
 'Source/FPSGAME/UI/M4GunsmithWidget.h',
 'SourceAssets/G18AttachmentRepair20260930/import_repair.py',
 'SourceAssets/G18Integration20260929/import_assets.py',
 'SourceAssets/RSH12Integration20261003/prepare_delivery.py',
 'Tools/Weapons/g18_holographic_material.py',
]
for path in whole:
    add(path)

path = 'Source/FPSGAME/FPSGAMECharacter.cpp'
text, current = head(path), work(path)
for marker in ('    if (bPresentationOnly)\n', 'bool AFPSGAMECharacter::TriggerRifleStockMelee()'):
    text = text.replace(block(text, marker), block(current, marker), 1)
add(path, text)

select('Source/FPSGAME/FPSGAMECharacter.h', lambda old,new:
       'UFPSConsumableAuditCommandlet' in new or 'CanBeginConsumableUse' in new)
select('Source/FPSGAME/Weapons/RuneSwordComponent.h', lambda old,new:
       'UFPSConsumableAuditCommandlet' in new or 'CanReleaseSupportHand' in new)
select('Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp', lambda old,new:
       any(s in new for s in ('TacticalDeviceVariants', 'RequestedVariant', 'BlessedDotMaterial', 'BlessedLaser')))
select('Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp', lambda old,new: 'ue_super90' not in new)
select('Source/FPSGAME/UI/ColdSteelIconResources.cpp', lambda old,new:
       any(s in new for s in ('LegendaryTacticalStock', 'TacticalDeviceVariants')))
select('Config/DefaultGame.ini', lambda old,new: 'LegendaryStock20261006' in new)

# Publish the red-card dependency without unrelated new melee identities or grouping.
path = 'Source/FPSGAME/Weapons/GunsmithModificationTier.h'
text = work(path)
text = text.replace('    if(Weapon==TEXT("ue_xuanchi_zhenyue")&&SlotKey==TEXT("blade_2")&&(Id==TEXT("zhenmo_rune")||Id==TEXT("jingang_rune")))\n        return EGunsmithModificationTier::Legendary;\n', '')
text = text.replace('        (Weapon==TEXT("ue_xuanchi_zhenyue") && SlotKey==TEXT("guard") && Id==TEXT("panchi_zhanyue")) ||\n', '')
text = text.replace('((Weapon==TEXT("ue_tang_dao")||Weapon==TEXT("ue_xuanchi_zhenyue")) &&', '(Weapon==TEXT("ue_tang_dao") &&')
add(path, text)
path = 'Source/FPSGAME/UI/M4GunsmithLayout.cpp'
text = work(path).replace('HeightOverride(186)', 'HeightOverride(158)')
a = text.index('    // A common melee option has one icon')
b = text.index('    const FString IconKey=', a)
text = text[:a] + '    const bool UseWeaponIcon=!SharedFirearmOption&&FPaths::FileExists(IconDirectory/(WeaponIconKey+TEXT(".png")));\n' + text[b:]
add(path, text)

# Merge only the two requested options, preserving all unrelated catalog entries in HEAD.
path = 'Content/ColdSteelData/gunsmith.json'
base_text = head(path)
base, current = json.loads(base_text), json.loads(work(path))
current_weapons = {w['id']:w for w in current['weapons']}
for weapon in base['weapons']:
    variants = current_weapons[weapon['id']]['options'].get('stock', [])
    wanted = [v for v in variants if v['id'] == 'legendary_adjustable_tactical_stock']
    if wanted:
        target = weapon['options'].setdefault('stock', [])
        target[:] = [v for v in target if v['id'] != wanted[0]['id']] + wanted
base.setdefault('common_options', {})['tactical'] = [v for v in current['common_options']['tactical'] if v['id'] == 'blessed_laser']
# Keep the existing catalog's formatting outside the edited option arrays.
decoder = json.JSONDecoder()
spans = {}
def locate(pos=0, keys=()):
    while base_text[pos].isspace(): pos += 1
    start = pos
    if base_text[pos] == '{':
        pos += 1
        while True:
            while base_text[pos].isspace(): pos += 1
            if base_text[pos] == '}': pos += 1; break
            key, pos = decoder.raw_decode(base_text, pos)
            while base_text[pos].isspace(): pos += 1
            assert base_text[pos] == ':'
            pos = locate(pos+1, keys+(key,))
            while base_text[pos].isspace(): pos += 1
            if base_text[pos] == ',': pos += 1
    elif base_text[pos] == '[':
        pos += 1; index = 0
        while True:
            while base_text[pos].isspace(): pos += 1
            if base_text[pos] == ']': pos += 1; break
            pos = locate(pos, keys+(index,)); index += 1
            while base_text[pos].isspace(): pos += 1
            if base_text[pos] == ',': pos += 1
    else:
        _, pos = decoder.raw_decode(base_text, pos)
    spans[keys] = (start, pos)
    return pos
locate()
edits = []
original = json.loads(base_text)
for index, weapon in enumerate(base['weapons']):
    wanted = [v for v in weapon['options'].get('stock',[]) if v['id']=='legendary_adjustable_tactical_stock']
    if not wanted: continue
    start,end = spans[('weapons',index,'options','stock')]
    old = base_text[start:end]
    closing_indent = len(old.rsplit('\n',1)[-1])-1
    item_indent = ' '*(closing_indent+2)
    new_item = item_indent+json.dumps(wanted[0],ensure_ascii=False,indent=2).replace('\n','\n'+item_indent)
    old_items = old[:-1].rstrip()
    edits.append((start,end,old_items+(',' if original['weapons'][index]['options']['stock'] else '')+'\n'+new_item+'\n'+' '*closing_indent+']'))
common = json.dumps(base['common_options'],ensure_ascii=False,indent=2).replace('\n','\n  ')
if ('common_options',) in spans:
    start,end=spans[('common_options',)];edits.append((start,end,common))
else:
    end=spans[()][1]-1
    prior=base_text[:end].rstrip()
    edits.append((len(prior),end,',\n  "common_options": '+common+'\n'))
for start,end,value in sorted(edits,reverse=True):
    base_text=base_text[:start]+value+base_text[end:]
if json.loads(base_text)!=base: raise RuntimeError('Catalog scope merge mismatch')
add(path,base_text)

source_dirs = [
 'SourceAssets/G18HolographicTransparency20261005', 'SourceAssets/G18OpticSeatReview20261005',
 'SourceAssets/BlessedLaser20261006', 'SourceAssets/RSH12InventoryIcon20261006',
 'SourceAssets/RSH12Mechanics20261006', 'SourceAssets/ThermalScope20261006',
 'SourceAssets/LegendaryStock20261006', 'SourceAssets/WeaponAccessoriesPublication20261006',
]
tool_dirs = ['Tools/Weapons/' + s for s in ('BlessedLaser20261006','LegendaryStock20261006','ThermalScope20261006','M4QuickMeleeTiming20261006')]
for directory in source_dirs + tool_dirs:
    for file in sorted((P / directory).rglob('*')):
        if file.is_file() and file.suffix in ('.py','.ps1','.md','.hlsl') and 'Research' not in file.parts and '__pycache__' not in file.parts:
            add(file.relative_to(P).as_posix())
for path in (
 'SourceAssets/BlessedLaser20261006/Model/MountRepair/Inputs/authoring-v1.json',
 'SourceAssets/BlessedLaser20261006/Model/MountRepair/surface_plan.json',
 'SourceAssets/WeaponAccessoriesPublication20261006/archive-manifest.json',
):
    add(path)
docs = ['Docs/Weapons/' + name + '-20261006.md' for name in (
 'adjustable-tactical-stock', 'blessed-laser', 'thermal-scope', 'rsh12-inventory-icon',
 'rsh12-mechanical-presentation', 'm4-quick-melee-timing', 'weapon-accessories-publication')]
docs += ['Docs/Weapons/g18-holographic-transparency-20261005.md', 'Docs/Items/consumable-weapon-handoff-20261006.md']
for path in docs:
    add(path)
for relative in (
 'ue5-weapon-workflow/references/attachment-fit-and-emission.md',
 'ue5-weapon-workflow/references/stocks.md',
 'ue5-weapon-workflow/references/revolver-mechanical-binding.md',
 'ue5-fps-arms-animation/references/food-and-drink-grasp.md',
 'ue5-fps-arms-animation/references/quick-melee-contact-recovery.md',
):
    add('skills/' + relative)
select('skills/ue5-weapon-workflow/SKILL.md', lambda old,new: 'attachment-fit-and-emission.md' in new)

ignore = '\n# Weapon accessories 2026-10-06: recipes only; licensed meshes, images and receipts stay local.\n'
for directory in source_dirs:
    ignore += '/' + directory + '/**\n!/' + directory + '/**/\n'
    for extension in ('py','ps1','md'):
        ignore += '!/' + directory + '/**/*.' + extension + '\n'
    ignore += '/' + directory + '/**/Research/\n'
for directory in tool_dirs:
    ignore += '/' + directory + '/*.txt\n/' + directory + '/*.json\n'
for path in ('SourceAssets/BlessedLaser20261006/Model/MountRepair/Inputs/authoring-v1.json',
             'SourceAssets/BlessedLaser20261006/Model/MountRepair/surface_plan.json',
             'SourceAssets/WeaponAccessoriesPublication20261006/archive-manifest.json',
             'SourceAssets/WeaponAccessoriesPublication20261006/published-files.json'):
    ignore += '!/' + path + '\n'
marker = '# Weapon accessories 2026-10-06:'
current_ignore = work('.gitignore')
if marker not in current_ignore:
    (P / '.gitignore').write_text(current_ignore.rstrip() + '\n' + ignore, encoding='utf-8')
add('.gitignore', head('.gitignore').rstrip() + '\n' + ignore)

manifest = dict(base=BASE, files=[dict(path=p, bytes=len(t.encode('utf-8')), partial=t!=work(p)) for p,t in sorted(contents.items())])
manifest_path = 'SourceAssets/WeaponAccessoriesPublication20261006/published-files.json'
(P / manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
add(manifest_path)
git('read-tree', BASE)
for path, text in contents.items():
    candidate = SCRATCH / 'Candidates' / path
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(text, encoding='utf-8', newline='\n')
    blob = git('hash-object', '-w', '--stdin', data=text.encode('utf-8')).decode().strip()
    git('update-index', '--add', '--cacheinfo', '100644', blob, path)
(SCRATCH / 'selected-edits.json').write_text(json.dumps(selections, ensure_ascii=False, indent=2), encoding='utf-8')
diff = git('diff', '--cached', '--binary', BASE)
(SCRATCH / 'staged.patch').write_bytes(diff)
print(json.dumps(dict(base=BASE,index=str(INDEX),files=len(contents),diff_bytes=len(diff))))
