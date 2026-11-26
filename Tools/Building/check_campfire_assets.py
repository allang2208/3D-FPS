"""Read-only completion audit for the existing four campfire food families."""
import json
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
OUT = P/'SourceAssets/CampfireCompletion20261015'
items = json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
recipes = json.loads((P/'Content/ColdSteelData/campfire-recipes.json').read_text(encoding='utf-8-sig'))['recipes']
issues = []; rows = []
families = {'roast_chicken_leg': 'ChickenLeg', 'roast_lamb_ribs': 'LambRibs',
            'roast_sausage': 'Sausage', 'roast_large_lamb': 'LargeLamb'}
for recipe in recipes:
    if not recipe.get('enabled', True): continue
    family = families.get(recipe['id'])
    if family is None: issues.append('Missing presentation mapping '+recipe['id']); continue
    row = {'recipe': recipe['id'], 'seconds': recipe['seconds'], 'food': []}
    for state, key in [('Raw', 'input'), ('Roasted', 'output')]:
        definition = items[recipe[key]['item']]
        path = f'/Game/Items/Consumables/{family}20261014/{state}/SM_{state}{family}'
        mesh = u.load_asset(path)
        if not isinstance(mesh, u.StaticMesh): issues.append('Missing mesh '+path)
        else:
            if any(slot.material_interface is None for slot in mesh.get_editor_property('static_materials')):
                issues.append('Unassigned material '+path)
        icon = P/'Content/ColdSteelData'/definition.get('ue_icon', '')
        if not icon.is_file(): issues.append('Missing food icon '+definition['id'])
        row['food'].append({'id': definition['id'], 'mesh': path, 'icon': str(icon)})
    rows.append(row)
cls = u.load_class(None, '/Script/FPSGAME.ColdSteelCampfire')
cdo = u.get_default_object(cls)
for name in ('CampfireBody', 'RoastingSupports', 'RoastingSpit'):
    component = u.find_object(cdo, name)
    if component is None or component.get_editor_property('static_mesh') is None:
        issues.append('Missing native component mesh '+name)
spit = u.find_object(cdo, 'RoastingSpit')
if spit and abs(spit.get_editor_property('relative_location').z-70.2) > .01:
    issues.append('Spit height differs from cooking presentation')
for path in ('/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire',
             '/Game/Fluids/FluidInteractions20260924/NS_WaterImpactSteam',
             '/Game/FreeGameSoundsVol1/SFX/Sizzle_Bacon_Frying/Sizzle_Bacon_Frying_01'):
    if u.load_asset(path) is None: issues.append('Missing shared presentation asset '+path)
palette = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entries = [e for e in palette.get_editor_property('components') if str(e.id)=='campfire']
if len(entries) != 1: issues.append('Campfire palette entry is missing or duplicated')
result = {'enabled_recipes': len(rows), 'rows': rows, 'issues': issues,
          'assets_modified': False, 'rendered': False, 'listened_to_audio': False}
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'asset-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('CAMPFIRE_ASSET_CHECK', json.dumps({'recipes': len(rows), 'issues': issues}))
if issues: raise RuntimeError('Campfire asset audit failed')
