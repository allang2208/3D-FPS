"""Add a fixed-mask traveling pulse to the existing opaque knife rune surface."""
from pathlib import Path
import unreal as u

L = u.MaterialEditingLibrary
MARKER = 'AllWeaponRuneFlow20261102'

def add_knife_flow(mat, start, length):
    nodes = list(L.get_material_expressions(mat))
    if any(isinstance(n, u.MaterialExpressionCustom) and MARKER in n.get_editor_property('code') for n in nodes):
        for n in nodes:
            if isinstance(n, u.MaterialExpressionScalarParameter):
                key = str(n.get_editor_property('parameter_name'))
                if key in ('RuneFlowBladeStart', 'RuneFlowBladeLength'):
                    n.set_editor_property('default_value', float(start if key == 'RuneFlowBladeStart' else length))
        return False
    parameters = {str(n.get_editor_property('parameter_name')): n for n in nodes
                  if isinstance(n, (u.MaterialExpressionVectorParameter, u.MaterialExpressionTextureSampleParameter2D))}
    front = L.get_material_property_input_node(mat, u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(front, u.MaterialExpressionSubstrateShadingModels):
        raise RuntimeError('Unexpected knife shading graph: ' + mat.get_path_name())
    names = list(L.get_material_expression_input_names(front))
    inputs = list(L.get_inputs_for_material_expression(mat, front))
    if inputs[names.index('Emissive Color')]:
        raise RuntimeError('Preserve existing knife emission: ' + mat.get_path_name())
    ink, tint = parameters['RuneMask'], parameters['RuneTint']

    def node(cls, **props):
        obj = L.create_material_expression(mat, cls, -1100, 950)
        obj.set_editor_properties(props)
        return obj

    def wire(source, target, pin, output=''):
        if not L.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Cannot connect rune flow ' + pin)

    def scalar(name, value):
        return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(value))

    local = node(u.MaterialExpressionPreSkinnedPosition)
    interpolated = node(u.MaterialExpressionVertexInterpolator)
    wire(local, interpolated, str(L.get_material_expression_input_names(interpolated)[0]))
    sources = {'P': (interpolated, ''), 'Ink': (ink, 'R'), 'RuneTint': (tint, 'RGB'),
               'T': (node(u.MaterialExpressionTime), ''),
               'PreviewTime': (scalar('PreviewTime', -1), ''),
               'BladeStart': (scalar('RuneFlowBladeStart', start), ''),
               'BladeLength': (scalar('RuneFlowBladeLength', length), ''),
               'GlowStrength': (scalar('RuneFlowGlowStrength', .90), '')}
    custom = node(u.MaterialExpressionCustom,
                  code=(Path(__file__).parent / 'knife_flow.hlsl').read_text(encoding='utf-8'),
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                  description=MARKER + ': native glyph pulse and root-to-tip flow')
    pins = []
    for name in sources:
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    custom.set_editor_property('inputs', pins)
    for name, (source, output) in sources.items(): wire(source, custom, name, output)
    wire(custom, front, 'Emissive Color')
    if not L.connect_material_property(custom, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect legacy emissive output')
    return True
