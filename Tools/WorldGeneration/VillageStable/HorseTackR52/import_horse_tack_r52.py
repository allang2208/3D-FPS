"""Headless UE 5.8 importer for HorseTackR52b:
- 2K weathered PBR textures & 6 SkeletalMesh+StaticMesh fade-synchronized materials (CPD[0] DitherTemporalAA)
- 4 standalone 3-LOD StaticMeshes (SM_Tack_{Horseshoes,Saddle,Barding,Saddlebags}) with box collision
- 4 skinned 3-LOD SkeletalMeshes (SK_Tack_{Horseshoes,Saddle,Barding,Saddlebags}_Mounted) sharing SK_StableWarhorse_Skeleton
- Upgrade M_Warhorse_Coat & M_Warhorse_CoatFade with CPD[1] (HideOriginalTack):
    * Repaints original white chest collar with horse's natural coat pigment (both materials)
    * Clips original white hanging stirrups via exact rest-space region mask (M_Warhorse_CoatFade)
"""
import hashlib
import json
from pathlib import Path
import unreal as ue

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
MANIFEST_PATH = PROJECT / 'SourceAssets/HillsVillageStable/HorseTackR52/model-manifest.json'
TEX_SRC_DIR = PROJECT / 'SourceAssets/HillsVillageStable/HorseTackR52/Textures'
REPORT_OUT = Path('F:/FPSGAMEData/ArtProduction/HillsVillageStable/HorseTackR52-20261126/import_report.json')

TACK_DEST = '/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52'
LOCAL_MATS = TACK_DEST + '/Materials'
LOCAL_TEXS = TACK_DEST + '/Textures'
HORSE_DEST = '/Game/WorldGeneration/TemperateHills/VillageStable/Horses'
APPEARANCE_DIR = HORSE_DEST + '/AppearanceR30'
WARHORSE_SK_PATH = HORSE_DEST + '/SK_StableWarhorse'

ASSETS = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
MAT_EDIT = ue.MaterialEditingLibrary
MESH_SUB = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
SK_SUB = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)

DONOR_MATERIALS = {
    'Brass': '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBrass',
    'WaxedThread': '/Game/Characters/ModularOutfit20260924/BrownLeatherSet20261004/Materials/M_BrownLeather_WaxedThread',
}

DONOR_WEATHER_CFG = {
    'Brass':       dict(dirt=0.56, mud=0.22, edge=0.45, edge_tint=(0.60, 0.46, 0.20), edge_polish=0.26, mud_rough=0.20),
    'WaxedThread': dict(dirt=0.45, mud=0.12, edge=0.14, edge_tint=(0.52, 0.44, 0.30), edge_polish=0.02, mud_rough=0.10),
}


def require(path):
    obj = ue.load_asset(path)
    if obj is None:
        raise RuntimeError(f'Missing required UE asset: {path}')
    return obj


def save(obj):
    if not ASSETS.save_loaded_asset(obj, False):
        raise RuntimeError(f'Failed to save UE asset: {obj.get_path_name()}')


def _sampler_type_for(tex):
    vt = bool(tex.get_editor_property('virtual_texture_streaming'))
    cs = tex.compression_settings
    srgb = bool(tex.srgb)
    if cs == ue.TextureCompressionSettings.TC_NORMALMAP:
        return ue.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if vt else ue.MaterialSamplerType.SAMPLERTYPE_NORMAL
    if cs == ue.TextureCompressionSettings.TC_MASKS:
        return ue.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_MASKS if vt else ue.MaterialSamplerType.SAMPLERTYPE_MASKS
    if cs == ue.TextureCompressionSettings.TC_GRAYSCALE:
        return ue.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_GRAYSCALE if vt else ue.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE
    if cs == ue.TextureCompressionSettings.TC_ALPHA:
        return ue.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_ALPHA if vt else ue.MaterialSamplerType.SAMPLERTYPE_ALPHA
    if not srgb:
        return ue.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_LINEAR_COLOR if vt else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    return ue.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if vt else ue.MaterialSamplerType.SAMPLERTYPE_COLOR


def _import_texture(png_path: Path, dest_dir: str, asset_name: str, kind: str):
    if not png_path.exists():
        raise RuntimeError(f'Missing source texture PNG: {png_path}')
    existing = dest_dir + '/' + asset_name
    if ASSETS.does_asset_exist(existing):
        return require(existing)
    ASSETS.make_directory(dest_dir)
    task = ue.AssetImportTask()
    task.filename = str(png_path)
    task.destination_path = dest_dir
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])

    tex = require(dest_dir + '/' + asset_name)
    tex.modify()
    if kind == 'basecolor':
        tex.srgb = True
        tex.compression_settings = ue.TextureCompressionSettings.TC_DEFAULT
    elif kind == 'normal_dx':
        tex.srgb = False
        tex.compression_settings = ue.TextureCompressionSettings.TC_NORMALMAP
        tex.flip_green_channel = False
    elif kind == 'orm':
        tex.srgb = False
        tex.compression_settings = ue.TextureCompressionSettings.TC_MASKS
    else:
        raise ValueError(f'Unknown texture kind: {kind}')
    tex.address_x = ue.TextureAddress.TA_WRAP
    tex.address_y = ue.TextureAddress.TA_WRAP
    save(tex)
    return tex


def _node(mat, cls, x, y):
    return MAT_EDIT.create_material_expression(mat, cls, int(x), int(y))


def _const(mat, val, x, y):
    c = _node(mat, ue.MaterialExpressionConstant, x, y)
    c.r = float(val)
    return c


def _const3(mat, rgb, x, y):
    c = _node(mat, ue.MaterialExpressionConstant3Vector, x, y)
    c.constant = ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)
    return c


def _connect(src, src_pin, dst, dst_pin):
    ok = MAT_EDIT.connect_material_expressions(src, src_pin, dst, dst_pin)
    if not ok:
        raise RuntimeError(f'Failed connecting {src.get_name()}.{src_pin} -> {dst.get_name()}.{dst_pin}')


def _wire_fade_dither(mat, x0=560, y0=520):
    """Synchronized summon/dismiss/retreat dissolve via CPD[0] ('HorseRetreatFade', default 0.0)."""
    mat.set_editor_property('blend_mode', ue.BlendMode.BLEND_MASKED)
    fade = _node(mat, ue.MaterialExpressionScalarParameter, x0, y0)
    fade.set_editor_property('parameter_name', 'HorseRetreatFade')
    fade.set_editor_property('default_value', 0.0)
    fade.set_editor_property('use_custom_primitive_data', True)
    fade.set_editor_property('primitive_data_index', 0)

    inv = _node(mat, ue.MaterialExpressionOneMinus, x0 + 180, y0)
    inv_in = str(MAT_EDIT.get_material_expression_input_names(inv)[0])
    _connect(fade, '', inv, inv_in)

    dither = _node(mat, ue.MaterialExpressionMaterialFunctionCall, x0 + 340, y0)
    fn = ue.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA')
    if not fn or not dither.set_material_function(fn):
        raise RuntimeError('Failed loading DitherTemporalAA material function')
    d_in = str(MAT_EDIT.get_material_expression_input_names(dither)[0])
    _connect(inv, '', dither, d_in)
    MAT_EDIT.connect_material_property(dither, '', ue.MaterialProperty.MP_OPACITY_MASK)


def _wire_vcol_weathering(mat, bc_node, bc_pin, rough_node, rough_pin, cfg, x0=220, y0=-220):
    vc = _node(mat, ue.MaterialExpressionVertexColor, x0, y0 + 260)

    dirt_amt = _node(mat, ue.MaterialExpressionMultiply, x0 + 180, y0 + 180)
    _connect(vc, 'R', dirt_amt, 'A')
    _connect(_const(mat, cfg['dirt'], x0 + 40, y0 + 180), '', dirt_amt, 'B')

    dirt_dark = _node(mat, ue.MaterialExpressionMultiply, x0 + 180, y0 - 60)
    _connect(bc_node, bc_pin, dirt_dark, 'A')
    _connect(_const3(mat, (0.30, 0.25, 0.20), x0 + 40, y0 - 20), '', dirt_dark, 'B')

    lerp_dirt = _node(mat, ue.MaterialExpressionLinearInterpolate, x0 + 360, y0 - 80)
    _connect(bc_node, bc_pin, lerp_dirt, 'A')
    _connect(dirt_dark, '', lerp_dirt, 'B')
    _connect(dirt_amt, '', lerp_dirt, 'Alpha')

    mud_amt = _node(mat, ue.MaterialExpressionMultiply, x0 + 180, y0 + 280)
    _connect(vc, 'G', mud_amt, 'A')
    _connect(_const(mat, cfg['mud'], x0 + 40, y0 + 280), '', mud_amt, 'B')

    lerp_mud = _node(mat, ue.MaterialExpressionLinearInterpolate, x0 + 540, y0 - 80)
    _connect(lerp_dirt, '', lerp_mud, 'A')
    _connect(_const3(mat, (0.135, 0.105, 0.072), x0 + 380, y0 + 20), '', lerp_mud, 'B')
    _connect(mud_amt, '', lerp_mud, 'Alpha')

    edge_amt = _node(mat, ue.MaterialExpressionMultiply, x0 + 180, y0 + 380)
    _connect(vc, 'B', edge_amt, 'A')
    _connect(_const(mat, cfg['edge'], x0 + 40, y0 + 380), '', edge_amt, 'B')

    lerp_edge = _node(mat, ue.MaterialExpressionLinearInterpolate, x0 + 720, y0 - 80)
    _connect(lerp_mud, '', lerp_edge, 'A')
    _connect(_const3(mat, cfg['edge_tint'], x0 + 560, y0 + 20), '', lerp_edge, 'B')
    _connect(edge_amt, '', lerp_edge, 'Alpha')

    MAT_EDIT.connect_material_property(lerp_edge, '', ue.MaterialProperty.MP_BASE_COLOR)

    if rough_node is not None:
        r_dirt = _node(mat, ue.MaterialExpressionMultiply, x0 + 360, y0 + 200)
        _connect(vc, 'R', r_dirt, 'A')
        _connect(_const(mat, 0.14 * cfg['dirt'], x0 + 220, y0 + 220), '', r_dirt, 'B')

        r_mud = _node(mat, ue.MaterialExpressionMultiply, x0 + 360, y0 + 300)
        _connect(vc, 'G', r_mud, 'A')
        _connect(_const(mat, cfg['mud_rough'], x0 + 220, y0 + 320), '', r_mud, 'B')

        r_polish = _node(mat, ue.MaterialExpressionMultiply, x0 + 360, y0 + 400)
        _connect(vc, 'B', r_polish, 'A')
        _connect(_const(mat, cfg['edge_polish'], x0 + 220, y0 + 420), '', r_polish, 'B')

        r_add1 = _node(mat, ue.MaterialExpressionAdd, x0 + 540, y0 + 200)
        _connect(rough_node, rough_pin, r_add1, 'A')
        _connect(r_dirt, '', r_add1, 'B')

        r_add2 = _node(mat, ue.MaterialExpressionAdd, x0 + 680, y0 + 240)
        _connect(r_add1, '', r_add2, 'A')
        _connect(r_mud, '', r_add2, 'B')

        r_sub = _node(mat, ue.MaterialExpressionSubtract, x0 + 820, y0 + 260)
        _connect(r_add2, '', r_sub, 'A')
        _connect(r_polish, '', r_sub, 'B')

        r_clamp = _node(mat, ue.MaterialExpressionClamp, x0 + 960, y0 + 260)
        clamp_ins = [str(n) for n in MAT_EDIT.get_material_expression_input_names(r_clamp)]
        _connect(r_sub, '', r_clamp, clamp_ins[0])
        _connect(_const(mat, 0.14, x0 + 820, y0 + 360), '', r_clamp, clamp_ins[1])
        _connect(_const(mat, 0.96, x0 + 820, y0 + 420), '', r_clamp, clamp_ins[2])
        MAT_EDIT.connect_material_property(r_clamp, '', ue.MaterialProperty.MP_ROUGHNESS)

    return vc


def _build_authored_pbr_material(mat_name: str, bc_tex, n_tex, orm_tex, tint_rgb,
                                 uv_tile: float, rough_scale: float, rough_bias: float,
                                 cfg: dict, use_orm_metallic=False, spec=0.45):
    ASSETS.make_directory(LOCAL_MATS)
    mat_path = LOCAL_MATS + '/' + mat_name
    existed = ASSETS.does_asset_exist(mat_path)
    mat = (require(mat_path) if existed
           else TOOLS.create_asset(mat_name, LOCAL_MATS, ue.Material, ue.MaterialFactoryNew()))
    mat.modify()
    mat.set_editor_property('two_sided', False)
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    if existed and MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_BASE_COLOR) is not None:
        if MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_OPACITY_MASK) is not None:
            return mat
        _wire_fade_dither(mat, x0=520, y0=600)
        errors = MAT_EDIT.recompile_material(mat)
        if errors:
            raise RuntimeError(f'Material compile error on {mat_path}: {errors}')
        save(mat)
        return mat

    MAT_EDIT.delete_all_material_expressions(mat)

    uv = _node(mat, ue.MaterialExpressionTextureCoordinate, -780, 0)
    uv.u_tiling = float(uv_tile)
    uv.v_tiling = float(uv_tile)

    s_bc = _node(mat, ue.MaterialExpressionTextureSample, -520, -240)
    s_bc.texture = bc_tex
    s_bc.sampler_type = _sampler_type_for(bc_tex)
    _connect(uv, '', s_bc, 'UVs')

    bc_tinted = _node(mat, ue.MaterialExpressionMultiply, -240, -240)
    _connect(s_bc, 'RGB', bc_tinted, 'A')
    _connect(_const3(mat, tint_rgb, -420, -80), '', bc_tinted, 'B')

    s_orm = _node(mat, ue.MaterialExpressionTextureSample, -520, 80)
    s_orm.texture = orm_tex
    s_orm.sampler_type = _sampler_type_for(orm_tex)
    _connect(uv, '', s_orm, 'UVs')

    r_mul = _node(mat, ue.MaterialExpressionMultiply, -240, 100)
    _connect(s_orm, 'G', r_mul, 'A')
    _connect(_const(mat, rough_scale, -380, 200), '', r_mul, 'B')

    r_add = _node(mat, ue.MaterialExpressionAdd, -80, 100)
    _connect(r_mul, '', r_add, 'A')
    _connect(_const(mat, rough_bias, -220, 220), '', r_add, 'B')

    vc = _wire_vcol_weathering(mat, bc_tinted, '', r_add, '', cfg, x0=160, y0=-200)

    s_n = _node(mat, ue.MaterialExpressionTextureSample, -520, 380)
    s_n.texture = n_tex
    s_n.sampler_type = _sampler_type_for(n_tex)
    _connect(uv, '', s_n, 'UVs')
    MAT_EDIT.connect_material_property(s_n, 'RGB', ue.MaterialProperty.MP_NORMAL)

    if use_orm_metallic:
        inv_mud = _node(mat, ue.MaterialExpressionOneMinus, 180, 340)
        mud_m = _node(mat, ue.MaterialExpressionMultiply, 20, 340)
        _connect(vc, 'G', mud_m, 'A')
        _connect(_const(mat, 0.75, -100, 360), '', mud_m, 'B')
        inv_in = str(MAT_EDIT.get_material_expression_input_names(inv_mud)[0])
        _connect(mud_m, '', inv_mud, inv_in)
        met_out = _node(mat, ue.MaterialExpressionMultiply, 340, 340)
        _connect(s_orm, 'B', met_out, 'A')
        _connect(inv_mud, '', met_out, 'B')
        MAT_EDIT.connect_material_property(met_out, '', ue.MaterialProperty.MP_METALLIC)
    else:
        MAT_EDIT.connect_material_property(_const(mat, 0.0, -80, 320), '', ue.MaterialProperty.MP_METALLIC)
    MAT_EDIT.connect_material_property(_const(mat, spec, -80, 400), '', ue.MaterialProperty.MP_SPECULAR)

    inv_dirt = _node(mat, ue.MaterialExpressionOneMinus, 520, 460)
    dirt_ao = _node(mat, ue.MaterialExpressionMultiply, 360, 460)
    _connect(vc, 'R', dirt_ao, 'A')
    _connect(_const(mat, 0.45, 220, 480), '', dirt_ao, 'B')
    inv_in = str(MAT_EDIT.get_material_expression_input_names(inv_dirt)[0])
    _connect(dirt_ao, '', inv_dirt, inv_in)
    ao_comb = _node(mat, ue.MaterialExpressionMultiply, 700, 460)
    _connect(s_orm, 'R', ao_comb, 'A')
    _connect(inv_dirt, '', ao_comb, 'B')
    MAT_EDIT.connect_material_property(ao_comb, '', ue.MaterialProperty.MP_AMBIENT_OCCLUSION)

    _wire_fade_dither(mat, x0=520, y0=600)

    MAT_EDIT.layout_material_expressions(mat)
    errors = MAT_EDIT.recompile_material(mat)
    if errors:
        raise RuntimeError(f'Material compile error on {mat_path}: {errors}')
    save(mat)
    return mat


def _build_weathered_donor_material(slot_name: str, donor_path: str, cfg: dict):
    ASSETS.make_directory(LOCAL_MATS)
    mat_path = LOCAL_MATS + '/M_Tack_' + slot_name
    if ASSETS.does_asset_exist(mat_path):
        mat = require(mat_path)
        if MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_OPACITY_MASK) is not None:
            return mat
        mat.modify()
        MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
        MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
        _wire_fade_dither(mat, x0=640, y0=480)
        errors = MAT_EDIT.recompile_material(mat)
        if errors:
            raise RuntimeError(f'Weathered donor compile error on {mat_path}: {errors}')
        save(mat)
        return mat

    mat = ASSETS.duplicate_asset(donor_path, mat_path)
    if not mat:
        raise RuntimeError(f'Failed duplicating donor Material {donor_path} -> {mat_path}')
    mat.modify()
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    bc_node = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_BASE_COLOR)
    bc_pin = MAT_EDIT.get_material_property_input_node_output_name(mat, ue.MaterialProperty.MP_BASE_COLOR)
    r_node = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_ROUGHNESS)
    r_pin = MAT_EDIT.get_material_property_input_node_output_name(mat, ue.MaterialProperty.MP_ROUGHNESS)
    if bc_node is not None:
        _wire_vcol_weathering(mat, bc_node, bc_pin or '', r_node, r_pin or '', cfg, x0=640, y0=-260)
    _wire_fade_dither(mat, x0=640, y0=480)

    errors = MAT_EDIT.recompile_material(mat)
    if errors:
        raise RuntimeError(f'Weathered donor compile error on {mat_path}: {errors}')
    save(mat)
    return mat


def build_all_tack_materials():
    tex_paths = []
    tex_sets = {}
    for key, prefix in (
        ('TackSteel', 'T_TackSteel'),
        ('TackLeather', 'T_TackLeather'),
        ('TackLeatherDark', 'T_TackLeatherDark'),
        ('TackBlanket', 'T_TackBlanket'),
    ):
        bc = _import_texture(TEX_SRC_DIR / f'{prefix}_BaseColor.png', LOCAL_TEXS, f'{prefix}_BaseColor', 'basecolor')
        n = _import_texture(TEX_SRC_DIR / f'{prefix}_NormalDX.png', LOCAL_TEXS, f'{prefix}_NormalDX', 'normal_dx')
        orm = _import_texture(TEX_SRC_DIR / f'{prefix}_ORM.png', LOCAL_TEXS, f'{prefix}_ORM', 'orm')
        tex_sets[key] = (bc, n, orm)
        tex_paths.extend([bc.get_path_name(), n.get_path_name(), orm.get_path_name()])

    mats = {}
    mats['TackSteel'] = _build_authored_pbr_material(
        'M_TackSteel', *tex_sets['TackSteel'], tint_rgb=(0.95, 0.96, 0.98), uv_tile=1.4,
        rough_scale=0.92, rough_bias=0.00, use_orm_metallic=True, spec=0.55,
        cfg=dict(dirt=0.52, mud=0.45, edge=0.48, edge_tint=(0.56, 0.58, 0.61), edge_polish=0.22, mud_rough=0.26),
    )
    mats['TackLeather'] = _build_authored_pbr_material(
        'M_TackLeather', *tex_sets['TackLeather'], tint_rgb=(0.96, 0.93, 0.90), uv_tile=1.6,
        rough_scale=0.92, rough_bias=0.02, use_orm_metallic=False, spec=0.46,
        cfg=dict(dirt=0.62, mud=0.25, edge=0.42, edge_tint=(0.44, 0.24, 0.12), edge_polish=0.20, mud_rough=0.18),
    )
    mats['TackLeatherDark'] = _build_authored_pbr_material(
        'M_TackLeatherDark', *tex_sets['TackLeatherDark'], tint_rgb=(0.94, 0.91, 0.88), uv_tile=1.8,
        rough_scale=0.90, rough_bias=0.00, use_orm_metallic=False, spec=0.45,
        cfg=dict(dirt=0.58, mud=0.30, edge=0.36, edge_tint=(0.28, 0.16, 0.09), edge_polish=0.18, mud_rough=0.18),
    )
    mats['TackBlanket'] = _build_authored_pbr_material(
        'M_TackBlanket', *tex_sets['TackBlanket'], tint_rgb=(0.98, 0.96, 0.94), uv_tile=1.0,
        rough_scale=1.00, rough_bias=0.02, use_orm_metallic=False, spec=0.28,
        cfg=dict(dirt=0.55, mud=0.22, edge=0.20, edge_tint=(0.40, 0.20, 0.16), edge_polish=0.03, mud_rough=0.12),
    )

    for slot, donor_path in DONOR_MATERIALS.items():
        mats[slot] = _build_weathered_donor_material(slot, donor_path, DONOR_WEATHER_CFG[slot])

    return mats, tex_paths


def upgrade_warhorse_coat_materials():
    """Upgrade M_Warhorse_Coat and M_Warhorse_CoatFade IN-PLACE (zero DeleteAllMaterialExpressions)
       to support CPD[1] ('HideOriginalTack'):
       - Repaints pale white chest collar with horse's natural coat pigment in both materials
       - Clips original white hanging stirrups in M_Warhorse_CoatFade (0% torso hole, 100% stirrup removal)
    """
    collar_hlsl = """
float field=.61*NoiseA+.39*NoiseB;
float pigmentCoverage=smoothstep(Threshold-Softness,Threshold+Softness,field);
float luma=max(.0004,dot(Original,float3(.25,.60,.15)));
float h=Rest.g*2.2;
float f=Rest.b*2.6-1.3;
float tackBox=step(.5,HideTack)*step(-.44,f)*step(f,.78)*step(.82,h)*step(h,1.68)*step(.35,Area);
float tackMask=tackBox*saturate((.94-Area)/.44);
float effLuma=lerp(luma,.044,tackMask*.88);
float3 coat=lerp(Base,Patch,pigmentCoverage)*clamp(pow(effLuma/.042,.55),.26,1.7);
float3 tail=Hair*clamp(pow(luma/.035,.65),.13,2.4);
float coatAlpha=max(saturate((Area-.51)/.49),tackBox);
return lerp(lerp(Original,coat,coatAlpha),tail,saturate((.49-Area)/.49));"""

    stirrup_hlsl = """
float x=Rest.r-.5;
float h=Rest.g*2.2;
float f=Rest.b*2.6-1.3;
float isSide=max(step(.333,x),step(x,-.346));
float isStirrup=step(.5,HideTack)*isSide*step(h,1.32)*step(-.05,f)*step(f,.18);
return 1.-isStirrup;"""

    updated = []
    for name, is_fade in (('M_Warhorse_Coat', False), ('M_Warhorse_CoatFade', True)):
        path = APPEARANCE_DIR + '/' + name
        mat = require(path)

        bc_node = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_BASE_COLOR)
        if bc_node is None or not isinstance(bc_node, ue.MaterialExpressionCustom):
            raise RuntimeError(f'Expected Custom node on {name} MP_BASE_COLOR, got {bc_node}')

        pins = list(bc_node.get_editor_property('inputs'))
        pin_names = [str(p.get_editor_property('input_name')) for p in pins]
        already_upgraded = ('HideTack' in pin_names) and ('Rest' in pin_names)
        op_node_existing = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_OPACITY_MASK) if is_fade else None
        fade_already_wired = (not is_fade) or isinstance(op_node_existing, ue.MaterialExpressionMultiply)

        # If fade stirrup Custom node already exists, check whether its HLSL needs updating
        existing_keep_node = None
        if is_fade and isinstance(op_node_existing, ue.MaterialExpressionMultiply):
            for inp_node in MAT_EDIT.get_inputs_for_material_expression(mat, op_node_existing):
                if isinstance(inp_node, ue.MaterialExpressionCustom):
                    existing_keep_node = inp_node
                    break

        needs_save = False
        if already_upgraded and fade_already_wired:
            if str(bc_node.get_editor_property('code')).strip() != collar_hlsl.strip():
                mat.modify()
                bc_node.set_editor_property('code', collar_hlsl)
                needs_save = True
            if existing_keep_node is not None and str(existing_keep_node.get_editor_property('code')).strip() != stirrup_hlsl.strip():
                if not needs_save:
                    mat.modify()
                existing_keep_node.set_editor_property('code', stirrup_hlsl)
                needs_save = True
            if not needs_save:
                updated.append(mat.get_path_name())
                ue.log(f'WARHORSE_COAT_ALREADY_UPGRADED {name} fade={is_fade}')
                continue
        else:
            mat.modify()
            needs_save = True

        if not already_upgraded:
            region_tex = require(APPEARANCE_DIR + '/T_Warhorse_Regions')
            region_node = _node(mat, ue.MaterialExpressionTextureSample, -420, 420)
            region_node.texture = region_tex
            region_node.set_editor_property('sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)

            hide_tack = _node(mat, ue.MaterialExpressionScalarParameter, -420, 620)
            hide_tack.set_editor_property('parameter_name', 'HideOriginalTack')
            hide_tack.set_editor_property('default_value', 0.0)
            hide_tack.set_editor_property('use_custom_primitive_data', True)
            hide_tack.set_editor_property('primitive_data_index', 1)

            for req_pin in ('Rest', 'HideTack'):
                if req_pin not in pin_names:
                    p = ue.CustomInput()
                    p.set_editor_property('input_name', req_pin)
                    pins.append(p)
            bc_node.set_editor_property('inputs', pins)
            bc_node.set_editor_property('code', collar_hlsl)
            _connect(region_node, 'RGB', bc_node, 'Rest')
            _connect(hide_tack, '', bc_node, 'HideTack')
        else:
            bc_node.set_editor_property('code', collar_hlsl)
            region_node = None
            hide_tack = None

        if is_fade:
            op_node = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_OPACITY_MASK)
            op_pin = MAT_EDIT.get_material_property_input_node_output_name(mat, ue.MaterialProperty.MP_OPACITY_MASK) or ''
            if op_node is None:
                raise RuntimeError(f'Missing MP_OPACITY_MASK input on {name}')
            if not isinstance(op_node, ue.MaterialExpressionMultiply):
                if region_node is None:
                    region_tex = require(APPEARANCE_DIR + '/T_Warhorse_Regions')
                    region_node = _node(mat, ue.MaterialExpressionTextureSample, -420, 420)
                    region_node.texture = region_tex
                    region_node.set_editor_property('sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
                if hide_tack is None:
                    hide_tack = _node(mat, ue.MaterialExpressionScalarParameter, -420, 620)
                    hide_tack.set_editor_property('parameter_name', 'HideOriginalTack')
                    hide_tack.set_editor_property('default_value', 0.0)
                    hide_tack.set_editor_property('use_custom_primitive_data', True)
                    hide_tack.set_editor_property('primitive_data_index', 1)
                keep_stirrup = _node(mat, ue.MaterialExpressionCustom, 140, 560)
                keep_stirrup.set_editor_property('description', 'Hide original white stirrups when 3A saddle equipped')
                keep_stirrup.set_editor_property('output_type', ue.CustomMaterialOutputType.CMOT_FLOAT1)
                kpins = []
                for kname in ('Rest', 'HideTack'):
                    kp = ue.CustomInput()
                    kp.set_editor_property('input_name', kname)
                    kpins.append(kp)
                keep_stirrup.set_editor_property('inputs', kpins)
                keep_stirrup.set_editor_property('code', stirrup_hlsl)
                _connect(region_node, 'RGB', keep_stirrup, 'Rest')
                _connect(hide_tack, '', keep_stirrup, 'HideTack')

                mul = _node(mat, ue.MaterialExpressionMultiply, 380, 500)
                _connect(keep_stirrup, '', mul, 'A')
                _connect(op_node, op_pin, mul, 'B')
                MAT_EDIT.connect_material_property(mul, '', ue.MaterialProperty.MP_OPACITY_MASK)

        errors = MAT_EDIT.recompile_material(mat)
        if errors:
            raise RuntimeError(f'{name} shader compilation failed: {errors}')
        save(mat)
        updated.append(mat.get_path_name())
        ue.log(f'WARHORSE_COAT_UPGRADED {name} fade={is_fade}')
    return updated


def _fresh_import_static_fbx(fbx_path: Path, dest_folder: str, asset_name: str):
    pkg_path = dest_folder + '/' + asset_name
    if ASSETS.does_asset_exist(pkg_path):
        if not ASSETS.delete_asset(pkg_path):
            raise RuntimeError(f'Could not delete old StaticMesh before fresh import: {pkg_path}')

    opts = ue.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    opts.import_as_skeletal = False
    opts.import_mesh = True
    opts.import_materials = False
    opts.import_textures = False
    opts.set_editor_property('reset_to_fbx_on_material_conflict', True)

    data = opts.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = False
    data.transform_vertex_to_absolute = True
    data.bake_pivot_in_vertex = False
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = False
    data.remove_degenerates = True
    data.build_nanite = False
    data.vertex_color_import_option = ue.VertexColorImportOption.REPLACE
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS

    task = ue.AssetImportTask()
    task.filename = str(fbx_path)
    task.destination_path = dest_folder
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = opts
    task.factory = ue.FbxFactory()
    TOOLS.import_asset_tasks([task])

    imported = task.get_objects()
    if len(imported) != 1 or not isinstance(imported[0], ue.StaticMesh):
        raise RuntimeError(f'Expected 1 StaticMesh for {fbx_path}, got {imported}')
    return imported[0]


def _fresh_import_skeletal_fbx(fbx_path: Path, dest_folder: str, asset_name: str, skeleton):
    pkg_path = dest_folder + '/' + asset_name
    if ASSETS.does_asset_exist(pkg_path):
        if not ASSETS.delete_asset(pkg_path):
            raise RuntimeError(f'Could not delete old SkeletalMesh before fresh import: {pkg_path}')

    opts = ue.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_as_skeletal = True
    opts.import_mesh = True
    opts.import_materials = False
    opts.import_textures = False
    opts.import_animations = False
    opts.create_physics_asset = False
    opts.skeleton = skeleton
    opts.set_editor_property('reset_to_fbx_on_material_conflict', True)

    sdata = opts.skeletal_mesh_import_data
    sdata.convert_scene = True
    sdata.convert_scene_unit = True
    sdata.force_front_x_axis = False
    sdata.set_editor_property('use_t0_as_ref_pose', False)
    sdata.set_editor_property('vertex_color_import_option', ue.VertexColorImportOption.REPLACE)
    sdata.set_editor_property('normal_import_method', ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)

    task = ue.AssetImportTask()
    task.filename = str(fbx_path)
    task.destination_path = dest_folder
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = opts
    task.factory = ue.FbxFactory()
    TOOLS.import_asset_tasks([task])

    imported = task.get_objects()
    sk_list = [o for o in imported if isinstance(o, ue.SkeletalMesh)]
    if len(sk_list) != 1:
        raise RuntimeError(f'Expected 1 SkeletalMesh for {fbx_path}, got {imported}')
    return sk_list[0]


def run():
    ASSETS.make_directory(TACK_DEST)
    resolved_mats, imported_textures = build_all_tack_materials()
    upgraded_coats = upgrade_warhorse_coat_materials()

    warhorse_sk = require(WARHORSE_SK_PATH)
    warhorse_skeleton = warhorse_sk.get_editor_property('skeleton')
    if not warhorse_skeleton:
        raise RuntimeError('SK_StableWarhorse missing skeleton')

    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))

    imported_records = []
    for row in manifest['assets']:
        name = row['name']
        kind = row.get('kind', 'static')
        lod0_file = Path(row['lods'][0]['file'])
        src_sha = hashlib.sha256(lod0_file.read_bytes()).hexdigest()

        if kind == 'skeletal_mounted':
            pkg_path = TACK_DEST + '/' + name
            if ASSETS.does_asset_exist(pkg_path):
                existing = ue.load_asset(pkg_path)
                if existing and ASSETS.get_metadata_tag(existing, 'HorseTackR52bSha') == src_sha:
                    ue.log(f'HORSE_TACK_R52B_SKIP_UNCHANGED_SK {name}')
                    continue
            sk = _fresh_import_skeletal_fbx(lod0_file, TACK_DEST, name, warhorse_skeleton)
            slot_bindings = {}
            slots = list(sk.materials)
            for idx, slot in enumerate(slots):
                sname = str(slot.get_editor_property('imported_material_slot_name'))
                if sname not in resolved_mats:
                    sname = str(slot.material_slot_name)
                if sname not in resolved_mats:
                    raise RuntimeError(f'Unknown material slot {sname!r} on {name}')
                slot.material_interface = resolved_mats[sname]
                slot_bindings[sname] = resolved_mats[sname].get_path_name()
            sk.materials = slots

            # Import LOD1 / LOD2 onto SkeletalMesh
            lod_count = 1
            for lod in row['lods'][1:]:
                lvl = int(lod['level'])
                try:
                    ok = SK_SUB.import_lod(sk, lvl, str(lod['file']))
                    if ok:
                        lod_count += 1
                except Exception as exc:
                    ue.log_warning(f'SK_SUB.import_lod warning on {name} LOD{lvl}: {exc}')

            for idx, slot in enumerate(sk.materials):
                if slot.material_interface is None:
                    raise RuntimeError(f'Null material on {name} slot {idx}')

            bb = sk.get_bounds()
            ue_size = [round(float(bb.box_extent.x * 2.0), 2),
                       round(float(bb.box_extent.y * 2.0), 2),
                       round(float(bb.box_extent.z * 2.0), 2)]
            ASSETS.set_metadata_tag(sk, 'HorseTackR52bSha', src_sha)
            save(sk)

            imported_records.append(dict(
                name=name,
                kind='skeletal_mounted',
                package=TACK_DEST + '/' + name,
                skeleton=warhorse_skeleton.get_path_name(),
                lod_count=int(SK_SUB.get_lod_count(sk)) if hasattr(SK_SUB, 'get_lod_count') else lod_count,
                lod_triangles=[int(l['triangles']) for l in row['lods']],
                ue_size_cm=ue_size,
                materials=slot_bindings,
                source_sha256=src_sha,
            ))
            ue.log(f'HORSE_TACK_R52B_IMPORTED_SK {name} lods={lod_count} mats={len(slot_bindings)} size={ue_size}')
        else:
            pkg_path = TACK_DEST + '/' + name
            if ASSETS.does_asset_exist(pkg_path):
                existing = ue.load_asset(pkg_path)
                if existing and ASSETS.get_metadata_tag(existing, 'HorseTackR52bSha') == src_sha:
                    ue.log(f'HORSE_TACK_R52B_SKIP_UNCHANGED_SM {name}')
                    continue
            mesh = _fresh_import_static_fbx(lod0_file, TACK_DEST, name)

            slot_bindings = {}
            for idx, slot in enumerate(mesh.static_materials):
                sname = str(slot.get_editor_property('imported_material_slot_name'))
                if sname not in resolved_mats:
                    sname = str(slot.material_slot_name)
                if sname not in resolved_mats:
                    raise RuntimeError(f'Unknown material slot {sname!r} on {name}')
                mesh.set_material(idx, resolved_mats[sname])
                slot_bindings[sname] = resolved_mats[sname].get_path_name()

            for lod in row['lods'][1:]:
                lvl = int(lod['level'])
                res = MESH_SUB.import_lod(mesh, lvl, str(lod['file']))
                if res != lvl:
                    raise RuntimeError(f'Failed importing LOD{lvl} for {name}: got {res}')
            MESH_SUB.set_lod_screen_sizes(mesh, [1.0, 0.28, 0.09])

            boxes = []
            for col in row.get('colliders', []):
                box = ue.KBoxElem()
                box.set_editor_property('center', ue.Vector(*col['center']))
                box.set_editor_property('rotation', ue.Rotator(yaw=float(col.get('yaw', 0.0))))
                box.set_editor_property('x', float(col['size'][0]))
                box.set_editor_property('y', float(col['size'][1]))
                box.set_editor_property('z', float(col['size'][2]))
                boxes.append(box)
            body = mesh.get_editor_property('body_setup')
            agg = body.get_editor_property('agg_geom')
            agg.set_editor_property('box_elems', boxes)
            body.set_editor_property('agg_geom', agg)
            body.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            if boxes:
                cooked = ue.GeometryScript_Collision.get_simple_collision_from_static_mesh(mesh)
                ue.GeometryScript_Collision.set_simple_collision_of_static_mesh(
                    cooked, mesh, ue.GeometryScriptSetSimpleCollisionOptions()
                )

            for idx, slot in enumerate(mesh.static_materials):
                if slot.material_interface is None:
                    raise RuntimeError(f'Null material on {name} slot {idx}')

            bb = mesh.get_bounding_box()
            ue_size = [round(float(bb.max.x - bb.min.x), 2),
                       round(float(bb.max.y - bb.min.y), 2),
                       round(float(bb.max.z - bb.min.z), 2)]
            expected = row['size_cm']
            for ax, (got, exp) in enumerate(zip(ue_size, expected)):
                if abs(got - exp) > 2.5:
                    raise RuntimeError(f'Size mismatch on {name} axis {ax}: got {got} cm vs expected {exp} cm')

            ASSETS.set_metadata_tag(mesh, 'HorseTackR52bSha', src_sha)
            save(mesh)

            imported_records.append(dict(
                name=name,
                kind='static_standalone',
                package=TACK_DEST + '/' + name,
                lod_count=int(MESH_SUB.get_lod_count(mesh)),
                lod_triangles=[int(l['triangles']) for l in row['lods']],
                ue_bounds_min_cm=[round(float(bb.min.x), 2), round(float(bb.min.y), 2), round(float(bb.min.z), 2)],
                ue_bounds_max_cm=[round(float(bb.max.x), 2), round(float(bb.max.y), 2), round(float(bb.max.z), 2)],
                ue_size_cm=ue_size,
                collision_boxes=len(boxes),
                materials=slot_bindings,
                source_sha256=src_sha,
            ))
            ue.log(f'HORSE_TACK_R52B_IMPORTED_SM {name} lods={MESH_SUB.get_lod_count(mesh)} mats={len(slot_bindings)} size={ue_size}')

    if imported_records:
        report = dict(
            revision='HorseTackR52b',
            package_root=TACK_DEST,
            upgraded_warhorse_coats=upgraded_coats,
            textures=imported_textures,
            materials={k: v.get_path_name() for k, v in resolved_mats.items()},
            meshes=imported_records,
        )
        REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
        REPORT_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log(f'HORSE_TACK_R52B_IMPORT_DONE count={len(imported_records)} report={REPORT_OUT}')


if __name__ == '__main__':
    run()
