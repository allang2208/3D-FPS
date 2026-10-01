"""Read saved level weather routes and simulate only the material copy operation."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Use a read-only headless commandlet; do not replace an open editor level')
if Path(u.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
result = {'level': '/Game/GameMaps/DayNight_Lighting', 'weather_actors': [], 'material_copies': []}
world = u.EditorLoadingAndSavingUtils.load_map(result['level'])
if not world:
    raise RuntimeError('Cannot read saved default map')
main_path = '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative'
mesh = u.load_asset(main_path)
current = json.loads((O.parent / 'current_surface_bindings.json').read_text())
paths = set(current['meshes'][mesh.get_path_name()].values())
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.FPSWeatherManager):
    library = actor.get_editor_property('presentation_library')
    asset = library if isinstance(library, u.Object) else u.load_asset(str(library)) if library else None
    result['weather_actors'].append({'path': actor.get_path_name(), 'class': actor.get_class().get_path_name(),
        'library': str(library), 'library_object': asset.get_path_name() if asset else None,
        'new_material_mappings': {str(k): v.get_path_name() if v else None
            for k, v in dict(asset.get_editor_property('wet_materials')).items() if str(k) in paths} if asset else {}})
if not result['weather_actors']:
    result['fallback_library'] = str(u.get_default_object(u.FPSWeatherManager).get_editor_property('presentation_library'))
library = u.load_asset('/Game/Weather/RainVisibility/DA_WeatherPresentation')
mapping = dict(library.get_editor_property('wet_materials'))
for index, slot in enumerate(mesh.get_editor_property('materials')[:4]):
    source = slot.material_interface
    replacement = mapping.get(source.get_path_name())
    mid = u.MaterialLibrary.create_dynamic_material_instance(world, replacement or source)
    # Blueprint quick-copy forwards to the same CopyMaterialUniformParameters
    # used by WeatherViewEffectsComponent::AcquireWet (UE 5.8 engine source).
    mid.copy_material_instance_parameters(source, True)
    mid.set_scalar_parameter_value('WeaponWetness', 0.)
    result['material_copies'].append({'slot': index, 'source': source.get_path_name(),
        'replacement': replacement.get_path_name() if replacement else None,
        'mid_parent': mid.get_editor_property('parent').get_path_name(),
        'scalars': {name: mid.get_scalar_parameter_value(name)
            for name in ('R01_Roughness', 'R01_SourceRoughnessWeight', 'R02_SourceColorContrast', 'WeaponWetness')}})
(O / 'saved-world-routes.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_AKM_SAVED_WORLD_ROUTES', json.dumps(result), flush=True)
