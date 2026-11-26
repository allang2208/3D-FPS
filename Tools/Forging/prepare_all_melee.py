"""Prepare the current melee-to-forge mapping without changing runtime data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ForgeAllMelee20261024'
OUT.mkdir(parents=True, exist_ok=True)
items = json.loads((ROOT / 'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
catalog = json.loads((ROOT / 'Content/ColdSteelData/forging-recipes.json').read_text(encoding='utf-8-sig'))
# Costs extend the existing plain/rune sword and plain hammer recipes.
specs = [
    ('ue_kukri', 'single_handed', [('ironIngot', 4), ('wood', 1), ('search_forging_alloy_blank', 1)]),
    ('ue_xuanchi_zhenyue', 'sword', [('ironIngot', 10), ('silverIngot', 2), ('wood', 3), ('search_forging_alloy_blank', 2)]),
    ('ue_zhanmadao', 'tang_dao', [('ironIngot', 10), ('wood', 3), ('search_forging_alloy_blank', 1)]),
    ('ue_runebound_warhammer', 'warhammer', [('ironIngot', 12), ('silverIngot', 4), ('wood', 3), ('magic_dust', 6), ('search_forging_alloy_blank', 2)]),
]
recipes = []
for item, blank, inputs in specs:
    recipes.append({'id': 'forge_' + item.removeprefix('ue_'), 'output': item, 'blank': blank,
                    'inputs': [{'item': key, 'count': count} for key, count in inputs], 'mold': items[item]['ue_icon']})
existing = {r['output']: r for r in catalog['recipes']}
planned = {r['output']: r for r in recipes}
rows = []
for key, item in items.items():
    if item.get('category') != 'weapon_melee':
        continue
    recipe = existing.get(key) or planned.get(key)
    if recipe is None:
        raise RuntimeError('Unmapped current melee weapon: ' + key)
    rows.append({'item': key, 'name': item['name'], 'recipe': recipe['id'],
                 'blank': recipe.get('blank', 'sword'), 'action': 'preserve' if key in existing else 'add'})
plan = {'scope': 'All current category=weapon_melee equipment; harvesting tools retain their crafting route',
        'coverage': rows, 'additions': [r for r in recipes if r['output'] not in existing],
        'tests_run': False}
(OUT / 'recipe_plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('MELEE_FORGE_PLAN total=%d additions=%d' % (len(rows), len(plan['additions'])))
