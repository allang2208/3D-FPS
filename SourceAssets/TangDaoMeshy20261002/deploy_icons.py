"""Deploy new weapon icons; shared rune/pommel artwork retains its established identity."""
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DATA = ROOT / 'Content/ColdSteelData'
TARGET = DATA / 'AttachmentIcons20260913'
ID = 'ue_tang_dao'
manifest = json.loads((P / 'generated_icons.json').read_text(encoding='utf-8'))
generated = P / 'FramedIcons'
generated.mkdir(exist_ok=True)
deployed = []

def deploy(source, key):
    target = TARGET / (ID + '_' + key + '.png')
    shutil.copy2(source, target)
    deployed.append({'source': str(source), 'destination': str(target), 'asset': '/Game/ColdSteelData/AttachmentIcons20260913/' + target.stem})

for entry in manifest:
    local = generated / (ID + '_' + entry['key'] + '.png')
    shutil.copy2(entry['file'], local)
    deploy(local, entry['key'])
    if entry['key'].endswith('_false'):
        slot = entry['key'][:-6]
        deploy(local, 'category_' + slot)
for option in ['false', 'resonance_rune', 'erosion_rune', 'conduction_rune']:
    deploy(TARGET / ('ue_rune_sword_blade_2_' + option + '.png'), 'blade_2_' + option)
deploy(TARGET / 'ue_rune_sword_category_blade_2.png', 'category_blade_2')
shared = json.loads((DATA / 'shared-sword-pommels.json').read_text(encoding='utf-8-sig'))
for option in shared['options']:
    source = TARGET / ('ue_frost_crystal_sword_pommel_' + option + '.png')
    if not source.exists():
        source = TARGET / ('ue_rune_sword_pommel_' + option + '.png')
    deploy(source, 'pommel_' + option)
inventory = DATA / 'Icons' / (ID + '.png')
shutil.copy2(P / 'Icons' / (ID + '.png'), inventory)
deployed.append({'source': str(P / 'Icons' / (ID + '.png')), 'destination': str(inventory), 'asset': '/Game/ColdSteelData/Icons/' + ID})
(P / 'icon_deploy_receipt.json').write_text(json.dumps(deployed, indent=2), encoding='utf-8')
print('TANGDAO_ICONS_DEPLOYED ' + str(len(deployed)))
