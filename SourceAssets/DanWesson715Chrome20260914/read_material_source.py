"""Read downloaded material graph inputs needed to author the 715 adaptation."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
L = u.MaterialEditingLibrary
report = {'assets': [], 'graphs': {}}
def path(obj):
    return obj.get_path_name() if obj else None

def graph(obj):
    key = path(obj)
    if key in report['graphs']: return
    rows = []; report['graphs'][key] = rows
    is_material = isinstance(obj, u.Material)
    nodes = L.get_material_expressions(obj) if is_material else L.get_material_function_expressions(obj)
    functions = []
    for node in nodes:
        row = {'id': node.get_name(), 'type': node.get_class().get_name(), 'properties': {}}
        for prop in ['parameter_name','default_value','texture','const_a','const_b','r','desc','material_function','input_name','output_name','code','tangent_space_normal']:
            try:
                value = node.get_editor_property(prop)
                row['properties'][prop] = path(value) if isinstance(value,u.Object) else str(value)
                if prop == 'material_function' and value and '/SubstrateMaterials/' in path(value): functions.append(value)
            except Exception: pass
        names = L.get_material_expression_input_names(node)
        sources = L.get_inputs_for_material_expression(obj,node) if is_material else L.get_inputs_for_material_function_expression(obj,node)
        row['inputs'] = {str(name): path(sources[i]) if i < len(sources) else None for i,name in enumerate(names)}
        row['outputs'] = [str(n) for n in L.get_material_expression_output_names(node)]
        rows.append(row)
    for fn in functions: graph(fn)

for source in ['/Game/SubstrateMaterials/Materials/03_Metals/1_Basic/MI_Chromium', '/Game/SubstrateMaterials/Materials/03_Metals/1_Basic/MI_Silver']:
    obj = u.load_asset(source)
    if not obj: raise RuntimeError(source)
    row = {'path': path(obj),'parents':[]}
    for category, getter in [('scalar','scalar'),('vector','vector'),('texture','texture'),('static_switch','static_switch')]:
        values = {}
        for name in getattr(L,'get_'+category+'_parameter_names')(obj):
            value = getattr(L,'get_material_instance_'+getter+'_parameter_value')(obj,name)
            values[str(name)] = path(value) if isinstance(value,u.Object) else str(value) if category == 'vector' else value
        row[category] = values
    root = obj
    while isinstance(root,u.MaterialInstance):
        root = root.get_editor_property('parent'); row['parents'].append(path(root))
    graph(root)
    report['assets'].append(row)
mirror = json.loads((O.parent/'DanWesson715Mirror20260914/import.json').read_text())
for source in mirror['attachment_materials'].values(): graph(u.load_asset(source))
(O/'source-material.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('DW715_CHROME_SOURCE_READ')
