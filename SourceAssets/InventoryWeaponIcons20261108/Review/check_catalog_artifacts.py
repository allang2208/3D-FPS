"""Check actual published PNGs against the existing inventory definitions."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
DATA = PROJECT / 'Content/ColdSteelData'
receipts = {Path(row['png']).name: row for row in json.loads(
    (ROOT.parent / 'saved-icons.json').read_text(encoding='utf-8-sig'))}
rows = []
for definition, catalog, size, grid in [
    ('tool_axe', 'production_tools.json', (512, 1536), (1, 3)),
    ('ue_m249', 'items.json', (800, 320), (5, 2)),
]:
    entry = json.loads((DATA / catalog).read_text(encoding='utf-8-sig'))[definition]
    path = DATA / entry['ue_icon']
    image = Image.open(path)
    alpha = image.getchannel('A')
    bounds = alpha.getbbox()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert image.size == size and image.mode == 'RGBA', str(path)
    assert (entry['grid_w'], entry['grid_h']) == grid, definition
    assert size[0] * grid[1] == size[1] * grid[0], definition
    assert alpha.getextrema() == (0, 255), definition
    assert bounds and 0 < bounds[0] < bounds[2] < size[0] and 0 < bounds[1] < bounds[3] < size[1], definition
    assert digest == receipts[path.name]['png_sha256'], definition
    assert path.with_suffix('.uasset').stat().st_size > 0, definition
    assert (ROOT.parent / 'Artwork' / path.name).read_bytes() == path.read_bytes(), definition
    rows.append(dict(definition=definition, png=str(path), size=size, grid=grid,
                     alpha_range=alpha.getextrema(), visible_bounds=bounds, sha256=digest))
(ROOT / 'catalog-artifact-check.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('INVENTORY_ICON_CATALOG_ARTIFACTS_OK')
