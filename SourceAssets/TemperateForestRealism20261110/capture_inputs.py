"""Read the existing biome and candidate art needed for this authoring batch."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestRealism20261110')
ROOT.mkdir(parents=True, exist_ok=True)
DA = u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
if not DA:
    raise RuntimeError('The installed hills biome is missing')

def path(obj):
    if obj is None:
        return None
    return obj.get_path_name() if hasattr(obj, 'get_path_name') else str(obj)

fields = ['ground_material', 'trees', 'rocks', 'shrubs', 'grass', 'grass_accents',
          'meadow_flowers', 'fallen_logs', 'forest_roots', 'cliffs', 'backdrop_trees',
          'river_ground_cover', 'river_understory', 'graphs']
result = {'asset': DA.get_path_name(), 'fields': {}, 'scalars': {}, 'candidates': []}
for name in fields:
    value = DA.get_editor_property(name)
    result['fields'][name] = [path(v) for v in value] if isinstance(value, u.Array) else path(value)
for name in ['grass_spacing_cm', 'grass_coverage', 'grass_accent_spacing_cm',
             'grass_accent_coverage', 'meadow_flower_coverage', 'forest_floor_coverage',
             'cliff_coverage', 'backdrop_tree_budget', 'ground_debris_coverage']:
    result['scalars'][name] = DA.get_editor_property(name)

ar = u.AssetRegistryHelpers.get_asset_registry()
for prefix in ['/Game/PN_FoliageCollection', '/Game/PN_GrassLibrary', '/Game/RuralAustralia',
               '/Game/Megascans', '/Game/WorldGeneration/TemperateHills']:
    for a in ar.get_assets_by_path(prefix, recursive=True):
        name = str(a.asset_name)
        cls = str(a.asset_class_path.asset_name)
        p = str(a.package_name)
        if cls in ('StaticMesh', 'SkeletalMesh') and any(x in name.lower() for x in
                ('fern', 'root', 'log_', 'sapling', 'seedling', 'tree', 'poplar', 'beech', 'shrub', 'planttype')):
            result['candidates'].append({'path': p, 'class': cls})
        elif cls == 'Texture2D' and any(x in name.lower() for x in
                ('ground', 'forest', 'litter', 'leaves', 'moss', 'soil')):
            result['candidates'].append({'path': p, 'class': cls})

result['ground_parameters'] = {}
mat = u.load_asset(result['fields']['ground_material'])
for name in u.MaterialEditingLibrary.get_scalar_parameter_names(mat):
    result['ground_parameters'][str(name)] = u.MaterialEditingLibrary.get_material_default_scalar_parameter_value(mat, name)
(ROOT / 'inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
u.log('FOREST_INPUTS_CAPTURED ' + json.dumps({'pools': {k: len(v) if isinstance(v, list) else v for k,v in result['fields'].items()}, 'candidates':len(result['candidates'])}))
