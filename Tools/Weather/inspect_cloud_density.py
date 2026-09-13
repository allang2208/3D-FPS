"""Read cloud parameters and expression wiring. Does not modify assets or run PIE."""
import json
from pathlib import Path
import unreal as u

out = Path(u.Paths.project_saved_dir()) / 'CloudDensityDiagnosis'
out.mkdir(parents=True, exist_ok=True)
lib = u.MaterialEditingLibrary
report = {'assets': [], 'graphs': {}}

def path(obj):
    return obj.get_path_name() if obj else None

def graph(obj):
    key = path(obj)
    if key in report['graphs']:
        return
    rows = []
    report['graphs'][key] = rows
    is_material = isinstance(obj, u.Material)
    nodes = (lib.get_material_expressions(obj) if is_material
             else lib.get_material_function_expressions(obj))
    functions = []
    for node in nodes:
        row = {'id': node.get_name(), 'type': node.get_class().get_name(), 'properties': {}}
        for prop in ['parameter_name', 'default_value', 'const_a', 'const_b', 'r',
                     'desc', 'material_function', 'input_name', 'output_name', 'code']:
            try:
                value = node.get_editor_property(prop)
                row['properties'][prop] = path(value) if isinstance(value, u.Object) else str(value)
                if prop == 'material_function' and value:
                    functions.append(value)
            except Exception:
                pass
        names = lib.get_material_expression_input_names(node)
        sources = (lib.get_inputs_for_material_expression(obj, node) if is_material
                   else lib.get_inputs_for_material_function_expression(obj, node))
        row['inputs'] = {str(name): (sources[i].get_name() if i < len(sources) and sources[i] else None)
                         for i, name in enumerate(names)}
        rows.append(row)
    for function in functions:
        graph(function)

for asset_path in ['/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst',
                   '/Game/WorldGeneration/TemperateHills/Sky/MI_HillsClouds']:
    obj = u.load_asset(asset_path)
    if not obj:
        raise RuntimeError('Missing cloud material: ' + asset_path)
    row = {'path': path(obj), 'scalars': {}, 'vectors': {}, 'parents': []}
    for name in lib.get_scalar_parameter_names(obj):
        row['scalars'][str(name)] = lib.get_material_instance_scalar_parameter_value(obj, name)
    for name in lib.get_vector_parameter_names(obj):
        row['vectors'][str(name)] = str(lib.get_material_instance_vector_parameter_value(obj, name))
    root = obj
    while isinstance(root, u.MaterialInstance):
        root = root.get_editor_property('parent')
        row['parents'].append(path(root))
    row['domain'] = str(root.get_editor_property('material_domain'))
    graph(root)
    report['assets'].append(row)

(out / 'material-wiring.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('CLOUD_DENSITY_INSPECTION_COMPLETE ' + str(out / 'material-wiring.json'))
