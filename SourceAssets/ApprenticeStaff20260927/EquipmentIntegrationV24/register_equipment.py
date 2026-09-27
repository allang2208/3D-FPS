"""Register the existing staff rig with modular outfits; keep inventory identities."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE = '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7'
M4 = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416'

inspection = json.loads((ROOT / 'outfit-source-inspection.json').read_text(encoding='utf-8'))
source = next(m for m in inspection['meshes'] if m['path'] == SOURCE)
if source['materials'] != ['BareUpperArms', 'BareLowerArms', 'BareHandsOriginalGrip']:
    raise RuntimeError('Staff source sections changed; update this profile from the actual mesh.')
if any(m['skeleton'] != source['skeleton'] for m in inspection['meshes']):
    raise RuntimeError('Outfit rig differs from the staff source.')

path = PROJECT / 'Content/ColdSteelData/modular_outfits.json'
config = json.loads(path.read_text(encoding='utf-8-sig'))
profile = copy.deepcopy(config['profiles'][M4])
for field in ('base', 'native_bare_skin', 'bare_arms_candidate'):
    profile[field] = SOURCE
profile['hide_source_materials'] = [0, 1, 2]
profile['native_bare_arms'] = True
config['profiles'][SOURCE] = profile
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

path = PROJECT / 'Content/ColdSteelData/staffs.json'
staffs = json.loads(path.read_text(encoding='utf-8-sig'))
staffs['ue_apprentice_staff']['ue_icon'] = 'Icons/ue_apprentice_staff.png'
path.write_text(json.dumps(staffs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

receipt = {'profile': SOURCE, 'rig_profile': profile['rig_profile'],
           'hide_source_materials': profile['hide_source_materials'],
           'equipment_slots': [3, 7], 'animation_changed': False,
           'catalog_icon': 'Icons/ue_apprentice_staff.png', 'runtime_tested': False}
(ROOT / 'registration-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt))
