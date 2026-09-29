"""Add a zero-default, runtime-only light control without changing transparency."""
import unreal as u

PARAMETER = 'StaffLightAmount'
EXPOSURE_MARKER = 'StaffLightExposureV32'
L = u.MaterialEditingLibrary


def upgrade_light_exposure(material):
    nodes = list(L.get_material_expressions(material))
    if any(str(n.get_editor_property('desc')) == EXPOSURE_MARKER for n in nodes):
        return False
    amount = next(n for n in nodes if isinstance(n, u.MaterialExpressionScalarParameter)
                  and str(n.get_editor_property('parameter_name')) == PARAMETER)
    # V31 has a dedicated color * amount branch. Compensate only that new light,
    # leaving the crystal's original emission and transparency untouched.
    glow = next(n for n in nodes if isinstance(n, u.MaterialExpressionMultiply)
                and amount in L.get_inputs_for_material_expression(material, n))
    inverse = L.create_material_expression(material, u.MaterialExpressionEyeAdaptationInverse)
    inverse.set_editor_property('desc', EXPOSURE_MARKER)
    corrected = L.create_material_expression(material, u.MaterialExpressionMultiply)
    for source, target, pin in ((amount, corrected, 'A'), (inverse, corrected, 'B'), (corrected, glow, 'B')):
        if not L.connect_material_expressions(source, '', target, pin):
            raise RuntimeError('Cannot connect staff light exposure: ' + pin)
    return True


def add_light_control(material):
    if PARAMETER in {str(name) for name in L.get_scalar_parameter_names(material)}:
        return upgrade_light_exposure(material)
    prop = u.MaterialProperty.MP_EMISSIVE_COLOR
    previous = L.get_material_property_input_node(material, prop)
    previous_output = L.get_material_property_input_node_output_name(material, prop) if previous else ''

    amount = L.create_material_expression(material, u.MaterialExpressionScalarParameter)
    amount.set_editor_property('parameter_name', PARAMETER)
    amount.set_editor_property('default_value', 0.)
    color = L.create_material_expression(material, u.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', u.LinearColor(1., .94, .82, 1.))
    glow = L.create_material_expression(material, u.MaterialExpressionMultiply)

    def wire(source, output, target, pin):
        if not L.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Cannot connect staff illumination: ' + pin)

    wire(color, '', glow, 'A')
    wire(amount, '', glow, 'B')
    if previous:
        combined = L.create_material_expression(material, u.MaterialExpressionAdd)
        wire(previous, previous_output, combined, 'A')
        wire(glow, '', combined, 'B')
        glow = combined
    if not L.connect_material_property(glow, '', prop):
        raise RuntimeError('Cannot connect staff illumination output')
    upgrade_light_exposure(material)
    return True
