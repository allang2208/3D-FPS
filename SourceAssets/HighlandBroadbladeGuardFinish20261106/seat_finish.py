"""Material boundaries in Highland mesh-local centimetres (+Z towards the tip)."""
import unreal as u

NATIVE_METAL = 'M_BroadbladeGuard_HighlandClaymoreSurface'
REVISION = 'HighlandBroadbladeSeat20261107'
EDITOR = u.MaterialEditingLibrary


def native_protection(material):
    if material.get_name() != NATIVE_METAL:
        # The split Cloven wing and recess are entirely decorative guard slots.
        return 'return 1.0;'
    # JunctionBlendV5 author_junction_v5.master() welds the OLD physical
    # blade/guard seam z=.005+.95*abs(x) before cutting the module higher.
    # The span between those seams is a piece of blade now owned by the guard.
    return """
float fromSeat = P.z - (0.5 + 0.95 * abs(P.x));
float seat = smoothstep(0.0, 0.08, fromSeat);
float dz = P.z + 0.1589306;
float diamond = abs(P.x + 0.02)/1.32 + (dz >= 0 ? dz/2.02 : -dz/1.67);
float outsideBezel = smoothstep(1.22, 1.28, diamond);
return 1.0 - seat * outsideBezel;
"""


def bind_gale_seat(material, fields, wire, root, input_of):
    """Limit the broadblade insert above the rolled collar to the blade finish."""
    is_seat_steel = material.get_name() == 'M_GaleWing_Broadblade_Steel'
    if is_seat_steel:
        position = EDITOR.create_material_expression(material, u.MaterialExpressionPreSkinnedPosition)
        interpolated = EDITOR.create_material_expression(material, u.MaterialExpressionVertexInterpolator)
        wire(position, interpolated, 'Input')
        mask = EDITOR.create_material_expression(material, u.MaterialExpressionCustom)
        pin = u.CustomInput()
        pin.set_editor_property('input_name', 'P')
        mask.set_editor_property('inputs', [pin])
        mask.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
        mask.set_editor_property('desc', REVISION + ' Gale Wing seat')
        # Upper lip ends at +0.50 cm. Insert width tapers from 3.28 cm to
        # the V5 blade contour. Wing caps, star housing and rails stay native.
        mask.set_editor_property('code', """
float aboveLip = smoothstep(0.50, 0.60, P.z);
float withinSeat = 1.0 - smoothstep(3.28, 3.36, abs(P.x));
return aboveLip * withinSeat;
""")
        wire(interpolated, mask, 'P')

    substrate, _ = root(material, 'FRONT_MATERIAL')
    for field, pin_name in [('BASE_COLOR','BaseColor'), ('NORMAL','Normal'),
                           ('ROUGHNESS','Roughness'), ('METALLIC','Metallic'),
                           ('ANISOTROPY','Anisotropy'), ('TANGENT','Tangent')]:
        finish = fields[field]
        base, channel = input_of(material, finish, 'Base')
        if is_seat_steel:
            result = EDITOR.create_material_expression(material, u.MaterialExpressionLinearInterpolate)
            wire(base, result, 'A', channel)
            wire(finish, result, 'B')
            wire(mask, result, 'Alpha')
            channel = ''
        else:
            # The polished material covers the rolled lips and end caps only.
            result = base
        if not EDITOR.connect_material_property(result, channel, getattr(u.MaterialProperty, 'MP_' + field)):
            raise RuntimeError('Could not connect ' + field)
        if substrate:
            wire(result, substrate, pin_name, channel)
