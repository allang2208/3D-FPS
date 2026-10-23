"""Record production receipts and the shared animation dependency map, without tests."""
import json
import re
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
BASE = '/Game/Weapons/SteelWarhammer20261014/'
PICKAXE = '/Game/Items/ProductionTools/RusticPickaxe20260919/A_RusticPickaxe_'
def path(package):
    return package + '.' + package.rsplit('/', 1)[-1]

roles = {role: path(PICKAXE + role) for role in ('Idle', 'Equip', 'Swing', 'HitRecover')}
roles['SprintCarry'] = path(BASE + 'SprintDragV1/A_Warhammer_SprintCarry')
combo_header = (ROOT / 'Source/FPSGAME/Production/ProductionBluntCombo.h').read_text(encoding='utf-8-sig')
match = re.search(r'Clips\[\].*?\{(.*?)\}', combo_header, re.S)
if match:
    for role in re.findall(r'TEXT\("([^"]+)"\)', match[1]):
        roles[role] = path(BASE + 'NormalComboV4/A_Warhammer_' + role)
for role in ('HeavyCharge', 'HeavyRelease'):
    roles[role] = path(BASE + 'HeavySlamV4/A_Warhammer_' + role)
for role, folder in [('Whirlwind','WhirlwindV1'), ('Uppercut','UppercutV1'),
                     ('Inspect','InspectV1'), ('InspectWalk','InspectV1'),
                     ('QuickCombat','QuickCombatLeftWristV7')]:
    roles[role] = path(BASE + folder + '/A_Warhammer_' + role)
for role in ('GuardEnter', 'GuardHold', 'GuardHit', 'GuardBreak', 'GuardExit'):
    roles[role] = path(BASE + 'GuardV1/A_Warhammer_' + role)
body_config = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
body_roles = {}
def collect_body_roles(value):
    if isinstance(value, dict):
        for key, entry in value.items():
            if key.startswith('Warhammer.') and isinstance(entry, str):
                body_roles[key] = entry
            collect_body_roles(entry)
    elif isinstance(value, list):
        for entry in value:
            collect_body_roles(entry)
collect_body_roles(body_config)
manifest = {
    'weapon': 'ue_runebound_warhammer', 'name': '符文战锤',
    'first_person': roles,
    'shared_grip_profile': path(BASE + 'RhythmClearanceV2/DA_Warhammer_Clearance'),
    'procedural': ['two-hand walking stride', 'sprint blend', 'charge return/cancellation',
                   'ground planting / impact hold / recovery', 'left-hand casting and return'],
    'third_person': {
        'configuration': 'Content/ColdSteelData/player_body.json (existing shared configuration)',
        'dispatch': 'Tool / warhammer',
        'shared_roles': body_roles,
        'consumers': ['FPSPlayerBodyActions.cpp', 'FPSPlayerBodyAnimInstance.cpp', 'FPSPlayerBodyMotion.cpp'],
        'policy': 'Share every current warhammer locomotion, action and casting mapping; capture the new static attachment from the live viewmodel',
    },
    'animation_assets_created': 0, 'tested': False,
}
(P / 'animation_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
delivery = {'weapon': 'ue_runebound_warhammer', 'name': '符文战锤', 'tested': False,
    'authoring': json.loads((P / 'authored.json').read_text(encoding='utf-8-sig')),
    'source_license': 'User-provided Meshy GLB; retained locally; no public redistribution performed',
    'animation_license': 'Reuse existing project-owned/licensed animations in place; no new external donor',
    'animation_manifest': str(P / 'animation_manifest.json'),
    'inventory': 'GrantStartingArmory, idempotent warehouse grant to existing/new profiles',
    'parts_policy': 'Integral supplied model; factory body only. No unrequested decomposition or borrowed steel-hammer modifications.',
    'balance': 'Independent formula entry initialized to current steel-warhammer values; no added innate rune effect',
    'ui_opened': False, 'game_started': False,
}
for filename, key in [('build_receipt.json','builds'), ('import_receipt.json','import')]:
    if (P / filename).exists():
        delivery[key] = json.loads((P / filename).read_text(encoding='utf-8-sig'))
module_delivery = P / 'ModulesV1/delivery.json'
if module_delivery.exists():
    delivery['modules'] = json.loads(module_delivery.read_text(encoding='utf-8-sig'))
    delivery['parts_policy'] = 'Six original modules; fourteen host-fitted common parts; five shared runes; original appearance and all motions retained'
(P / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
print('Production delivery receipts saved')
