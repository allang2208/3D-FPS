"""Extract the requested legacy staff design and migration references; not a test."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEGACY = Path(r'E:\无尽轮回\长期备份\2026-7-13-1\game-dev')
PROJECT = ROOT.parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def occurrences(root, suffixes, terms):
    result = {term: [] for term in terms}
    pattern = re.compile('|'.join(re.escape(term) for term in sorted(terms, key=len, reverse=True)))
    for path in sorted(root.rglob('*')):
        if path.suffix not in suffixes or not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
            for term in set(pattern.findall(line)):
                result[term].append({'file': path.relative_to(root).as_posix(), 'line': number, 'text': line.strip()})
    return result


def main():
    item = read_json(LEGACY / 'data/equipment.json')['equipment']['apprentice_staff']
    craft = read_json(LEGACY / 'data/craft-config.json')['weapon20']
    edm = (LEGACY / 'src/ui/equip-data-manager.js').read_text(encoding='utf-8-sig')
    item_text = edm.split('    APPRENTICE_STAFF_ITEM: {', 1)[1].split('    PKM_ITEM: {', 1)[0]
    (ROOT / 'Reference/apprentice-staff-edm.txt').write_text('    APPRENTICE_STAFF_ITEM: {' + item_text, encoding='utf-8')
    # EDM is the runtime authority for these fields missing from equipment.json.
    runtime = dict(item)
    runtime.update({
        'weaponType': 'staff', 'isTwoHanded': False,
        'attackKey': 'melee', 'animConfigKey': 'sword', 'castAnimKey': 'staff_cast',
        'attackFormula': {'base': 3, 'enhanceFlat': 0.25, 'attrs': [
            {'key': 'dex', 'base': 0.25, 'perEnhance': 0.1},
            {'key': 'str', 'base': 0.25, 'perEnhance': 0.15}]},
    })
    keys = sorted({key for options in craft['options'].values() for option in options for key in option['effects']})
    write_json(ROOT / 'Reference/legacy-contract.json', {
        'captured_on': '2026-09-27', 'legacy_root': str(LEGACY),
        'status': 'reference_only_not_installed', 'equipment_template': item,
        'runtime_item_contract': runtime, 'craft': craft, 'effect_keys': keys,
        'option_count': sum(len(options) for options in craft['options'].values()),
        'semantic_notes': [
            'EDM provides the physical attack formula and staff_cast key absent from the equipment template.',
            'isTwoHanded=false makes the existing implicit single-handed contract explicit; this is not a source field.',
            'Only the active mainhand staff supplies formula and crafting bonuses.',
            'castSpeedPercent=.25 divides both animation durations by 1.25; the original option prose is inconsistent.',
            'staffSpecialty is a string override; remaining option effects are numeric sums.',
            'No model generation, live definition registration, asset import, build or test is represented by this snapshot.',
        ],
    })
    for source in ['src/utils/magic-craft-helper.js', 'src/config/magic-categories.js', 'src/ui/craft/craft-effects.js']:
        destination = ROOT / 'Reference/SourceCode' / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY / source, destination)
    for options in craft['options'].values():
        for option in options:
            source = LEGACY / option['icon']
            if source.is_file():
                destination = ROOT / 'Reference/LegacyIcons' / source.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    write_json(ROOT / 'Reference/legacy-effect-references.json', occurrences(LEGACY / 'src', {'.js'}, keys))
    write_json(ROOT / 'Reference/ue-effect-references.json', occurrences(PROJECT / 'Source/FPSGAME', {'.cpp', '.h'}, keys))
    player = read_json(LEGACY / 'data/player-anim-config.json')
    weapon = read_json(LEGACY / 'data/weapon-anim-config.json')
    def staff_nodes(value):
        if not isinstance(value, dict):
            return {}
        result = {}
        for key, entry in value.items():
            if 'staff' in key.lower():
                result[key] = entry
            elif isinstance(entry, dict):
                nested = staff_nodes(entry)
                if nested:
                    result[key] = nested
        return result
    write_json(ROOT / 'Reference/legacy-staff-animation.json', {'player': staff_nodes(player), 'weapon': staff_nodes(weapon)})
    print(json.dumps({'output': str(ROOT / 'Reference'), 'slots': len(craft['slots']), 'options': sum(map(len, craft['options'].values())), 'effect_keys': len(keys)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
