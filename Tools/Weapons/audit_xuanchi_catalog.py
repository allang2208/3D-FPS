"""Scoped, read-only Zhenyue catalog and asset-path audit."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'Content/ColdSteelData'
WEAPON = 'ue_xuanchi_zhenyue'
def read(name):
    return json.loads((DATA / name).read_text(encoding='utf-8-sig'))

def run():
    item = read('items.json')[WEAPON]
    catalog = read(item['modular_sword_catalog'])
    library = read(catalog['pommel_profile']['library'])
    profile = catalog['pommel_profile']
    slots = catalog['slots']
    for key, entry in library['options'].items():
        spec = dict(entry)
        spec.update({k: profile[k] for k in ('location_cm', 'rotation_deg', 'scale', 'adapter') if k in profile})
        spec.update(profile.get('interfaces', {}).get(entry['interface'], {}))
        spec.update(library['finishes'][profile['finish']].get(key, {}))
        slots['pommel'][key] = spec
    references = set()
    def walk(value):
        if isinstance(value, dict):
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
        elif isinstance(value, str) and value.startswith('/Game/'):
            references.add(value)
    walk(catalog)
    walk(item)
    for source in ('FrostSwordRunes.h', 'JingangRuneComponent.cpp', 'ZhenmoRuneComponent.cpp'):
        references.update(re.findall(r'/Game/[A-Za-z0-9_./]+',
                          (ROOT / 'Source/FPSGAME/Weapons' / source).read_text(encoding='utf-8-sig')))
    missing_assets = []
    for path in sorted(references):
        file = ROOT / 'Content' / (path[6:].split('.')[0] + '.uasset')
        # Animation folders are directory references, not individual assets.
        if not file.exists() and not file.with_suffix('').is_dir(): missing_assets.append(path)
    icons = DATA / 'AttachmentIcons20260913'
    missing_icons = []
    options = []
    factory_icons = {}
    category_icons = {}
    for column in read('melee-gunsmith.json')['columns']:
        slot = column['key']
        for prefix, output in ((f'{slot}_false', factory_icons), (f'category_{slot}', category_icons)):
            specific = icons / f'{WEAPON}_{prefix}.png'
            icon = specific if specific.exists() else icons / f'{prefix}.png'
            output[slot] = icon.name
            if not icon.exists(): missing_icons.append(prefix)
        for entry in column['options']:
            if entry.get('weapons') and WEAPON not in entry['weapons']: continue
            key = entry['id']
            shared = icons / f'{slot}_{key}.png'
            specific = icons / f'{WEAPON}_{slot}_{key}.png'
            is_shared = key != 'false' and entry.get('tier') != 'legendary' and shared.exists()
            icon = shared if is_shared else specific if specific.exists() else shared
            if not icon.exists(): missing_icons.append(f'{slot}/{key}')
            options.append({'slot': slot, 'id': key, 'tier': entry.get('tier', 'common'),
                            'icon': icon.name, 'physical': key in slots.get(slot, {})})
    result = {'weapon': WEAPON, 'base_reach_cm': item['melee_reach_cm'],
              'asset_reference_count': len(references), 'missing_assets': missing_assets,
              'asset_references': sorted(references), 'missing_icons': missing_icons, 'options': options,
              'factory_icons': factory_icons, 'category_icons': category_icons,
              'shared_pommel_finish': profile['finish'], 'runtime_tested': False}
    out = ROOT / 'Saved/XuanChiReview20261006/catalog-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('options', 'asset_references')}, ensure_ascii=False))
    print('options=' + str(len(options)))
    return 1 if missing_assets or missing_icons else 0

if __name__ == '__main__':
    raise SystemExit(run())
