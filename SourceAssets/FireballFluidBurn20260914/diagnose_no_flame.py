"""Read fireball material output wiring and emitter setup for the no-flame bug."""
import json
import sys
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(root / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters

out = {}
for label in ['A', 'B']:
    mat = unreal.load_asset('/Game/Skills/Fireball/FluidBurn20260914/M_FireballFluid_' + label)
    info = {'attributes': str(mat.get_editor_property('use_material_attributes')),
            'blend': str(mat.get_editor_property('blend_mode')), 'nodes': [], 'outputs': {}}
    for prop in [unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY]:
        node = LIB.get_material_property_input_node(mat, prop)
        info['outputs'][str(prop)] = str(node)
    for node in LIB.get_material_expressions(mat):
        data = {'name': node.get_name(), 'type': node.get_class().get_name(),
                'pins': [str(x) for x in LIB.get_material_expression_input_names(node)],
                'outputs': [str(x) for x in LIB.get_material_expression_output_names(node)],
                'sources': [str(x) for x in LIB.get_inputs_for_material_expression(mat, node)]}
        if isinstance(node, unreal.MaterialExpressionScalarParameter):
            data['parameter'] = str(node.get_editor_property('parameter_name'))
            data['value'] = node.get_editor_property('default_value')
        info['nodes'].append(data)
    out[label] = info
system = unreal.load_asset('/Game/Skills/Fireball/NS_FireballSlowBurnCore')
out['emitters'] = {}
out['renderers'] = {}
for name in emitters(system):
    topo = API.call_method('GetEmitterTopology', (ref(system, name),))
    out['emitters'][name] = topo.export_text()
    values = json.loads(API.call_method('GetRendererData', (ref(system,name,renderer=0),)).get_editor_property('property_values'))
    out['renderers'][name] = {key:value for key,value in values.items()
                            if any(term.lower() in key.lower() for term in ['cutout','bound','material','sort','opacity','alpha'])}
(root / 'SourceAssets/FireballFluidBurn20260914/no-flame-diagnosis.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
unreal.log('FIREBALL_NO_FLAME_DIAGNOSIS_WRITTEN')
