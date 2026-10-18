"""Record the requested per-weapon source/configuration inventory; no engine run."""
import json
import re
from pathlib import Path

task = Path(__file__).resolve().parent
project = task.parents[1]
data = json.loads((project / 'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
variants = (project / 'Source/FPSGAME/Weapons/TacticalDeviceVariants.h').read_text(encoding='utf-8-sig')
secondary_body = variants.split('inline bool SupportsSecondary(', 1)[1].split('\n}', 1)[0]
secondary = set(re.findall(r'TEXT\("(ue_[^"]+)"\)', secondary_body))
offhand = {'ue_m1911', 'ue_pit_viper2011', 'ue_g18', 'ue_dan_wesson715', 'ue_rsh12'}
families = dict(re.findall(r'if\(Definition==TEXT\("([^"]+)"\)\)return TEXT\("([^"]+)"\);', variants))
weapons = []
for weapon in data['weapons']:
    definition = weapon['id']
    devices = {option['id'] for option in weapon['options'].get('tactical', [])}
    devices.update(option['id'] for option in data.get('common_options', {}).get('tactical', []))
    weapons.append({
        'definition': definition,
        'name': weapon['name'],
        'definition_tactical_family': families.get(definition, 'M4'),
        'devices': sorted(devices - {'false'}),
        'primary_route': 'AFPSGAMECharacter::SetGunsmithTactical -> UTacticalDeviceComponent',
        'secondary_declared': 'tactical_secondary' in weapon['allowed'],
        'secondary_runtime_enabled': definition in secondary,
        'offhand_route': 'UPistolDualWieldComponent::CopyLeftAttachments -> UTacticalDeviceComponent' if definition in offhand else None,
        'owner_third_person_route': 'UTacticalDeviceComponent -> ResolveWorldWeaponPart',
        'remote_route': 'RebuildWeapons -> ConfigureWorld; laser and flashlight from installed manifest',
        'source_reviewed': True,
        'gameplay_tested': False,
    })
motion = json.loads((project / 'Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8-sig'))
food = ['bread', 'baguette_bread', 'roasted_chicken_leg', 'roasted_lamb_ribs', 'roasted_sausage', 'roasted_large_lamb']
report = {
    'scope': 'Source/configuration audit of every catalog gun and its existing tactical slots during consumable weapon stow.',
    'weapons': weapons,
    'food': [{'definition': item, 'two_handed': motion[item].get('two_handed', False)} for item in food],
    'counts': {'catalog_weapons': len(weapons), 'secondary_slots': sum(w['secondary_runtime_enabled'] for w in weapons), 'offhand_pistols': sum(w['offhand_route'] is not None for w in weapons)},
    'svch_note': 'SVCh is included from the current catalog and secondary-slot opt-in. Its attachment-family development is independent of the shared emission/stow gate changed here.',
    'tests_run': False,
}
(task / 'coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report['counts']))
