"""Author M_SiegeRangeIndicator: subtle, slope-masked, upgrade-synced placement decal for village defenses."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[3]
DEST = '/Game/WorldGeneration/TemperateHills/HighVillageDefense/PlacementPreview'
NAME = 'M_SiegeRangeIndicator'
PATH = f'{DEST}/{NAME}'
RECEIPT = Path('F:/FPSGAMEData/ArtProduction/HighVillageDefense/SiegeRangeIndicator-20261127/published.json')

EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary


def build():
    if ROOT != Path('D:/FPS3D/FPSGAME').resolve():
        raise RuntimeError('Authoring script belongs to D:/FPS3D/FPSGAME')
    EAL.make_directory(DEST)
    material = u.load_asset(PATH) if EAL.does_asset_exist(PATH) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        NAME, DEST, u.Material, u.MaterialFactoryNew())
    if not material:
        raise RuntimeError(f'Cannot create/load {PATH}')

    LIB.delete_all_material_expressions(material)
    material.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)

    def parameter(param_name, default_val):
        is_vec = isinstance(default_val, u.LinearColor)
        expr = LIB.create_material_expression(
            material, u.MaterialExpressionVectorParameter if is_vec else u.MaterialExpressionScalarParameter)
        expr.set_editor_property('parameter_name', param_name)
        expr.set_editor_property('default_value', default_val)
        return expr, ('RGB' if is_vec else '')

    def custom(code, inputs, output_type):
        expr = LIB.create_material_expression(material, u.MaterialExpressionCustom)
        expr.set_editor_property('code', code)
        expr.set_editor_property('output_type', output_type)
        pins = []
        for pin_name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', pin_name)
            pins.append(pin)
        expr.set_editor_property('inputs', pins)
        for pin_name, (src, ch) in inputs.items():
            if not LIB.connect_material_expressions(src, ch, expr, pin_name):
                raise RuntimeError(f'Failed connecting {pin_name}')
        return expr

    world = LIB.create_material_expression(material, u.MaterialExpressionWorldPosition)
    center = parameter('Center', u.LinearColor(0.0, 0.0, 0.0, 1.0))
    ring_color = parameter('RingColor', u.LinearColor(0.26, 0.80, 1.0, 1.0))
    fill_color = parameter('FillColor', u.LinearColor(0.14, 0.52, 0.72, 1.0))
    outer_r = parameter('OuterRadius', 5200.0)
    inner_r = parameter('InnerRadius', 0.0)
    fill_inner = parameter('FillInner', 0.0)
    vert_span = parameter('VerticalSpan', 3500.0)
    opacity_scale = parameter('OpacityScale', 1.0)

    common_math = '''
float3 delta = World - Center;
float d = length(delta.xy);
float3 rawN = cross(ddx(World), ddy(World));
float len2 = dot(rawN, rawN);
float upMask = len2 > 1e-6 ? smoothstep(0.42, 0.72, abs(rawN.z) * rsqrt(len2)) : 1.0;
float vertFade = 1.0 - smoothstep(VerticalSpan * 0.85, VerticalSpan, abs(delta.z));

float px = max(fwidth(d), 0.5);
float lineW = clamp(px * 1.45, max(4.5, OuterRadius * 0.0022), max(22.0, OuterRadius * 0.010));
float outerLine = 1.0 - smoothstep(lineW * 0.55, lineW * 1.40, abs(d - OuterRadius));
float echoR = max(0.0, OuterRadius - max(28.0, OuterRadius * 0.014));
float echoLine = (1.0 - smoothstep(lineW * 0.40, lineW * 1.10, abs(d - echoR))) * 0.24;

float inOuter = 1.0 - smoothstep(OuterRadius - lineW * 0.5, OuterRadius + lineW * 0.5, d);
float rimW = clamp(OuterRadius * 0.055, 40.0, 420.0);
float rimFeather = inOuter * smoothstep(OuterRadius - rimW, OuterRadius, d) * 0.13;

float inRingBand = InnerRadius > 1.0 ? smoothstep(InnerRadius - lineW * 0.5, InnerRadius + lineW * 0.5, d) : 1.0;
float activeFillMask = lerp(inRingBand, 1.0, saturate(FillInner)) * inOuter;

float ang = atan2(delta.y, delta.x);
float dashFreq = clamp(floor(InnerRadius / 55.0 + 0.5), 14.0, 44.0);
float dash = smoothstep(0.10, 0.35, sin(ang * dashFreq));
float innerLine = InnerRadius > 1.0 ? (1.0 - smoothstep(lineW * 0.45, lineW * 1.25, abs(d - InnerRadius))) * lerp(0.16, 0.62, dash) : 0.0;

float effInner = FillInner > 0.5 ? 0.0 : InnerRadius;
float radialT = saturate((d - effInner) / max(1.0, OuterRadius - effInner));
float bgWash = activeFillMask * lerp(0.024, 0.072, pow(radialT, 1.75));
float lineWeight = saturate(outerLine * 0.82 + echoLine + innerLine * 0.78);
'''
    base_inputs = {
        'World': (world, ''),
        'Center': center,
        'OuterRadius': outer_r,
        'InnerRadius': inner_r,
        'FillInner': fill_inner,
        'VerticalSpan': vert_span,
        'OpacityScale': opacity_scale,
    }
    opacity_out = custom(
        common_math + '\nreturn saturate((bgWash + rimFeather * activeFillMask + lineWeight) * OpacityScale) * upMask * vertFade;',
        base_inputs,
        u.CustomMaterialOutputType.CMOT_FLOAT1,
    )
    color_out = custom(
        common_math + '\nreturn lerp(FillColor, RingColor, saturate(lineWeight * 1.15));',
        {**base_inputs, 'FillColor': fill_color, 'RingColor': ring_color},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    emissive_out = custom(
        common_math + '\nfloat glow = saturate(lineWeight * 1.2 + rimFeather * activeFillMask * 2.5) * OpacityScale;\nreturn lerp(FillColor * 0.32, RingColor * 1.30, glow);',
        {**base_inputs, 'FillColor': fill_color, 'RingColor': ring_color},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )

    for node, prop in [
        (opacity_out, u.MaterialProperty.MP_OPACITY),
        (color_out, u.MaterialProperty.MP_BASE_COLOR),
        (emissive_out, u.MaterialProperty.MP_EMISSIVE_COLOR),
    ]:
        if not LIB.connect_material_property(node, '', prop):
            raise RuntimeError(f'Failed connecting {prop}')

    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError(str(errors))
    if hasattr(u, 'DragonBreathAuthorLibrary') and not u.DragonBreathAuthorLibrary.compile_material_assets([material]):
        raise RuntimeError('M_SiegeRangeIndicator compilation failed')
    if not EAL.save_loaded_asset(material, False):
        raise RuntimeError('Failed saving M_SiegeRangeIndicator')

    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(
        json.dumps(
            {
                'complete': True,
                'asset': material.get_path_name(),
                'parameters': ['Center', 'RingColor', 'FillColor', 'OuterRadius', 'InnerRadius', 'FillInner', 'VerticalSpan', 'OpacityScale'],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )
    u.log('SIEGE_RANGE_INDICATOR_SAVED ' + material.get_path_name())


if __name__ == '__main__':
    build()
