"""Publish only the saved TangDao blade-material fields and temporal pairs."""
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]


def installed():
    receipt = P / 'material-receipt.json'
    return receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')).get('assets_complete', False)


def merge_file(path, change):
    original = path.read_bytes()
    data = json.loads(original.decode('utf-8-sig'))
    change(data)
    backup = P / 'BeforeData' / path.relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    if path.read_bytes() != original:
        raise RuntimeError('Catalog changed during publication: ' + str(path))
    temporary = path.with_suffix(path.suffix + '.dao-longitudinal.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def install():
    if not installed():
        raise RuntimeError('Save longitudinal materials first')
    receipt = json.loads((P / 'material-receipt.json').read_text(encoding='utf-8'))
    def modules(data):
        for choice, row in receipt['tang_bindings'].items():
            target = data['slots']['blade_1'][choice]
            if target['mesh'] != row['mesh']:
                raise RuntimeError('Blade geometry changed; reauthor longitudinal layout: ' + choice)
            target.setdefault('materials', {}).update(row['materials'])
        data['longitudinal_surface_revision'] = receipt['revision']
    merge_file(ROOT / 'Content/ColdSteelData/tang-dao-modules.json', modules)
    def source_bindings(data):
        for choice, row in receipt['tang_bindings'].items():
            data['slots']['blade_1'].setdefault(choice, {}).update(row['materials'])
        data['longitudinal_surface_revision'] = receipt['revision']
    merge_file(ROOT / 'SourceAssets/TangDaoMeshy20261002/SurfaceV2/bindings.json', source_bindings)
    merge_file(ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json',
               lambda data: data.update(receipt['temporal_bindings']))
    print('DAO_LONGITUDINAL_CATALOG_SAVED')


if __name__ == '__main__':
    install()
