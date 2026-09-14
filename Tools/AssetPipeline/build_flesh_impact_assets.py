"""Create the accepted instanced blood mist/drop materials.

Reuses local Realistic Starter VFX Pack Vol 2 textures without modifying them.
Run with UE Python commandlet and D3D12 for necessary material compilation.
Does not launch gameplay or perform acceptance/performance tests.
"""
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/FleshImpacts20260914'
DEST = '/Game/Weapons/GunplayFX/Impacts/Blood'
PACK = '/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/'
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SOURCE.mkdir(parents=True, exist_ok=True)


def node(mat, cls, **props):
    expr = LIB.create_material_expression(mat, cls)
    for key, value in props.items():
        expr.set_editor_property(key, value)
    return expr


def wire(src, dst, pin, output=''):
    if isinstance(pin, int):
        pin = str(LIB.get_material_expression_input_names(dst)[pin])
    if not LIB.connect_material_expressions(src, output, dst, pin):
        raise RuntimeError('Cannot connect ' + pin)


def output(src, prop):
    if not LIB.connect_material_property(src, '', prop):
        raise RuntimeError('Cannot connect material property ' + str(prop))


def constant(mat, value):
    return node(mat, unreal.MaterialExpressionConstant, r=value)


def multiply(mat, a, b):
    expr = node(mat, unreal.MaterialExpressionMultiply)
    wire(a, expr, 'A'); wire(b, expr, 'B')
    return expr


def custom(mat, code, inputs):
    expr = node(mat, unreal.MaterialExpressionCustom, code=code,
                output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in inputs:
        pin = unreal.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    expr.set_editor_property('inputs', pins)
    for name, src in inputs.items():
        wire(src, expr, name)
    return expr


def instance_value(mat, index, default):
    value = node(mat, unreal.MaterialExpressionPerInstanceCustomData, data_index=index, const_default_value=default)
    interp = node(mat, unreal.MaterialExpressionVertexInterpolator)
    wire(value, interp, 0)
    return interp


def texture(mat, name):
    tex = unreal.load_asset(PACK + name)
    if not tex:
        raise RuntimeError('Acquire/import the local source pack first: ' + PACK + name)
    return node(mat, unreal.MaterialExpressionTextureObject, texture=tex)


def material(name):
    if unreal.EditorAssetLibrary.does_asset_exist(DEST + '/' + name):
        return None  # Versioned, project-owned assets; preserve subsequent tuning.
    return TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())


def save(mat):
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError('\n'.join(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat, False):
        raise RuntimeError('Cannot save ' + mat.get_path_name())
    unreal.log('FLESH_IMPACT_ASSET_SAVED ' + mat.get_path_name())


# T_Smoke_Wisp is an 8x8 RGBA flipbook. Alpha (not its pale RGB) is density.
# Interpolate adjacent frames within each cell, with padding against atlas bleed.
mist_code = r'''
float frame = 2.0 + saturate(Age) * 25.0 + Variation * 3.0;
float i0 = floor(frame), i1 = i0 + 1.0;
float2 inset = clamp(UV, 0.016, 0.984);
float2 a = (float2(fmod(i0,8.0),floor(i0/8.0)) + inset) / 8.0;
float2 b = (float2(fmod(i1,8.0),floor(i1/8.0)) + inset) / 8.0;
float density = lerp(Texture2DSample(Wisp,WispSampler,a).a,
                     Texture2DSample(Wisp,WispSampler,b).a,frac(frame));
float2 p = (UV-.5)*2;
float edge = 1.0-smoothstep(.60,1.0,length(p));
return saturate(density*3.4)*edge;
'''

# T_Droplets_A packs six shapes in 3 columns x 2 rows. Blue is the silhouette;
# RGB as a color would produce blue/pink blobs, and its absent alpha is opaque.
drop_code = r'''
float index = min(5.0,floor(Variation*6.0));
float2 cell = float2(fmod(index,3.0),floor(index/3.0));
float2 coord = (cell+clamp(UV,.015,.985))/float2(3.0,2.0);
float mask = Texture2DSample(Drops,DropsSampler,coord).b;
float2 edge = smoothstep(0.0,.075,UV)*smoothstep(0.0,.075,1.0-UV);
return smoothstep(.035,.70,mask)*edge.x*edge.y;
'''

for kind, code in (('Mist', mist_code), ('Droplet', drop_code)):
    (SOURCE / (kind + 'Mask.hlsl')).write_text(code.strip() + '\n', encoding='utf-8')
    mat = material('M_Flesh' + kind + 'V1')
    if not mat:
        continue
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided', True)
    LIB.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    rgb = node(mat, unreal.MaterialExpressionPerInstanceCustomData3Vector, data_index=0,
               const_default_value=unreal.LinearColor(.32,.009,.006,1))
    color = node(mat, unreal.MaterialExpressionVertexInterpolator)
    wire(rgb, color, 0)
    alpha = instance_value(mat,3,.7)
    age = instance_value(mat,4,.1)
    variation = instance_value(mat,5,.3)
    uv = node(mat, unreal.MaterialExpressionTextureCoordinate)
    inputs = {'UV': uv, 'Variation': variation}
    if kind == 'Mist':
        inputs.update(Age=age, Wisp=texture(mat,'T_Smoke_Wisp'))
    else:
        inputs.update(Drops=texture(mat,'T_Droplets_A'))
    mask = custom(mat,code,inputs)
    fade = node(mat,unreal.MaterialExpressionDepthFade,fade_distance_default=1.5 if kind=='Mist' else .35)
    wire(multiply(mat,mask,alpha),fade,'Opacity')
    output(fade,unreal.MaterialProperty.MP_OPACITY)
    output(color,unreal.MaterialProperty.MP_BASE_COLOR)
    output(multiply(mat,color,constant(mat,.025)),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output(constant(mat,.9 if kind=='Mist' else .42),unreal.MaterialProperty.MP_ROUGHNESS)
    output(constant(mat,.12 if kind=='Mist' else .25),unreal.MaterialProperty.MP_SPECULAR)
    save(mat)

# Ground blood is authored by build_flesh_ground_v2.py. The retired V1 stain
# and its shader are archived; this current entry never recreates that asset.

(SOURCE/'CREDITS.md').write_text('''# Flesh impact assets

Project-authored shaders in this folder; runtime materials in /Game/Weapons/GunplayFX/Impacts/Blood.
Texture dependencies: /Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Smoke_Wisp (8x8, alpha density)
and T_Droplets_A (3x2, blue silhouette). Existing imported source pack is unchanged.

Source: Realistic Starter VFX Pack Vol 2
https://www.fab.com/listings/ac2818b3-7d35-4cf5-a1af-cbf8ff5c61c1
Local Fab Library records previously identified this listing as acquired.
Keep the account's acquisition/license records; project use does not grant standalone
redistribution of the pack, exported source textures, or texture-bearing assets.
No purchase or new Fab download was performed for this implementation.

The source P_Blood_Splat_Cone is Cascade; it is not spawned per hit here. T_Splat's ring-like
mask and the pale RGB of transparent atlases are not used as blood color/opacity.
Small instanced cards and shared decal materials use the existing project's hard budgets.
Recreate mist/drops with Tools/AssetPipeline/build_flesh_impact_assets.py after restoring the pack.
Then run Tools/AssetPipeline/build_flesh_ground_v2.py for the accepted ground stain.
Only asset authoring/material compilation and necessary native build are part of this delivery;
in-game appearance and performance remain for the user to test.
''',encoding='utf-8')
unreal.log('FLESH_IMPACT_ASSETS_CREATED gameplay_not_run')
