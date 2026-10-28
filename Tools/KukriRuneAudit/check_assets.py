"""Read-only catalog and saved-file audit; no editor or rendering."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'Content/ColdSteelData'
OUT = ROOT / 'SourceAssets/KukriFrostRaven20261028/CompletionAudit/assets.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

options = [('blade_1', o, False) for o in read(DATA/'shared-knife-blade-options.json')['options']]
for file, exclusive in [('shared-knife-component-options.json', False), ('kukri-gunsmith.json', True)]:
    for column in read(DATA/file)['columns']:
        options.extend((column['key'], option, exclusive) for option in column['options'] if option['id'] != 'no_lanyard')
rows = []
for slot, option, exclusive in options:
    stem = ('ue_kukri_' if exclusive else '') + slot + '_' + option['id']
    png = DATA/'AttachmentIcons20260913'/f'{stem}.png'
    texture = png.with_suffix('.uasset')
    image = Image.open(png) if png.exists() else None
    rows.append(dict(slot=slot, id=option['id'], stats=option.get('stats'),
                     icon_png=png.exists(), icon_texture=texture.exists(),
                     image_size=list(image.size) if image else None,
                     image_mode=image.mode if image else None))
refs = set()
def scan(value):
    if isinstance(value, dict):
        for child in value.values(): scan(child)
    elif isinstance(value, list):
        for child in value: scan(child)
    elif isinstance(value, str) and value.startswith('/Game/'):
        refs.add(value)
scan(read(DATA/'kukri-modules.json'))
for receipt in ['BladeSigilV2/install-receipt.json', 'CrystalCrownV3/width-fit-receipt.json']:
    scan(read(ROOT/'SourceAssets/KukriFrostRaven20261028'/receipt))
missing = [r for r in sorted(refs) if not (ROOT/'Content'/(r[6:].split('.')[0]+'.uasset')).exists()]
result = dict(modifications=len(rows), options=rows, saved_asset_references=len(refs), missing_assets=missing,
              passed=not missing and all(r['stats'] and r['icon_png'] and r['icon_texture'] for r in rows),
              scope='Catalog values, icon files and declared saved assets only. No visual or packaged-build acceptance.')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k != 'options'}, ensure_ascii=True))
