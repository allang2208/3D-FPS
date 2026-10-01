"""User-requested read-only diagnosis of held AKM vs asset/preview material routes."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

O = Path(__file__).parent
if Path(u.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
L = u.MaterialEditingLibrary
current = json.loads((O.parent / 'current_surface_bindings.json').read_text())
main = '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative.SK_AKM_MannyNative'
result = {'asset': {}, 'runtime': [], 'weather': [], 'materials': {}, 'pie': False}


def describe(mat):
    if not mat:
        return None
    path = mat.get_path_name()
    if path in result['materials']:
        return path
    info = {'class': mat.get_class().get_name(), 'base': mat.get_base_material().get_path_name()}
    result['materials'][path] = info
    if isinstance(mat, u.MaterialInstance):
        info['parent'] = describe(mat.get_editor_property('parent'))
        info['scalar_overrides'] = {str(v.parameter_info.name): float(v.parameter_value)
            for v in mat.get_editor_property('scalar_parameter_values')}
        info['vector_overrides'] = {str(v.parameter_info.name): [v.parameter_value.r, v.parameter_value.g, v.parameter_value.b]
            for v in mat.get_editor_property('vector_parameter_values')}
    return path


asset = u.load_asset(main)
result['asset'] = {'path': main, 'slots': [
    {'index': i, 'name': str(s.material_slot_name), 'material': describe(s.material_interface)}
    for i, s in enumerate(asset.get_editor_property('materials'))]}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result['pie'] = bool(world)
if world:
    result['world'] = world.get_path_name()
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter):
        row = {'actor': actor.get_path_name(), 'components': []}
        for comp in actor.get_components_by_class(u.MeshComponent):
            if isinstance(comp, u.SkeletalMeshComponent):
                mesh = comp.get_editor_property('skeletal_mesh_asset')
            elif isinstance(comp, u.StaticMeshComponent):
                mesh = comp.get_editor_property('static_mesh')
            else:
                continue
            if not mesh:
                continue
            if comp.get_name() != 'AKMViewmodel' and 'AKM' not in mesh.get_path_name():
                continue
            row['components'].append({'name': comp.get_name(), 'mesh': mesh.get_path_name(),
                'visible': comp.is_visible(), 'materials': [describe(comp.get_material(i)) for i in range(comp.get_num_materials())]})
        result['runtime'].append(row)
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.FPSWeatherManager):
        for comp in actor.get_components_by_class(u.WeatherViewEffectsComponent):
            data = comp.get_editor_property('assets')
            mapping = dict(data.get_editor_property('wet_materials')) if data else {}
            relevant = {str(k): describe(v) for k, v in mapping.items()
                if '/AKMIntegration/' in str(k) and ('SurfaceStandard20261001' in str(k) or 'Soviet_PBR' in str(k))}
            result['weather'].append({'actor': actor.get_path_name(), 'assets': data.get_path_name() if data else None,
                'mappings': relevant, 'bindings': [
                    {'original': describe(b.get_editor_property('original')), 'wet': describe(b.get_editor_property('wet'))}
                    for b in comp.get_editor_property('bindings')]})
library = u.load_asset('/Game/Weather/RainVisibility/DA_WeatherPresentation')
result['saved_weather'] = {str(k): describe(v) for k, v in dict(library.get_editor_property('wet_materials')).items()
    if str(k) in set(current['meshes'][main].values())}
file = O / ('routes-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
file.write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_AKM_ROUTES_READ', str(file), 'PIE', result['pie'], flush=True)
for s in result['asset']['slots'][:4]:
    print('ASSET_SLOT', s['index'], s['name'], s['material'], flush=True)
for actor in result['runtime']:
    for comp in actor['components']:
        if comp['name'] == 'AKMViewmodel':
            print('HELD_MESH', comp['mesh'], flush=True)
            for i, mat in enumerate(comp['materials'][:4]):
                print('HELD_SLOT', i, mat, result['materials'].get(mat, {}), flush=True)
