"""Route the six steel shader inputs through the fitted seat boundary on guard components."""
from pathlib import Path
import runpy
import unreal as u

L = u.MaterialEditingLibrary
LABEL = 'Forged steel blade seat coverage'


def apply(material):
    expressions = list(L.get_material_expressions(material))
    modes = [n for n in expressions if isinstance(n, u.MaterialExpressionScalarParameter)
             and str(n.get_editor_property('parameter_name')) == 'BladeFinishMode']
    mode, = modes
    gate = next((n for n in expressions if isinstance(n, u.MaterialExpressionCustom)
                 and n.get_editor_property('desc') == LABEL), None)
    profile = runpy.run_path(str(Path(__file__).with_name('seat_profile.py')))
    code = profile['mode_shader']()
    damascus, = [n for n in expressions if isinstance(n, u.MaterialExpressionCustom)
                 and str(n.get_editor_property('desc')).endswith(' solid profile')]
    coordinates = profile['damascus_shader']()
    changed = damascus.get_editor_property('code') != coordinates
    if changed:
        damascus.set_editor_property('code', coordinates)
    if not gate:
        local_position = next(n for n in expressions if isinstance(n, u.MaterialExpressionVertexInterpolator)
                              and any(isinstance(i, u.MaterialExpressionPreSkinnedPosition)
                                      for i in L.get_inputs_for_material_expression(material, n)))
        scope = L.create_material_expression(material, u.MaterialExpressionScalarParameter)
        scope.set_editor_property('parameter_name', 'BladeFinishGuardRoot')
        scope.set_editor_property('default_value', 0.0)
        gate = L.create_material_expression(material, u.MaterialExpressionCustom)
        gate.set_editor_property('desc', LABEL)
        gate.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
        inputs = []
        for name in ('Mode', 'GuardRoot', 'P'):
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            inputs.append(pin)
        gate.set_editor_property('inputs', inputs)
        for source, name in zip((mode, scope, local_position), ('Mode', 'GuardRoot', 'P')):
            if not L.connect_material_expressions(source, '', gate, name):
                raise RuntimeError('Could not connect seat ' + name)
        changed = True
    if gate.get_editor_property('code') != code:
        gate.set_editor_property('code', code)
        changed = True
    fields = set()
    for n in expressions:
        if n == gate:
            continue
        for name, source in zip(L.get_material_expression_input_names(n), L.get_inputs_for_material_expression(material, n)):
            if source != mode and source != gate:
                continue
            if source == mode:
                if not L.connect_material_expressions(gate, '', n, str(name)):
                    raise RuntimeError('Could not route seat coverage into ' + n.get_name())
                changed = True
            fields.add(str(n.get_editor_property('desc')).split()[-1])
    if not {'BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','ANISOTROPY','TANGENT'} <= fields:
        raise RuntimeError('Incomplete fitted steel graph: ' + str(fields))
    if changed:
        errors = list(L.recompile_material(material))
        if errors or not u.EditorAssetLibrary.save_loaded_asset(material, False):
            raise RuntimeError('Could not save seat material ' + str(errors))
    return sorted(fields)
