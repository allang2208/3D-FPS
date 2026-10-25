"""Repair whole-groom hiding for current open hats and record the requested audit."""
import copy
import json
from pathlib import Path

from config_transaction import commit

P = Path(__file__).resolve().parents[2]
W = P / 'SourceAssets/HeadwearHair20261024'
OPEN = {'ue_st6_tactical_helmet', 'ue_field_hat', 'ue_ranger_feather_hat', 'ue_blue_mage_hat', 'ue_charcoal_sports_cap'}
CLOSED = {'ue_steel_armet'}


def variants(body):
    yield 'jason', (), body
    for key, value in body.get('body_variants', {}).items():
        yield key, ('body_variants', key), value


def main():
    path = P / 'Content/ColdSteelData/player_body.json'
    before = path.read_bytes()
    body = json.loads(before.decode('utf-8-sig'))
    original = copy.deepcopy(body)
    catalog = json.loads((P / 'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
    catalog_hats = {key for key, item in catalog.items() if item.get('equipSlot') in ('helmet', 'head')}
    owned = []
    for _, prefix, variant in variants(body):
        for key, recipe in variant.get('head_equipment', {}).items():
            if key in OPEN:
                recipe['covers_scalp_hair'] = False
                owned.append(prefix + ('head_equipment', key, 'covers_scalp_hair'))
    receipt = commit(path, before, body, owned_paths=owned, producer=__file__)
    applied = json.loads(path.read_text(encoding='utf-8-sig'))
    old_variants = {name: value for name, _, value in variants(original)}
    rows = []
    for name, _, variant in variants(applied):
        old = old_variants[name]
        recipes = variant.get('head_equipment', {})
        for key in sorted(catalog_hats | set(recipes)):
            recipe = recipes.get(key)
            expected = False if key in OPEN else True if key in CLOSED else None
            actual = recipe.get('covers_scalp_hair', False) if recipe is not None else None
            rows.append(dict(body=name, item=key, name=catalog.get(key, {}).get('name', key),
                             kind='open_hat' if key in OPEN else 'closed_helmet' if key in CLOSED else 'unclassified',
                             has_recipe=recipe is not None,
                             supported_heads=sorted(recipe.get('fits', {})) if recipe else [],
                             before=old.get('head_equipment', {}).get(key, {}).get('covers_scalp_hair', False),
                             after=actual, expected=expected,
                             policy_matches=recipe is not None and expected is not None and actual is expected))
    report = dict(completed=all(row['policy_matches'] for row in rows),
                  catalog_headwear=len(catalog_hats), body_headwear_rows=len(rows),
                  open_hat_rows=sum(row['kind'] == 'open_hat' for row in rows), rows=rows,
                  publication=receipt, runtime_tested=False,
                  coverage='Catalog, both body recipes, shared runtime whole-groom visibility branch; no visual or motion test',
                  runtime_rule='covers_scalp_hair hides all HeadScalpHair groom components, not only hair inside the hat',
                  configuration_load='FPSPlayerBodyComponent::BeginPlay; applies to newly created players / next play session')
    W.mkdir(parents=True, exist_ok=True)
    (W / 'audit-and-publication.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('completed', 'catalog_headwear', 'body_headwear_rows', 'open_hat_rows', 'runtime_tested')}))
    if not report['completed']:
        raise RuntimeError('Some headwear requires separate classification; see the saved matrix.')


if __name__ == '__main__':
    main()
