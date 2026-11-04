"""Publish only the approved Highland finishes and Weakness definition."""
from pathlib import Path
import json
import shutil
from runpy import run_path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
whitehart = run_path(str(ROOT / 'SourceAssets/WhitehartCriticalVulnerability20261103/definition.py'))

def read(relative):
    path = ROOT / relative
    backup = P / 'BeforeData' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(relative, data):
    (ROOT / relative).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

catalog_path = 'Content/ColdSteelData/melee-gunsmith.json'
catalog = read(catalog_path)
options = next(c for c in catalog['columns'] if c['key'] == 'blade_material')['options']
approved = [
    {
        'id': 'blackthorn_steel', 'name': '黑棘钢', 'tier': 'special',
        'weapons': ['ue_highland_claymore'],
        'description': '高地双手剑专属。深炭黑锻钢泛起冷蓝金属光泽，细密锤锻肌理衬托磨亮的银钢刃缘。',
        'stats': {'melee_critical_chance_add': 25.0},
        'effects': [{'text': '暴击率+25%', 'benefit': 1}],
        'special_effects': [
            '黑棘诅咒｜使用本武器攻击暴击命中敌人时，施加1层虚弱，持续8秒；普通攻击、重击和武技均可触发。',
            '虚弱｜每层使敌人造成的伤害降低10%，最多5层，满层降低50%。再次触发叠加1层，并将全部层数的剩余时间刷新为8秒；满层时仍刷新时间，到期全部清除。',
        ],
    },
    {
        'id': 'whitehart_mithril', 'name': '白鹿秘银', 'tier': 'special',
        'weapons': ['ue_highland_claymore'],
        'description': '高地双手剑专属。银白秘银呈现丝缎刃面与精抛刃脊，反射清亮，掠射角浮现淡淡冰蓝光泽。',
        'stats': whitehart['STATS'], 'effects': whitehart['EFFECTS'], 'special_effects': whitehart['SPECIAL_EFFECTS'],
    },
]
for option in approved:
    index = next((i for i, old in enumerate(options) if old['id'] == option['id']), None)
    if index is None:
        options.append(option)
    else:
        options[index] = option
write(catalog_path, catalog)

status_path = 'Content/ColdSteelData/status_effects.json'
statuses = read(status_path)
weakness = {
    'type': 'weakness', 'icon': '虚', 'name': '虚弱', 'color': '#9a86a8',
    'description': '每层使造成的伤害降低10%，最多5层，满层降低50%。持续8秒；再次触发叠加1层并将全部层数的剩余时间刷新为8秒，满层时仍刷新时间，到期全部清除。',
    'kind': 'debuff', 'group': 'combat',
}
index = next((i for i, old in enumerate(statuses['effects']) if old['type'] == 'weakness'), None)
if index is None:
    statuses['effects'].append(weakness)
else:
    statuses['effects'][index] = weakness
index = next((i for i, old in enumerate(statuses['effects']) if old['type'] == whitehart['STATUS']['type']), None)
if index is None:
    statuses['effects'].append(whitehart['STATUS'])
else:
    statuses['effects'][index] = whitehart['STATUS']
write(status_path, statuses)

icon_dir = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913'
icon_sources = {'blackthorn_steel': 'dark_iron', 'whitehart_mithril': 'mithril'}
for option, source in icon_sources.items():
    target = icon_dir / ('ue_highland_claymore_blade_material_' + option + '.png')
    if target.exists():
        backup = P / 'BeforeData/Icons' / target.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(target, backup)
    shutil.copy2(icon_dir / ('blade_material_' + source + '.png'), target)

draft_path = 'SourceAssets/HighlandExclusiveMaterialsConcept20261103/WesternV2/design-draft.json'
draft = read(draft_path)
draft['status'] = 'approved_material_integration_in_progress'
draft['implementation'] = '../../HighlandExclusiveMaterials20261103/delivery.json'
black, white = draft['options']
black['superseded_effect_draft'] = {'direct': black.pop('direct_stats_draft', []), 'special': black.pop('special_effects_draft', [])}
black['direct_stats_approved'] = ['暴击率+25%']
black['special_effects_approved'] = approved[0]['special_effects']
black['theme'] = '高地氏族的诅咒锻钢，冷硬厚重，以暴击削弱敌人的输出。'
black['author_notes'] = ['以2026-11-03用户确认的暴击与虚弱替换原物理增伤和满蓄力破韧草稿。', '同一敌人共享虚弱层数和到期时间；每次有效暴击增加1层，满层仍刷新。']
white['direct_stats_approved'] = ['暴击伤害+50%']
white['special_effects_approved'] = whitehart['SPECIAL_EFFECTS']
white['implementation_scope'] = '暴击伤害与暴击易伤按2026-11-03后续确认接入；原白鹿之舞草稿作废。'
white['passive_delivery'] = '../../WhitehartCriticalVulnerability20261103/delivery.json'
write(draft_path, draft)

(P / 'data-receipt.json').write_text(json.dumps({
    'weapon': 'ue_highland_claymore', 'slot': 'blade_material',
    'options': approved, 'status': weakness, 'icons_reuse': icon_sources,
    'whitehart_passive_enabled': True, 'gameplay_tested': False,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('HIGHLAND_DATA_PUBLISHED')
