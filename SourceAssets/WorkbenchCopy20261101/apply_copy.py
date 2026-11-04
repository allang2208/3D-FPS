"""Apply the reviewed copy to live JSON, preserving all non-copy fields."""
import copy
import json
from pathlib import Path
from copy_rules import apply_catalog

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'Content/ColdSteelData'
HERE = Path(__file__).resolve().parent


def without_copy(value):
    if isinstance(value, dict):
        return {k: without_copy(v) for k, v in value.items()
                if k not in ('description', 'appearance', 'special_effects')
                and not (k == 'effects' and isinstance(v, list))}
    if isinstance(value, list):return [without_copy(v) for v in value]
    return value


def apply_file(path, items=None):
    path = Path(path)
    before = path.read_bytes()
    original = json.loads(before.decode('utf-8-sig'))
    if items is None:items = json.loads((DATA/'items.json').read_text(encoding='utf-8-sig'))
    updated = apply_catalog(path.name, copy.deepcopy(original), items)
    if without_copy(original) != without_copy(updated):
        raise RuntimeError(f'Non-copy change rejected: {path.name}')
    if original == updated:return False
    backup = HERE/'before'/path.name
    if not backup.exists():
        backup.parent.mkdir(exist_ok=True)
        backup.write_bytes(before)
    if path.read_bytes() != before:raise RuntimeError(f'Concurrent edit: {path}')
    path.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return True


if __name__ == '__main__':
    items = json.loads((DATA/'items.json').read_text(encoding='utf-8-sig'))
    files = list(DATA.glob('*gunsmith.json'))
    for path in list(files):
        for col in json.loads(path.read_text(encoding='utf-8-sig')).get('columns', []):
            library = col.get('options_library')
            if library and DATA/library not in files:files.append(DATA/library)
    changed = [p.name for p in files if apply_file(p, items)]
    print(json.dumps({'changed_catalogs':changed,'non_copy_fields_preserved':True},ensure_ascii=False))
