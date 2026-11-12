"""Read imported forest source assets and the live biome; no asset mutation."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestSpecies20261110')
LIB = u.MaterialEditingLibrary
r = u.AssetRegistryHelpers.get_asset_registry()
r.scan_paths_synchronous(['/Game/Megaplant_Library', '/Game/Megascans', '/Game/Fab'], False)
report = {'imports': [], 'meshes': [], 'materials': {}, 'biome': {}}

def path(obj):
    return obj.get_path_name() if obj else None

def material(mat):
    key = path(mat)
    if not mat or key in report['materials']:
        return
    row = {'class': mat.get_class().get_name()}
    if isinstance(mat, u.MaterialInstanceConstant):
        row['parent'] = path(mat.get_editor_property('parent'))
        row['scalars'] = {str(k): LIB.get_material_instance_scalar_parameter_value(mat, k)
                          for k in LIB.get_scalar_parameter_names(mat)}
        row['switches'] = {str(k): LIB.get_material_instance_static_switch_parameter_value(mat, k)
                           for k in LIB.get_static_switch_parameter_names(mat)}
        row['textures'] = {str(k): path(LIB.get_material_instance_texture_parameter_value(mat, k))
                           for k in LIB.get_texture_parameter_names(mat)}
    report['materials'][key] = row

for asset in r.get_assets_by_path('/Game/Megaplant_Library', True):
    name, cls = str(asset.package_name), str(asset.asset_class_path.asset_name)
    if 'Tree_Black_Poplar' in name:
        continue
    report['imports'].append({'path': name, 'class': cls})
    # Full exported plants only. Instance/twig/leaf assembly parts stay source-only.
    if cls not in ('SkeletalMesh', 'StaticMesh') or '/Instances/' in name:
        continue
    mesh = asset.get_asset()
    bounds = mesh.get_bounds()
    mats = [s.get_editor_property('material_interface') for s in mesh.get_editor_property('materials')] if cls == 'SkeletalMesh' else [s.get_editor_property('material_interface') for s in mesh.get_editor_property('static_materials')]
    row = {'path': name, 'class': cls,
           'origin': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
           'extent': [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
           'materials': [path(m) for m in mats]}
    for prop in ('nanite_settings', 'default_mesh_deformer', 'physics_asset', 'skeleton'):
        try:
            row[prop] = str(mesh.get_editor_property(prop))
        except Exception:
            pass
    report['meshes'].append(row)
    for mat in mats:
        material(mat)

da = u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
for name in ('trees', 'shrubs', 'grass', 'grass_accents', 'graphs', 'backdrop_trees', 'river_understory'):
    report['biome'][name] = [path(x) for x in da.get_editor_property(name)]
report['biome']['ground_material'] = path(da.get_editor_property('ground_material'))
for name in ('grass_coverage', 'meadow_flower_coverage', 'forest_floor_coverage'):
    report['biome'][name] = da.get_editor_property(name)
(ROOT / 'sources.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('FOREST_SPECIES_SOURCES_CAPTURED ' + str(len(report['meshes'])))
