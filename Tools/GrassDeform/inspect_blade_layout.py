"""Read the live grass graph and mesh schema without changing assets or play state."""
import json
from pathlib import Path
import unreal as u

out = Path(u.Paths.project_saved_dir()) / 'GrassShape20260927'
out.mkdir(parents=True, exist_ok=True)
L = u.MaterialEditingLibrary
result = {'worlds': [], 'graphs': {}, 'meshes': {}}
for world in u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(), u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world():
    if world:
        result['worlds'].append(world.get_path_name())

def graph(obj):
    path = obj.get_path_name()
    if path in result['graphs']:
        return
    nodes = list(L.get_material_function_expressions(obj) if isinstance(obj, u.MaterialFunction) else L.get_material_expressions(obj))
    result['graphs'][path] = []
    for n in nodes:
        row = {'name': n.get_name(), 'type': n.get_class().get_name()}
        for prop in ['desc', 'parameter_name', 'code', 'coordinate_index', 'material_function', 'texture', 'default_value', 'constant', 'mask_r', 'mask_g', 'mask_b', 'mask_a', 'input_name', 'output_name', 'transform_source_type', 'transform_type', 'r', 'a', 'b', 'filter', 'sampler_type', 'mip_value_mode']:
            try:
                row[prop] = str(n.get_editor_property(prop))
            except Exception:
                pass
        try:
            inputs = (L.get_inputs_for_material_function_expression(obj, n) if isinstance(obj, u.MaterialFunction)
                      else L.get_inputs_for_material_expression(obj, n))
            row['inputs'] = [x.get_name() if x else None for x in inputs]
        except Exception:
            pass
        result['graphs'][path].append(row)
        if isinstance(n, u.MaterialExpressionMaterialFunctionCall):
            fn = n.get_editor_property('material_function')
            if fn and isinstance(fn, u.MaterialFunction):
                graph(fn)

for path in ['/Game/PN_GrassLibrary/Materials/grassMaterials/MA_Grass', '/Game/WorldGeneration/TemperateHills/Grass/M_TemperateMeadow']:
    graph(u.load_asset(path))
for path in ['/Game/WorldGeneration/TemperateHills/Grass/SM_Meadow_grass_03_08_mesh', '/Game/WorldGeneration/TemperateHills/Grass/SM_Meadow_grass_05_03_mesh']:
    mesh = u.load_asset(path)
    mats = []
    for slot in mesh.static_materials:
        mat = slot.material_interface
        params = []
        for name in L.get_texture_parameter_names(mat):
            tex = L.get_material_instance_texture_parameter_value(mat, name)
            params.append({'name': str(name), 'texture': tex.get_path_name() if tex else None,
                           'filter': str(tex.get_editor_property('filter')) if tex else None})
        mats.append({'path': mat.get_path_name(), 'textures': params})
    result['meshes'][path] = {'bounds': str(mesh.get_bounds()), 'lods': mesh.get_num_lods(), 'materials': mats}
(out / 'live-graph.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('GRASS_SHAPE_READ ' + json.dumps({'worlds': result['worlds'], 'graphs': list(result['graphs']), 'meshes': result['meshes']}))
