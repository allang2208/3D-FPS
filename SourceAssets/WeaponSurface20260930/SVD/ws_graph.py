"""SVD-local WS1 graph builder; shared assets and shaders are read only."""
import json
from pathlib import Path
import unreal as u
L=u.MaterialEditingLibrary
O=Path(__file__).parent.parent
card=json.loads((O/'surface_card.json').read_text())
SCALARS=card['master_defaults']['scalars'];VECTORS=card['master_defaults']['vectors'];GROUPS=card['master_defaults']['groups']
ROOT='/Game/Weapons/WeaponSurface'
grain_tex=u.load_asset(ROOT+'/Textures/T_WS_Grain')
mask_tex=u.load_asset(ROOT+'/Textures/T_WS_MaskNeutral')
white_tex=u.load_asset(ROOT+'/Textures/T_WS_White')
grey_tex=u.load_asset(ROOT+'/Textures/T_WS_GreyLinear')
flat_normal=u.load_asset('/Engine/EngineMaterials/DefaultNormal')
CODE={name:(O/'hlsl'/(name+'.hlsl')).read_text(encoding='utf-8-sig') for name in ('WS_Grain','WS_Wear','WS_ColorRough','WS_MetalAO','WS_Beads','WS_Wet','WS_WetNormal')}
def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def wire(src, dest, pin):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, out, dest, pin):
        raise RuntimeError('Cannot connect %s.%s -> %s' % (n.get_name(), out, pin))


def output(src, prop):
    n, out = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_property(n, out, getattr(u.MaterialProperty, 'MP_' + prop)):
        raise RuntimeError('Cannot connect output ' + prop)


def custom(m, name, inputs, size):
    n = node(m, u.MaterialExpressionCustom, code=CODE[name], description=name,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for key, src in inputs.items():
        wire(src, n, key)
    return n


def mask(m, src, channels):
    n = node(m, u.MaterialExpressionComponentMask, r='r' in channels, g='g' in channels,
             b='b' in channels, a='a' in channels)
    wire(src, n, '')
    return n


def build(m):
    L.set_material_usage(m, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    m.set_editor_property('two_sided', False)
    s = {}
    for name, value in SCALARS.items():
        s[name] = node(m, u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value,
                       group=GROUPS.get(name, 'Finish'))
    v = {}
    for name, value in VECTORS.items():
        v[name] = node(m, u.MaterialExpressionVectorParameter, parameter_name=name,
                       default_value=u.LinearColor(*value, 1), group=GROUPS.get(name, 'Finish'))
    ST = u.MaterialSamplerType
    src = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SourceBaseColor',
               texture=white_tex, sampler_type=ST.SAMPLERTYPE_COLOR, group='Source')
    srough = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SourceRoughness',
                  texture=grey_tex, sampler_type=ST.SAMPLERTYPE_LINEAR_GRAYSCALE, group='Source')
    nrm = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SurfaceNormal',
               texture=flat_normal, sampler_type=ST.SAMPLERTYPE_NORMAL, group='Source')
    msk = node(m, u.MaterialExpressionTextureSampleParameter2D, parameter_name='SurfaceMask',
               texture=mask_tex, sampler_type=ST.SAMPLERTYPE_MASKS, group='Source')
    # Baked masks live on a unique layout: UV1 on meshes whose UV0 tiles, else UV0.
    mask_uv = node(m, u.MaterialExpressionLinearInterpolate)
    wire(node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=0), mask_uv, 'A')
    wire(node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=1), mask_uv, 'B')
    wire(s['MaskUVChannel'], mask_uv, 'Alpha')
    wire(mask_uv, msk, 'UVs')
    grain = node(m, u.MaterialExpressionTextureObjectParameter, parameter_name='GrainTexture',
                 texture=grain_tex, sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR, group='Micro')
    pos = node(m, u.MaterialExpressionVertexInterpolator)
    wire(node(m, u.MaterialExpressionPreSkinnedPosition), pos, 'VS')
    nor = node(m, u.MaterialExpressionVertexInterpolator)
    wire(node(m, u.MaterialExpressionPreSkinnedNormal), nor, 'VS')
    g = custom(m, 'WS_Grain', {'P': pos, 'N': nor, 'Tex': grain, 'TileCm': s['GrainTileCm']}, 4)
    mask_rgba = (msk, 'RGBA')
    wear = custom(m, 'WS_Wear', {'Mask': mask_rgba, 'Grain': g, 'EdgeWear': s['EdgeWear'],
                                 'EdgeBreakup': s['EdgeBreakup'], 'EdgeContrast': s['EdgeContrast'],
                                 'ScratchAmount': s['ScratchAmount']}, 4)
    cr = custom(m, 'WS_ColorRough', {
        'Src': (src, 'RGB'), 'SrcR': (srough, 'R'), 'Mask': mask_rgba, 'Grain': g, 'Wear': wear,
        'Finish': (v['FinishColor'], 'RGB'), 'SrcW': s['SourceColorWeight'], 'Rough': s['Roughness'],
        'SrcRW': s['SourceRoughnessWeight'], 'Pivot': s['SourceRoughnessPivot'],
        'GrainR': s['GrainRoughness'], 'MottleR': s['MottleRoughness'], 'MottleC': s['MottleColor'],
        'Stipple': s['Stipple'], 'EdgeColor': (v['EdgeColor'], 'RGB'), 'EdgeRough': s['EdgeRoughness'],
        'EdgeHL': s['EdgeHighlight'], 'CavDark': s['CavityDarken'], 'CavRough': s['CavityRoughness'],
        'Handling': s['HandlingPolish']}, 4)
    ma = custom(m, 'WS_MetalAO', {'Metal': s['Metallic'], 'EdgeMetal': s['EdgeMetallic'], 'Wear': wear,
                                  'Mask': mask_rgba, 'AOStrength': s['AOStrength']}, 4)
    uv = node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
    beads = custom(m, 'WS_Beads', {'UV': uv, 'Wet': s['WeaponWetness'], 'Scale': s['BeadScale']}, 4)
    wet = custom(m, 'WS_Wet', {'CR': cr, 'Data': beads}, 4)
    wn = custom(m, 'WS_WetNormal', {'Base': (nrm, 'RGB'), 'Data': beads}, 3)
    output(mask(m, wet, 'rgb'), 'BASE_COLOR')
    output(mask(m, wet, 'a'), 'ROUGHNESS')
    output(mask(m, ma, 'r'), 'METALLIC')
    output(mask(m, ma, 'g'), 'AMBIENT_OCCLUSION')
    output(s['Specular'], 'SPECULAR')
    output(wn, 'NORMAL')
