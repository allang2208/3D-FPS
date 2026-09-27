"""Activate the saved V19 sight while preserving the current camera and actions."""
import json
from pathlib import Path

P = Path(__file__).parent
ROOT = P.parents[1]
receipt = json.loads((P/'import-receipt.json').read_text(encoding='utf8'))
mesh = receipt['saved']['SM_Bow_WoodBracketSight']
pin = ','.join(f'{x:g}' for x in receipt['sight_pin_cm'])
visual = {
    'bow_part_sight_mesh': mesh,
    'bow_part_sight_rods': 0,
    'bow_part_sight_scale': 1.,
    'bow_part_sight_location_cm': '0,0,0',
    'bow_part_sight_rotation_deg': '0,0,0',
    'bow_ads_sight_cm': pin,
}

path = ROOT/'Content/ColdSteelData/bows.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
bow = data['bow_dark']
revision = max(30, int(bow.get('bow_presentation_revision', 0)) +
               int(bow.get('bow_part_sight_mesh') != mesh))
bow.update(visual)
bow['bow_presentation_revision'] = revision
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

path = ROOT/'Content/ColdSteelData/bow-gunsmith.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
sight = next(c for c in data['columns'] if c['key'] == 'sight')
sight['default'] = '弧臂圆环木制瞄具'
sight['description'] = '弧形木臂从贴合弓体的水滴形木座延伸至圆环下缘，绑线嵌入浅槽，环内设竖向准星。'
sight['factory_visual'].update(visual)
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

path = ROOT/'Config/DefaultGame.ini'
text = path.read_text(encoding='utf-8-sig')
line = '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/WoodBracketV19")'
if line not in text:
    section = '[/Script/UnrealEd.ProjectPackagingSettings]'
    if section not in text:
        raise RuntimeError('Packaging section missing')
    path.write_text(text.replace(section, section+'\n'+line, 1), encoding='utf8')

(P/'install-receipt.json').write_text(json.dumps({
    'revision': revision, 'mesh': mesh, 'sight_pin_cm': pin,
    'ads_distance_cm': bow.get('bow_ads_sight_distance_cm'),
    'ads_in_seconds': bow.get('bow_ads_in_seconds'),
    'ads_out_seconds': bow.get('bow_ads_out_seconds'),
    'gameplay_tested': False, 'rendered': False,
}, indent=2), encoding='utf8')
print('BOW_WOOD_BRACKET_V19_ACTIVATED revision='+str(revision))
