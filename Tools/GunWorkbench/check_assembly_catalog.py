"""On-demand catalog diagnostics; runtime framing uses loaded mesh bounds."""
import argparse, json, math
from pathlib import Path

P = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=P/'SourceAssets/GunAssemblyCompletion20261015')
ROOT = parser.parse_args().output_dir.resolve()
def read(name):
    return json.loads((P / 'Content/ColdSteelData' / name).read_text(encoding='utf-8-sig'))
def sub(a, b): return [x-y for x, y in zip(a, b)]
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def unit(a): return [x/math.sqrt(dot(a, a)) for x in a]
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def screen(recipe, position, aspect):
    f = unit(sub(recipe['look_at'], recipe['camera']))
    r = unit(cross([0, 0, 1], f)); up = cross(f, r)
    v = sub(position, recipe['camera']); depth = dot(v, f)
    tan = math.tan(math.radians(65/2))
    return [.5+dot(v, r)/(2*depth*tan), .5-dot(v, up)*aspect/(2*depth*tan)]

items = read('items.json'); guns = read('gunsmith.json')['weapons']
recipes = read('gun-assembly.json')['recipes']
issues = []; rows = []; seen = set()
gun_ids = {w['id'] for w in guns}
item_guns = {k for k, v in items.items() if v.get('weaponType') in ('rifle', 'pistol', 'machineGun', 'shotgun', 'sniper')}
if gun_ids != item_guns: issues.append({'catalog_difference': sorted(gun_ids ^ item_guns)})
for missing in sorted(gun_ids-{r['output'] for r in recipes}): issues.append({'missing_recipe': missing})
for recipe in recipes:
    errors = []; rid = recipe['id']; parts = recipe['parts']; placements = []
    if rid in seen: errors.append('Duplicate recipe ID')
    seen.add(rid)
    if recipe['output'] not in gun_ids: errors.append('Output is not a registered firearm')
    if not 1 <= len(parts) <= 30: errors.append('Invalid installed-bitmask part count')
    if len({p['id'] for p in parts}) != len(parts): errors.append('Duplicate part ID')
    for field in ('position_tolerance_cm', 'angle_tolerance_deg', 'calibration_seconds'):
        if not math.isfinite(recipe[field]) or recipe[field] <= 0: errors.append('Invalid '+field)
    for entry in recipe['inputs']:
        if entry['item'] not in items or entry['count'] <= 0: errors.append('Invalid material '+entry['item'])
        if entry['item'] in ('ironIngot', 'copperIngot', 'silverIngot', 'goldIngot'):
            errors.append('Metal must use the selectable metal_count contract')
    if not isinstance(recipe.get('metal_count'), int) or recipe['metal_count'] <= 0:
        errors.append('Invalid selectable metal count')
    for path in [recipe['body_mesh']] + [p['mesh'] for p in parts]:
        if not (P / 'Content' / (path.removeprefix('/Game/').split('.')[0]+'.uasset')).is_file():
            errors.append('Missing mesh '+path)
    for part in parts:
        if any(v <= 0 or not math.isfinite(v) for v in part['extent']): errors.append('Invalid extent '+part['id'])
        for state in ('loose', 'target'):
            if len(part[state]) != 3 or not all(math.isfinite(v) for v in part[state]): errors.append('Invalid vector '+part['id'])
            position = list(part[state])
            # Use the exact target plane. Runtime expands drag bounds from all placements
            # and fits the loaded meshes above the HUD; authored camera is reference only.
            views = {str(a): screen(recipe, position, a) for a in (16/9, 16/10, 4/3)}
            placements.append({'part': part['id'], 'state': state, 'authored_screen_reference': views})
    row = {'id': rid, 'output': recipe['output'], 'parts': len(parts),
           'calibration_seconds': recipe['calibration_seconds'], 'errors': errors, 'placements': placements}
    rows.append(row)
    if errors: issues.append({'recipe': rid, 'errors': errors})
result = {'firearms': len(gun_ids), 'recipes': len(recipes), 'issues': issues, 'rows': rows,
          'scope': 'Config/file checks only; fitted camera, HUD guides and actual interaction require gameplay acceptance'}
ROOT.mkdir(parents=True, exist_ok=True)
(ROOT / 'catalog-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'firearms': len(gun_ids), 'recipes': len(recipes), 'issues': issues}, ensure_ascii=False))
raise SystemExit(1 if issues else 0)
