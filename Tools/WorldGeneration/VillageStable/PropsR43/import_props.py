"""Headless UE 5.8 importer for StablePropsR44: 2K weathered PBR textures, VertexColor-weathered ISM materials, 3-LOD FBXs & MI_StableSign."""
import hashlib
import json
from pathlib import Path
import unreal as ue

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
MANIFEST_PATH = PROJECT / 'SourceAssets/HillsVillageStable/PropsR43/model-manifest.json'
TEX_SRC_DIR = PROJECT / 'SourceAssets/HillsVillageStable/PropsR43/Textures'
SIGN_PNG = PROJECT / 'SourceAssets/HillsVillageTradeSigns/T_StableSign_Color.png'

PROPS_DEST = '/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43'
LOCAL_MATS = PROPS_DEST + '/Materials'
LOCAL_TEXS = PROPS_DEST + '/Textures'
TRADE_ROOT = '/Game/WorldGeneration/TemperateHills/VillageTradeSigns'

ASSETS = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
MAT_EDIT = ue.MaterialEditingLibrary
MESH_SUB = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)

# Scanned donor leather maps verified in project Content (GunWorkbenchMedieval20260928)
GWM_LEATHER_DIR = '/Game/Building/GunWorkbenchMedieval20260928/Textures'

# Existing verified scanned/authored project donor materials reused & enhanced with 3D VertexColor weathering
DONOR_MATERIALS = {
    'Oak': '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak',
    'OiledOak': '/Game/WorldGeneration/VillageTavern/Furniture/M_TavernOiledOak',
    'DarkWood': '/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelTimber',
    'Sawn': '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSawn',
    'Endgrain': '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterCut',
    'Lime': '/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelLimewash',
    'Stone': '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_HearthStone',
    'ScaleIron': '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_SmithScaleIron',
    'Iron': '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron',
    'Steel': '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterSteel',
    'Brass': '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterBrass',
    'WaxedThread': '/Game/Characters/ModularOutfit20260924/BrownLeatherSet20261004/Materials/M_BrownLeather_WaxedThread',
    'Linen': '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Linen',
    'Hay': '/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Materials/MI_MillHay',
}

# Per-material-class physical use-wear & weathering calibration driven by Blender VertexColor:
#   R = 3D concavity/crevice dirt & underside grime
#   G = ground mud splash & lower dampness
#   B = convex edge scuff / wear / hand-rub burnish
DONOR_WEATHER_CFG = {
    'Oak':         dict(dirt=0.62, mud=0.58, edge=0.28, edge_tint=(0.30, 0.22, 0.14), edge_polish=0.06, mud_rough=0.18),
    'OiledOak':    dict(dirt=0.58, mud=0.52, edge=0.30, edge_tint=(0.28, 0.20, 0.12), edge_polish=0.10, mud_rough=0.18),
    'DarkWood':    dict(dirt=0.55, mud=0.62, edge=0.32, edge_tint=(0.24, 0.17, 0.11), edge_polish=0.08, mud_rough=0.20),
    'Sawn':        dict(dirt=0.60, mud=0.45, edge=0.26, edge_tint=(0.36, 0.27, 0.18), edge_polish=0.05, mud_rough=0.16),
    'Endgrain':    dict(dirt=0.65, mud=0.50, edge=0.22, edge_tint=(0.30, 0.22, 0.14), edge_polish=0.04, mud_rough=0.16),
    'Lime':        dict(dirt=0.68, mud=0.42, edge=0.25, edge_tint=(0.48, 0.43, 0.36), edge_polish=0.04, mud_rough=0.15),
    'Stone':       dict(dirt=0.62, mud=0.68, edge=0.24, edge_tint=(0.34, 0.32, 0.29), edge_polish=0.04, mud_rough=0.18),
    'ScaleIron':   dict(dirt=0.58, mud=0.65, edge=0.38, edge_tint=(0.26, 0.27, 0.29), edge_polish=0.18, mud_rough=0.26),
    'Iron':        dict(dirt=0.55, mud=0.55, edge=0.40, edge_tint=(0.32, 0.33, 0.35), edge_polish=0.22, mud_rough=0.24),
    'Steel':       dict(dirt=0.48, mud=0.45, edge=0.36, edge_tint=(0.44, 0.45, 0.47), edge_polish=0.22, mud_rough=0.22),
    'Brass':       dict(dirt=0.60, mud=0.30, edge=0.42, edge_tint=(0.56, 0.42, 0.18), edge_polish=0.24, mud_rough=0.22),
    'WaxedThread': dict(dirt=0.50, mud=0.15, edge=0.15, edge_tint=(0.45, 0.38, 0.26), edge_polish=0.02, mud_rough=0.10),
    'Linen':       dict(dirt=0.58, mud=0.25, edge=0.22, edge_tint=(0.38, 0.33, 0.26), edge_polish=0.03, mud_rough=0.12),
    'Hay':         dict(dirt=0.55, mud=0.35, edge=0.24, edge_tint=(0.38, 0.30, 0.15), edge_polish=0.02, mud_rough=0.12),
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
    """Return exact UE5 MaterialSamplerType matching texture compression, sRGB & virtual-texture streaming."""
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
    """Import a PNG texture with exact PBR compression, sRGB & DX normal orientation."""
    if not png_path.exists():
        raise RuntimeError(f'Missing source texture PNG: {png_path}')
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


def _wire_vcol_weathering(mat, bc_node, bc_pin, rough_node, rough_pin, cfg, x0=220, y0=-220):
    """Splice 3D baked VertexColor weathering (R=crevice grime, G=ground mud, B=edge scuff/burnish) onto BaseColor & Roughness."""
    vc = _node(mat, ue.MaterialExpressionVertexColor, x0, y0 + 260)

    # 1. Crevice & underside oil/dirt darkening (R channel)
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

    # 2. Ground mud-splash & damp soil grime (G channel)
    mud_amt = _node(mat, ue.MaterialExpressionMultiply, x0 + 180, y0 + 280)
    _connect(vc, 'G', mud_amt, 'A')
    _connect(_const(mat, cfg['mud'], x0 + 40, y0 + 280), '', mud_amt, 'B')

    lerp_mud = _node(mat, ue.MaterialExpressionLinearInterpolate, x0 + 540, y0 - 80)
    _connect(lerp_dirt, '', lerp_mud, 'A')
    _connect(_const3(mat, (0.135, 0.105, 0.072), x0 + 380, y0 + 20), '', lerp_mud, 'B')
    _connect(mud_amt, '', lerp_mud, 'Alpha')

    # 3. Convex edge scuff & high-touch burnish (B channel)
    edge_amt = _node(mat, ue.MaterialExpressionMultiply, x0 + 180, y0 + 380)
    _connect(vc, 'B', edge_amt, 'A')
    _connect(_const(mat, cfg['edge'], x0 + 40, y0 + 380), '', edge_amt, 'B')

    lerp_edge = _node(mat, ue.MaterialExpressionLinearInterpolate, x0 + 720, y0 - 80)
    _connect(lerp_mud, '', lerp_edge, 'A')
    _connect(_const3(mat, cfg['edge_tint'], x0 + 560, y0 + 20), '', lerp_edge, 'B')
    _connect(edge_amt, '', lerp_edge, 'Alpha')

    MAT_EDIT.connect_material_property(lerp_edge, '', ue.MaterialProperty.MP_BASE_COLOR)

    # 4. Roughness wear response: grime/mud roughens surface, high-touch convex edges subtly burnish/polish
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
        _connect(_const(mat, 0.16, x0 + 820, y0 + 360), '', r_clamp, clamp_ins[1])
        _connect(_const(mat, 0.96, x0 + 820, y0 + 420), '', r_clamp, clamp_ins[2])
        MAT_EDIT.connect_material_property(r_clamp, '', ue.MaterialProperty.MP_ROUGHNESS)

    return vc


def _build_authored_pbr_material(mat_name: str, bc_tex, n_tex, r_tex, is_orm: bool, tint_rgb,
                                 uv_tile: float, rough_scale: float, rough_bias: float, cfg: dict, spec=0.45):
    """Build a crisp ISM-ready PBR material with scanned/authored 2K maps + 3D VertexColor weathering."""
    ASSETS.make_directory(LOCAL_MATS)
    mat_path = LOCAL_MATS + '/' + mat_name
    mat = (require(mat_path) if ASSETS.does_asset_exist(mat_path)
           else TOOLS.create_asset(mat_name, LOCAL_MATS, ue.Material, ue.MaterialFactoryNew()))
    mat.modify()
    MAT_EDIT.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', False)
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_NANITE, True)

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

    s_r = _node(mat, ue.MaterialExpressionTextureSample, -520, 80)
    s_r.texture = r_tex
    s_r.sampler_type = _sampler_type_for(r_tex)
    _connect(uv, '', s_r, 'UVs')

    r_pin = 'G' if is_orm else 'R'
    r_mul = _node(mat, ue.MaterialExpressionMultiply, -240, 100)
    _connect(s_r, r_pin, r_mul, 'A')
    _connect(_const(mat, rough_scale, -380, 200), '', r_mul, 'B')

    r_add = _node(mat, ue.MaterialExpressionAdd, -80, 100)
    _connect(r_mul, '', r_add, 'A')
    _connect(_const(mat, rough_bias, -220, 220), '', r_add, 'B')

    vc = _wire_vcol_weathering(mat, bc_tinted, '', r_add, '', cfg, x0=160, y0=-200)

    # Normal map
    s_n = _node(mat, ue.MaterialExpressionTextureSample, -520, 380)
    s_n.texture = n_tex
    s_n.sampler_type = _sampler_type_for(n_tex)
    _connect(uv, '', s_n, 'UVs')
    MAT_EDIT.connect_material_property(s_n, 'RGB', ue.MaterialProperty.MP_NORMAL)

    # Specular & Metallic
    MAT_EDIT.connect_material_property(_const(mat, 0.0, -80, 320), '', ue.MaterialProperty.MP_METALLIC)
    MAT_EDIT.connect_material_property(_const(mat, spec, -80, 400), '', ue.MaterialProperty.MP_SPECULAR)

    # Ambient Occlusion combining ORM.R (when present) with VertexColor crevice occlusion
    inv_dirt = _node(mat, ue.MaterialExpressionOneMinus, 520, 460)
    dirt_ao = _node(mat, ue.MaterialExpressionMultiply, 360, 460)
    _connect(vc, 'R', dirt_ao, 'A')
    _connect(_const(mat, 0.45, 220, 480), '', dirt_ao, 'B')
    inv_in = str(MAT_EDIT.get_material_expression_input_names(inv_dirt)[0])
    _connect(dirt_ao, '', inv_dirt, inv_in)
    if is_orm:
        ao_comb = _node(mat, ue.MaterialExpressionMultiply, 700, 460)
        _connect(s_r, 'R', ao_comb, 'A')
        _connect(inv_dirt, '', ao_comb, 'B')
        MAT_EDIT.connect_material_property(ao_comb, '', ue.MaterialProperty.MP_AMBIENT_OCCLUSION)
    else:
        MAT_EDIT.connect_material_property(inv_dirt, '', ue.MaterialProperty.MP_AMBIENT_OCCLUSION)

    MAT_EDIT.layout_material_expressions(mat)
    errors = MAT_EDIT.recompile_material(mat)
    if errors:
        raise RuntimeError(f'Material compile error on {mat_path}: {errors}')
    save(mat)
    return mat


def _build_weathered_donor_material(slot_name: str, donor_path: str, cfg: dict):
    """Duplicate project donor material locally, enable ISM, and splice 3D VertexColor weathering cleanly."""
    ASSETS.make_directory(LOCAL_MATS)
    orig = require(donor_path)

    if isinstance(orig, ue.MaterialInstanceConstant):
        parent = orig.get_editor_property('parent')
        parent_path = parent.get_path_name().split('.')[0]
        weathered_parent = _build_weathered_donor_material(slot_name + '_Parent', parent_path, cfg)
        mi_path = LOCAL_MATS + '/MI_StableR44_' + slot_name
        if ASSETS.does_asset_exist(mi_path):
            ASSETS.delete_asset(mi_path)
        mi = ASSETS.duplicate_asset(donor_path, mi_path)
        if not mi:
            raise RuntimeError(f'Failed duplicating donor MI {donor_path} -> {mi_path}')
        mi.modify()
        MAT_EDIT.set_material_instance_parent(mi, weathered_parent)
        MAT_EDIT.update_material_instance(mi)
        save(mi)
        return mi

    mat_path = LOCAL_MATS + '/M_StableR44_' + slot_name
    if ASSETS.does_asset_exist(mat_path):
        ASSETS.delete_asset(mat_path)
    mat = ASSETS.duplicate_asset(donor_path, mat_path)
    if not mat:
        raise RuntimeError(f'Failed duplicating donor Material {donor_path} -> {mat_path}')
    mat.modify()
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    MAT_EDIT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_NANITE, True)

    bc_node = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_BASE_COLOR)
    bc_pin = MAT_EDIT.get_material_property_input_node_output_name(mat, ue.MaterialProperty.MP_BASE_COLOR)
    r_node = MAT_EDIT.get_material_property_input_node(mat, ue.MaterialProperty.MP_ROUGHNESS)
    r_pin = MAT_EDIT.get_material_property_input_node_output_name(mat, ue.MaterialProperty.MP_ROUGHNESS)
    if bc_node is not None:
        _wire_vcol_weathering(mat, bc_node, bc_pin or '', r_node, r_pin or '', cfg, x0=640, y0=-260)

    errors = MAT_EDIT.recompile_material(mat)
    if errors:
        raise RuntimeError(f'Weathered donor compile error on {mat_path}: {errors}')
    save(mat)
    return mat


def build_all_weathered_materials():
    """Import new 2K rope & blanket maps, author 4 signature weathered materials & upgrade all 14 reused donor slots."""
    rope_bc = _import_texture(TEX_SRC_DIR / 'T_StableRope_BaseColor.png', LOCAL_TEXS, 'T_StableRope_BaseColor', 'basecolor')
    rope_n = _import_texture(TEX_SRC_DIR / 'T_StableRope_NormalDX.png', LOCAL_TEXS, 'T_StableRope_NormalDX', 'normal_dx')
    rope_orm = _import_texture(TEX_SRC_DIR / 'T_StableRope_ORM.png', LOCAL_TEXS, 'T_StableRope_ORM', 'orm')

    bl_bc = _import_texture(TEX_SRC_DIR / 'T_StableBlanket_BaseColor.png', LOCAL_TEXS, 'T_StableBlanket_BaseColor', 'basecolor')
    bl_n = _import_texture(TEX_SRC_DIR / 'T_StableBlanket_NormalDX.png', LOCAL_TEXS, 'T_StableBlanket_NormalDX', 'normal_dx')
    bl_orm = _import_texture(TEX_SRC_DIR / 'T_StableBlanket_ORM.png', LOCAL_TEXS, 'T_StableBlanket_ORM', 'orm')

    gwm_bc = require(GWM_LEATHER_DIR + '/T_GWM_leather_basecolor')
    gwm_n = require(GWM_LEATHER_DIR + '/T_GWM_leather_normal')
    gwm_r = require(GWM_LEATHER_DIR + '/T_GWM_leather_rough')

    mats = {}
    mats['Rope'] = _build_authored_pbr_material(
        'M_StableWeatheredRope', rope_bc, rope_n, rope_orm, is_orm=True,
        tint_rgb=(0.94, 0.90, 0.84), uv_tile=1.0, rough_scale=1.0, rough_bias=0.02,
        cfg=dict(dirt=0.68, mud=0.45, edge=0.30, edge_tint=(0.36, 0.28, 0.17), edge_polish=0.04, mud_rough=0.14),
        spec=0.35,
    )
    mats['Blanket'] = _build_authored_pbr_material(
        'M_StableWoolBlanket', bl_bc, bl_n, bl_orm, is_orm=True,
        tint_rgb=(0.96, 0.94, 0.91), uv_tile=1.0, rough_scale=1.0, rough_bias=0.02,
        cfg=dict(dirt=0.62, mud=0.22, edge=0.24, edge_tint=(0.33, 0.27, 0.21), edge_polish=0.03, mud_rough=0.12),
        spec=0.30,
    )
    mats['LeatherMain'] = _build_authored_pbr_material(
        'M_StableSaddleLeather', gwm_bc, gwm_n, gwm_r, is_orm=False,
        tint_rgb=(0.56, 0.30, 0.14), uv_tile=2.2, rough_scale=0.86, rough_bias=0.02,
        cfg=dict(dirt=0.72, mud=0.22, edge=0.42, edge_tint=(0.46, 0.27, 0.14), edge_polish=0.22, mud_rough=0.18),
        spec=0.48,
    )
    mats['LeatherDark'] = _build_authored_pbr_material(
        'M_StableHarnessLeather', gwm_bc, gwm_n, gwm_r, is_orm=False,
        tint_rgb=(0.24, 0.13, 0.075), uv_tile=2.8, rough_scale=0.82, rough_bias=0.00,
        cfg=dict(dirt=0.65, mud=0.28, edge=0.38, edge_tint=(0.30, 0.17, 0.10), edge_polish=0.20, mud_rough=0.18),
        spec=0.46,
    )

    for slot, donor_path in DONOR_MATERIALS.items():
        mats[slot] = _build_weathered_donor_material(slot, donor_path, DONOR_WEATHER_CFG[slot])

    textures = [
        rope_bc.get_path_name(), rope_n.get_path_name(), rope_orm.get_path_name(),
        bl_bc.get_path_name(), bl_n.get_path_name(), bl_orm.get_path_name(),
    ]
    return mats, textures


def import_stable_sign():
    """Import T_StableSign_Color and create/update MI_StableSign inheriting M_TradeSignOak."""
    parent = require(TRADE_ROOT + '/M_TradeSignOak')
    ref_tex = require('/Game/WorldGeneration/TemperateHills/VillageTradeSigns/T_TavernSign_Color')
    vt_flag = bool(ref_tex.get_editor_property('virtual_texture_streaming'))

    tex_name = 'T_StableSign_Color'
    tex_path = TRADE_ROOT + '/' + tex_name
    task = ue.AssetImportTask()
    task.filename = str(SIGN_PNG)
    task.destination_path = TRADE_ROOT
    task.destination_name = tex_name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])

    tex = require(tex_path)
    tex.modify()
    tex.srgb = True
    tex.compression_settings = ue.TextureCompressionSettings.TC_DEFAULT
    if bool(tex.get_editor_property('virtual_texture_streaming')) != vt_flag:
        tex.set_editor_property('virtual_texture_streaming', vt_flag)
    tex.address_x = ue.TextureAddress.TA_CLAMP
    tex.address_y = ue.TextureAddress.TA_CLAMP
    save(tex)

    mi_name = 'MI_StableSign'
    mi_path = TRADE_ROOT + '/' + mi_name
    mi = (require(mi_path) if ASSETS.does_asset_exist(mi_path)
          else TOOLS.create_asset(mi_name, TRADE_ROOT, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew()))
    mi.modify()
    MAT_EDIT.set_material_instance_parent(mi, parent)
    MAT_EDIT.set_material_instance_texture_parameter_value(mi, 'PaintedFace', tex)
    MAT_EDIT.update_material_instance(mi)
    bound = MAT_EDIT.get_material_instance_texture_parameter_value(mi, 'PaintedFace')
    if bound != tex:
        raise RuntimeError(f'MI_StableSign PaintedFace readback mismatch: {bound}')
    save(mi)
    return dict(
        texture=tex.get_path_name(),
        material=mi.get_path_name(),
        parent=parent.get_path_name(),
        virtual_texture=vt_flag,
    )


def _fresh_import_fbx(fbx_path: Path, dest_folder: str, asset_name: str):
    """Fresh StaticMesh import preserving Blender linear vertex colors (REPLACE) & exact cm scale."""
    pkg_path = dest_folder + '/' + asset_name
    if ASSETS.does_asset_exist(pkg_path):
        if not ASSETS.delete_asset(pkg_path):
            raise RuntimeError(f'Could not delete old mesh before fresh import: {pkg_path}')

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


def import_all_props():
    ASSETS.make_directory(PROPS_DEST)
    sign_report = import_stable_sign()
    resolved_mats, imported_textures = build_all_weathered_materials()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    shadow_recipe = Path(__file__).resolve().parents[2] / 'ForestVillage' / 'shadow_geometry.json'
    nanite_props = set(json.loads(shadow_recipe.read_text(encoding='utf-8'))['meshes'])

    imported_records = []
    for row in manifest['assets']:
        name = row['name']
        lod0_file = Path(row['lods'][0]['file'])
        mesh = _fresh_import_fbx(lod0_file, PROPS_DEST, name)

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
        MESH_SUB.set_lod_screen_sizes(mesh, [1.0, 0.25, 0.08])

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
        if mesh.get_path_name().split('.')[0] in nanite_props:
            if not ue.ForestVillageRegion.build_scenery_nanite_mesh(mesh,None):
                raise RuntimeError('Failed to build Nanite geometry for '+name)
        bb = mesh.get_bounding_box()
        ue_size = [round(float(bb.max.x - bb.min.x), 2),
                   round(float(bb.max.y - bb.min.y), 2),
                   round(float(bb.max.z - bb.min.z), 2)]
        expected = row['size_cm']
        for ax, (got, exp) in enumerate(zip(ue_size, expected)):
            if abs(got - exp) > 2.0:
                raise RuntimeError(f'Size mismatch on {name} axis {ax}: got {got} cm vs expected {exp} cm')

        src_sha = hashlib.sha256(lod0_file.read_bytes()).hexdigest()
        ASSETS.set_metadata_tag(mesh, 'StablePropsR44Sha', src_sha)
        save(mesh)

        imported_records.append(dict(
            name=name,
            package=PROPS_DEST + '/' + name,
            lod_count=int(MESH_SUB.get_lod_count(mesh)),
            lod_triangles=[int(l['triangles']) for l in row['lods']],
            ue_bounds_min_cm=[round(float(bb.min.x), 2), round(float(bb.min.y), 2), round(float(bb.min.z), 2)],
            ue_bounds_max_cm=[round(float(bb.max.x), 2), round(float(bb.max.y), 2), round(float(bb.max.z), 2)],
            ue_size_cm=ue_size,
            collision_boxes=len(boxes),
            materials=slot_bindings,
            source_sha256=src_sha,
        ))
        ue.log(f'PROPS_R44_IMPORTED {name} lods={MESH_SUB.get_lod_count(mesh)} size={ue_size}')

    return dict(
        trade_sign=sign_report,
        textures=imported_textures,
        weathered_materials={k: v.get_path_name() for k, v in resolved_mats.items()},
        meshes=imported_records,
    )
