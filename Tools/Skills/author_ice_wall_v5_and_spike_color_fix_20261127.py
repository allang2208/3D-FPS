"""Headless UE5 authoring script for:
  1) IceSpike Color Fix (2026-11-27):
     - Enables MATUSAGE_INSTANCED_STATIC_MESHES on M_IceHeart, M_IceShell,
       M_BlizzardIceHeart, and M_BlizzardIceShell (eliminating ISM WorldGridMaterial fallback).
     - Upgrades M_IceHeart & M_IceShell (and Blizzard mirrors) to pure glacier-blue/cyan-white
       crystalline ice with Fresnel edge brilliance, 3-layer parallax fractures, exposure-safe
       inner refraction sheen, and zero muddy/earth-brown cast or terrain bleed-through.
  2) IceWall Glacial V5 (2026-11-27):
     - Re-imports high-detail sculpted SM_IceBlock_01..04.fbx from SourceAssets/IceWall20260930/GlacialV5
       with VertexColorImportOption.REPLACE + FBXNIM_IMPORT_NORMALS_AND_TANGENTS.
     - Rebuilds /Game/Skills/IceWall/FabIceV3/M_IceWall with world-space triplanar mapping
       (zero UV stretch or seams), Snell-refracted (IOR 1.31) interior clouding + 3-layer
       parallax fractures, dual-scale Fab crystal normals (T_Ice1_normal + T_Ice6_normal),
       and true sculpted vertex-color curvature shading (R ridge frost, G shelf rime,
       B abyssal cleavage crevices, A per-facet crystal tone).
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
MESH_SRC = ROOT / 'SourceAssets/IceWall20260930/GlacialV5'

SPIKE_PROD = Path('F:/FPSGAMEData/ArtProduction/IceSpike/ColorFix-20261127')
SPIKE_BEFORE = SPIKE_PROD / 'Before'
SPIKE_BEFORE.mkdir(parents=True, exist_ok=True)

WALL_PROD = Path('F:/FPSGAMEData/ArtProduction/IceWall/GlacialV5-20261127')
WALL_BEFORE = WALL_PROD / 'Before'
WALL_BEFORE.mkdir(parents=True, exist_ok=True)

EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

SPIKE_TARGETS = [
    '/Game/Skills/IceSpike/FrostV2/M_IceSpikeHeartV3',
    '/Game/Skills/IceSpike/FrostV2/M_IceSpikeShellV3',
    '/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceHeart',
    '/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceShell',
]

WALL_TARGETS = [
    '/Game/Skills/IceWall/FabIceV3/M_IceWall',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_01',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_02',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_03',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_04',
]


def disk_path(asset_path):
    return ROOT / 'Content' / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def backup_list(targets, dest_dir):
    backed = {}
    for ap in targets:
        src = disk_path(ap)
        dst = dest_dir / (ap.split('/')[-1] + '.uasset')
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
        backed[ap] = str(dst) if dst.is_file() else None
    return backed


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def clear_expressions(mat):
    # UE 5.8 snapshot deletion avoids stranded Custom expressions
    for old in list(LIB.get_material_expressions(mat)):
        LIB.delete_material_expression(mat, old)


def make_helpers(mat, label):
    def node(cls):
        return LIB.create_material_expression(mat, cls)

    def wire(src, ch, dst, pin):
        if not LIB.connect_material_expressions(src, ch, dst, pin):
            raise RuntimeError(f'{label} wire failed -> {pin}')

    def out(src, ch, prop):
        if not LIB.connect_material_property(src, ch, prop):
            raise RuntimeError(f'{label} output failed -> {prop}')

    def scalar(name, val):
        n = node(u.MaterialExpressionScalarParameter)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', val)
        return n

    def custom(code, inputs, kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
        n = node(u.MaterialExpressionCustom)
        n.set_editor_property('code', code)
        n.set_editor_property('output_type', kind)
        pins = []
        for k in inputs:
            p = u.CustomInput()
            p.set_editor_property('input_name', k)
            pins.append(p)
        n.set_editor_property('inputs', pins)
        for k, (expr, ch) in inputs.items():
            wire(expr, ch, n, k)
        return n

    return node, wire, out, scalar, custom


def rebuild_ice_spike_material(asset_path, is_shell, allow_delete=True):
    if EAL.does_asset_exist(asset_path):
        mat = u.load_asset(asset_path)
    else:
        folder, name = asset_path.rsplit('/', 1)
        mat = TOOLS.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('Missing or failed to create spike material: ' + asset_path)

    t_base = u.load_asset('/Game/Skills/IceSpike/FrostV2/T_IceBaseColor')
    t_normal = u.load_asset('/Game/Skills/IceSpike/FrostV2/T_IceNormal')
    t_cracks = u.load_asset('/Game/Skills/IceSpike/T_IceCracks')
    for tex, nm in ((t_base, 'T_IceBaseColor'), (t_normal, 'T_IceNormal'), (t_cracks, 'T_IceCracks')):
        if not tex:
            raise RuntimeError('Missing required spike texture: ' + nm)

    if allow_delete:
        clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT if is_shell else u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT if is_shell else u.MaterialShadingModel.MSM_SUBSURFACE)
    if is_shell:
        mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property('enable_responsive_aa', True)
        mat.set_editor_property('output_translucent_velocity', True)
        mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        mat.set_editor_property('two_sided', False)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    node, wire, out, scalar, custom = make_helpers(mat, asset_path.split('/')[-1])

    uv = node(u.MaterialExpressionTextureCoordinate)
    rand = node(u.MaterialExpressionPerInstanceRandom)
    base = node(u.MaterialExpressionTextureSample)
    base.set_editor_property('texture', t_base)
    base.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    wire(uv, '', base, 'UVs')

    normal = node(u.MaterialExpressionTextureSample)
    normal.set_editor_property('texture', t_normal)
    normal.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    wire(uv, '', normal, 'UVs')

    vcol = node(u.MaterialExpressionVertexColor)
    crack_obj = node(u.MaterialExpressionTextureObject)
    crack_obj.set_editor_property('texture', t_cracks)
    cam_ws = node(u.MaterialExpressionCameraVectorWS)
    norm_ws = node(u.MaterialExpressionVertexNormalWS)

    cam_ts = node(u.MaterialExpressionTransform)
    cam_ts.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    cam_ts.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    wire(cam_ws, '', cam_ts, '')

    cracks = custom(
        '''float2 p = clamp(normalize(V).xy / max(abs(normalize(V).z), .35), -1.3, 1.3) * .018;
float2 o = float2(R * .47, R * .83);
float c1 = Texture2DSample(T, TSampler, UV * 2.1 + o).r;
float c2 = Texture2DSample(T, TSampler, UV * 2.4 + p + o).g;
float c3 = Texture2DSample(T, TSampler, UV * 3.8 + p * 2.1 + o).b;
return saturate(c1 * .52 + c2 * .34 + c3 * .22);''',
        {'T': (crack_obj, ''), 'UV': (uv, ''), 'V': (cam_ts, ''), 'R': (rand, '')},
    )

    fresnel = custom(
        'return pow(1. - saturate(abs(dot(normalize(N), normalize(V)))), 2.35);',
        {'N': (norm_ws, ''), 'V': (cam_ws, '')},
    )

    # VertexColor.R runs 0 at thick base -> 1 at sharp tip; add base frost + tip crystal sheen + cracks
    frost = custom(
        'float baseF = pow(saturate(1. - H), 3.2) * .68; float tipF = pow(saturate(H), 2.6) * .28; return saturate(baseF + tipF + C * .34 + Fren * .24);',
        {'H': (vcol, 'R'), 'C': (cracks, ''), 'Fren': (fresnel, '')},
    )

    # Pure glacier-blue / frost-white palette driven by luminance only -> zero warm/brown contamination
    if is_shell:
        color_code = '''float lum = saturate(dot(B, float3(.2126, .7152, .0722)));
float3 deepIce = float3(.16, .48, .72);
float3 midIce  = float3(.48, .82, .96);
float3 frostW  = float3(.86, .95, 1.00);
float3 col = lerp(deepIce, midIce, saturate(lum * 1.15 + C * .35));
col = lerp(col, frostW, saturate(F * .78 + Fren * .42));
return col * lerp(.93, 1.07, R);'''
    else:
        color_code = '''float lum = saturate(dot(B, float3(.2126, .7152, .0722)));
float3 deepIce = float3(.07, .28, .48);
float3 midIce  = float3(.32, .68, .88);
float3 frostW  = float3(.84, .94, .99);
float3 col = lerp(deepIce, midIce, saturate(pow(max(lum, 0.), .85) * 1.25 + C * .28));
col = lerp(col, float3(.62, .88, .98), saturate(Fren * .46 + C * .24));
col = lerp(col, frostW, saturate(F * .72));
return col * lerp(.92, 1.08, R);'''

    base_color = custom(
        color_code,
        {'B': (base, 'RGB'), 'C': (cracks, ''), 'F': (frost, ''), 'Fren': (fresnel, ''), 'R': (rand, '')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    out(base_color, '', u.MaterialProperty.MP_BASE_COLOR)

    norm_out = custom(
        'return normalize(lerp(float3(0, 0, 1), N, .52));',
        {'N': (normal, 'RGB')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    out(norm_out, '', u.MaterialProperty.MP_NORMAL)

    rough_code = 'return lerp(.10, .34, F);' if is_shell else 'return lerp(.11, .38, F);'
    out(custom(rough_code, {'F': (frost, '')}), '', u.MaterialProperty.MP_ROUGHNESS)

    spec_c = node(u.MaterialExpressionConstant)
    spec_c.set_editor_property('r', 0.48)
    out(spec_c, '', u.MaterialProperty.MP_SPECULAR)

    metal_c = node(u.MaterialExpressionConstant)
    metal_c.set_editor_property('r', 0.0)
    out(metal_c, '', u.MaterialProperty.MP_METALLIC)

    ao_c = node(u.MaterialExpressionConstant)
    ao_c.set_editor_property('r', 1.0)
    out(ao_c, '', u.MaterialProperty.MP_AMBIENT_OCCLUSION)

    if is_shell:
        opac = custom('return lerp(.34, .90, saturate(F * .82 + Fren * .58));', {'F': (frost, ''), 'Fren': (fresnel, '')})
        out(opac, '', u.MaterialProperty.MP_OPACITY)
    else:
        opac_c = node(u.MaterialExpressionConstant)
        opac_c.set_editor_property('r', 0.68)
        out(opac_c, '', u.MaterialProperty.MP_OPACITY)
        sss = custom(
            'return lerp(float3(.16, .54, .82), float3(.58, .88, 1.00), saturate(F * .65 + C * .35));',
            {'F': (frost, ''), 'C': (cracks, '')},
            u.CustomMaterialOutputType.CMOT_FLOAT3,
        )
        out(sss, '', u.MaterialProperty.MP_SUBSURFACE_COLOR)

    # Subtle exposure-compensated cool inner refraction sheen keeps shadowed spike faces pure icy blue
    exposure = node(u.MaterialExpressionEyeAdaptation)
    em_gain = '(.024 + C * .075 + Fren * .11)' if not is_shell else '(.016 + C * .055 + Fren * .09)'
    emissive = custom(
        f'return float3(.24, .68, .96) * {em_gain} / max(Exp, .18);',
        {'C': (cracks, ''), 'Fren': (fresnel, ''), 'Exp': (exposure, '')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    out(emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR)

    errors = [str(e) for e in LIB.recompile_material(mat)]
    if errors:
        raise RuntimeError(f'{asset_path} compile failed:\n' + '\n'.join(errors))
    if not EAL.save_loaded_asset(mat, False):
        raise RuntimeError(f'{asset_path} save failed')
    print('SPIKE_MAT_SAVED', mat.get_path_name(), flush=True)
    return mat


def rebuild_ice_wall_material_v5():
    path = '/Game/Skills/IceWall/FabIceV3/M_IceWall'
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing ' + path)

    t_color = u.load_asset('/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor')
    t_facet_norm = u.load_asset('/Game/Ice/Textures/T_Ice1_normal')
    t_facet_rough = u.load_asset('/Game/Ice/Textures/T_Ice1_roughness')
    t_micro_norm = u.load_asset('/Game/Ice/Textures/T_Ice6_normal')
    t_ao = u.load_asset('/Game/Ice/Textures/T_Ice6_AO')
    t_cracks = u.load_asset('/Game/Skills/IceSpike/T_IceCracks')
    for tex, nm in (
        (t_color, 'T_IceSurfaceColor'),
        (t_facet_norm, 'T_Ice1_normal'),
        (t_facet_rough, 'T_Ice1_roughness'),
        (t_micro_norm, 'T_Ice6_normal'),
        (t_ao, 'T_Ice6_AO'),
        (t_cracks, 'T_IceCracks'),
    ):
        if not tex:
            raise RuntimeError('Missing required IceWall texture: ' + nm)

    clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_SUBSURFACE)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    node, wire, out, scalar, custom = make_helpers(mat, 'M_IceWall_V5')

    def tex_obj(tex):
        o = node(u.MaterialExpressionTextureObject)
        o.set_editor_property('texture', tex)
        return o

    o_color = tex_obj(t_color)
    o_facet_norm = tex_obj(t_facet_norm)
    o_facet_rough = tex_obj(t_facet_rough)
    o_micro_norm = tex_obj(t_micro_norm)
    o_ao = tex_obj(t_ao)
    o_cracks = tex_obj(t_cracks)

    world_pos = node(u.MaterialExpressionWorldPosition)
    norm_ws = node(u.MaterialExpressionVertexNormalWS)
    cam_ws = node(u.MaterialExpressionCameraVectorWS)
    vcol = node(u.MaterialExpressionVertexColor)
    rand = node(u.MaterialExpressionPerInstanceRandom)

    tiling = scalar('IceTextureScale', 0.0082)       # ~122 cm real-world crystal repeat
    depth_cm = scalar('InternalIceDepth', 22.0)      # refracted interior depth in cm
    frost_amt = scalar('FrostAmount', 0.62)
    norm_str = scalar('IceNormalStrength', 0.82)
    damage_crack = scalar('DamageCrack', 0.0)
    freeze_prog = scalar('FreezeProgress', 1.0)
    base_z = scalar('BaseFrostZ', -99999.0)

    # 1) World-space triplanar surface + Snell-refracted (IOR 1.31) interior clouding + roughness + AO
    #    Returns float4(SurfaceLum, DeepLum, FacetRough, AO)
    tri_surface = custom(
        '''float3 n = normalize(NWS);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 offs = float3(R * 73.1, R * 131.7, R * 47.9);
float3 p = (WP + offs) * Scale;

// Snell-refracted interior sample point (ice IOR = 1.31) for physical glassy depth while strafing
float3 vws = normalize(CamWS);
float3 rdir = refract(-vws, n, 1.0 / 1.31);
if (dot(rdir, rdir) < 1e-4) rdir = -vws;
float3 pDeep = (WP + rdir * DepthCM + offs) * (Scale * 1.12);

float3 cX = Texture2DSample(TCol, TColSampler, p.yz).rgb;
float3 cY = Texture2DSample(TCol, TColSampler, p.xz).rgb;
float3 cZ = Texture2DSample(TCol, TColSampler, p.xy).rgb;
float3 colS = cX * w.x + cY * w.y + cZ * w.z;

float3 dX = Texture2DSample(TCol, TColSampler, pDeep.yz).rgb;
float3 dY = Texture2DSample(TCol, TColSampler, pDeep.xz).rgb;
float3 dZ = Texture2DSample(TCol, TColSampler, pDeep.xy).rgb;
float3 colD = dX * w.x + dY * w.y + dZ * w.z;

float rX = Texture2DSample(TRgh, TRghSampler, p.yz * 1.15).r;
float rY = Texture2DSample(TRgh, TRghSampler, p.xz * 1.15).r;
float rZ = Texture2DSample(TRgh, TRghSampler, p.xy * 1.15).r;
float rgh = rX * w.x + rY * w.y + rZ * w.z;

float aX = Texture2DSample(TAO, TAOSampler, p.yz * 1.25).r;
float aY = Texture2DSample(TAO, TAOSampler, p.xz * 1.25).r;
float aZ = Texture2DSample(TAO, TAOSampler, p.xy * 1.25).r;
float ao = aX * w.x + aY * w.y + aZ * w.z;

float lumS = dot(colS, float3(.2126, .7152, .0722));
float lumD = dot(colD, float3(.2126, .7152, .0722));
return float4(lumS, lumD, rgh, ao);''',
        {
            'WP': (world_pos, ''),
            'NWS': (norm_ws, ''),
            'CamWS': (cam_ws, ''),
            'R': (rand, ''),
            'Scale': (tiling, ''),
            'DepthCM': (depth_cm, ''),
            'TCol': (o_color, ''),
            'TRgh': (o_facet_rough, ''),
            'TAO': (o_ao, ''),
        },
        u.CustomMaterialOutputType.CMOT_FLOAT4,
    )

    # 2) World-space triplanar 3-layer refracted internal glacial fractures (T_IceCracks)
    cracks = custom(
        '''float3 n = normalize(NWS);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 vws = normalize(CamWS);
float3 rdir = refract(-vws, n, 1.0 / 1.31);
if (dot(rdir, rdir) < 1e-4) rdir = -vws;

float3 offs = float3(R * 53.7, R * 97.3, R * 31.1);
float3 p1 = (WP + offs) * (Scale * 1.35);
float3 p2 = (WP + rdir * (DepthCM * .55) + offs) * (Scale * 1.95);
float3 p3 = (WP + rdir * (DepthCM * 1.25) + offs) * (Scale * 3.10);

float c1 = Texture2DSample(TCrk, TCrkSampler, p1.yz).r * w.x + Texture2DSample(TCrk, TCrkSampler, p1.xz).r * w.y + Texture2DSample(TCrk, TCrkSampler, p1.xy).r * w.z;
float c2 = Texture2DSample(TCrk, TCrkSampler, p2.yz).g * w.x + Texture2DSample(TCrk, TCrkSampler, p2.xz).g * w.y + Texture2DSample(TCrk, TCrkSampler, p2.xy).g * w.z;
float c3 = Texture2DSample(TCrk, TCrkSampler, p3.yz).b * w.x + Texture2DSample(TCrk, TCrkSampler, p3.xz).b * w.y + Texture2DSample(TCrk, TCrkSampler, p3.xy).b * w.z;

float baseC = saturate(c1 * .46 + c2 * .34 + c3 * .24);
// Concentrate extra spiderweb fracturing inside sculpted concave cleavage seams (VC.b) and when damaged
float seamBoost = 1.0 + VC.b * .65 + Dmg * 1.15;
return saturate(baseC * .74 * seamBoost + pow(saturate(c1 * c2 * 2.4), 1.45) * (Dmg * .75 + VC.b * .28));''',
        {
            'WP': (world_pos, ''),
            'NWS': (norm_ws, ''),
            'CamWS': (cam_ws, ''),
            'R': (rand, ''),
            'Scale': (tiling, ''),
            'DepthCM': (depth_cm, ''),
            'TCrk': (o_cracks, ''),
            'VC': (vcol, ''),
            'Dmg': (damage_crack, ''),
        },
    )

    # 3) Frost / rime / upward freezing wave state -> float2(totalFrost, waveBand)
    frost_state = custom(
        '''float h = max(0., WP.z - BaseZ);
float hasBase = BaseZ > -90000. ? 1. : 0.;
float baseRime = smoothstep(82., 0., h) * hasBase;
float waveH = Freeze * 340.;
float waveBand = exp(-pow((h - waveH) / 36., 2)) * (1. - smoothstep(.88, 1., Freeze)) * hasBase;

// Sculpted vertex colors: R = sharp convex crystal ridges, G = upward shelf rime, B = deep crevices (stay clearer/darker)
float ridgeFrost = pow(saturate(VC.r), 1.15) * 1.05 * Amount;
float shelfRime  = pow(saturate(VC.g), 1.05) * .72 * Amount;
float cavityClear = 1.0 - saturate(VC.b) * .55;
float totalFrost = saturate((ridgeFrost + shelfRime + saturate(Surf.z - .48) * .18) * cavityClear + baseRime * .64 + Crk * .34 + waveBand * .58);
return float2(totalFrost, waveBand);''',
        {
            'WP': (world_pos, ''),
            'BaseZ': (base_z, ''),
            'Freeze': (freeze_prog, ''),
            'VC': (vcol, ''),
            'Amount': (frost_amt, ''),
            'Surf': (tri_surface, ''),
            'Crk': (cracks, ''),
        },
        u.CustomMaterialOutputType.CMOT_FLOAT2,
    )

    # 4) Dual-scale world-space triplanar normals (macro T_Ice1_normal facets + micro T_Ice6_normal glacier veins)
    #    Transformed cleanly from World -> Tangent space so normal detail is 100% scale-invariant and seam-free!
    world_norm = custom(
        '''float3 n = normalize(NWS);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 offs = float3(R * 73.1, R * 131.7, R * 47.9);
float3 p1 = (WP + offs) * (Scale * 1.10);
float3 p2 = (WP + offs) * (Scale * 2.45);

float3 fX = UnpackNormalMap(Texture2DSample(TFac, TFacSampler, p1.yz)).xyz;
float3 fY = UnpackNormalMap(Texture2DSample(TFac, TFacSampler, p1.xz)).xyz;
float3 fZ = UnpackNormalMap(Texture2DSample(TFac, TFacSampler, p1.xy)).xyz;

float3 mX = UnpackNormalMap(Texture2DSample(TMic, TMicSampler, p2.yz)).xyz;
float3 mY = UnpackNormalMap(Texture2DSample(TMic, TMicSampler, p2.xz)).xyz;
float3 mZ = UnpackNormalMap(Texture2DSample(TMic, TMicSampler, p2.xy)).xyz;

// Reduce normal noise slightly under heavy snow rime, sharpen along fractured seams (VC.b)
float sFac = Strength * lerp(.72, 1.12, saturate(VC.b + (1. - FS.x) * .5));
float sMic = Strength * .46 * lerp(1.0, .62, FS.x);

float2 dX = fX.xy * sFac + mX.xy * sMic;
float2 dY = fY.xy * sFac + mY.xy * sMic;
float2 dZ = fZ.xy * sFac + mZ.xy * sMic;

float3 wx = normalize(float3(n.x, n.y + dX.x, n.z + dX.y));
float3 wy = normalize(float3(n.x + dY.x, n.y, n.z + dY.y));
float3 wz = normalize(float3(n.x + dZ.x, n.y + dZ.y, n.z));
return normalize(wx * w.x + wy * w.y + wz * w.z);''',
        {
            'WP': (world_pos, ''),
            'NWS': (norm_ws, ''),
            'R': (rand, ''),
            'Scale': (tiling, ''),
            'Strength': (norm_str, ''),
            'TFac': (o_facet_norm, ''),
            'TMic': (o_micro_norm, ''),
            'VC': (vcol, ''),
            'FS': (frost_state, ''),
        },
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )

    norm_ts = node(u.MaterialExpressionTransform)
    norm_ts.set_editor_property('transform_source_type', u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    norm_ts.set_editor_property('transform_type', u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    wire(world_norm, '', norm_ts, '')

    fresnel = custom(
        'return pow(1. - saturate(abs(dot(normalize(N), normalize(V)))), 2.55);',
        {'N': (world_norm, ''), 'V': (cam_ws, '')},
    )

    # 5) Layered glacier crystal color: abyssal crevices -> deep sapphire core -> translucent cyan -> crisp frost ridges
    base_color = custom(
        '''float lumS = Surf.x;
float lumD = Surf.y;
float cloud = saturate(pow(max(lumS, 0.), .76) * 1.28);

float3 abyssal = float3(.03, .14, .26);
float3 deepIce = float3(.07, .26, .42);
float3 midIce  = float3(.26, .62, .82);
float3 facetHi = float3(.52, .84, .97);
float3 rimeCol = float3(.84, .93, .98);

// Per-facet crystal tone (VA) shifts neighboring cleaved planes subtly
float facetTone = lerp(.88, 1.14, VA);
float3 core = lerp(deepIce, midIce, cloud) * facetTone;

// Refracted interior brightness parallax contrast
core *= clamp(1.0 + (lumD - lumS) * 1.25, .80, 1.22) * lerp(.95, 1.06, R);

// Deepen sculpted concave cleavage grooves (VC.b) into glacial sapphire
core = lerp(core, abyssal, saturate(VC.b * .68));

// Brighten internal fracture veins & grazing Fresnel crystal rims
core = lerp(core, facetHi, saturate(Crk * .52 + Fren * .38 + VC.r * .22));

// Apply crisp frosted ridges, top shelf rime, and ground freeze collar
return lerp(core, rimeCol, saturate(FS.x * .82));''',
        {
            'Surf': (tri_surface, ''),
            'VA': (vcol, 'A'),
            'VC': (vcol, ''),
            'R': (rand, ''),
            'Crk': (cracks, ''),
            'Fren': (fresnel, ''),
            'FS': (frost_state, ''),
        },
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )

    # Glassy cleaved facets (~0.06-0.16 roughness) vs frosted rime ridges (~0.40-0.52)
    rough = custom(
        'float baseR = .055 + Surf.z * .18 + (1. - VA) * .04; return clamp(baseR + FS.x * .42 - Crk * .04 - VC.b * .03, .055, .52);',
        {'Surf': (tri_surface, ''), 'VA': (vcol, 'A'), 'FS': (frost_state, ''), 'Crk': (cracks, ''), 'VC': (vcol, '')},
    )

    ao = custom(
        'return clamp((.80 + Surf.w * .20) * (1.0 - VC.b * .28), .52, 1.0);',
        {'Surf': (tri_surface, ''), 'VC': (vcol, '')},
    )

    subsurface = custom(
        'float3 s = lerp(float3(.12, .48, .72), float3(.56, .88, 1.00), saturate(FS.x * .45 + Crk * .45 + VC.r * .25)); return s * (1.0 - VC.b * .32);',
        {'FS': (frost_state, ''), 'Crk': (cracks, ''), 'VC': (vcol, '')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )

    # Subtle exposure-compensated internal cryo sheen + freeze wave crest (never neon)
    exposure = node(u.MaterialExpressionEyeAdaptation)
    emissive = custom(
        '''float glow = .018 + Crk * (.072 + Dmg * .20) + Fren * .085 + VC.r * .026 + FS.y * .54;
return float3(.24, .68, .94) * glow / max(Exp, .18);''',
        {
            'Crk': (cracks, ''),
            'Dmg': (damage_crack, ''),
            'Fren': (fresnel, ''),
            'VC': (vcol, ''),
            'FS': (frost_state, ''),
            'Exp': (exposure, ''),
        },
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )

    out(base_color, '', u.MaterialProperty.MP_BASE_COLOR)
    out(rough, '', u.MaterialProperty.MP_ROUGHNESS)
    out(norm_ts, '', u.MaterialProperty.MP_NORMAL)
    out(ao, '', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    out(subsurface, '', u.MaterialProperty.MP_SUBSURFACE_COLOR)
    out(emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    for prop, val in (
        (u.MaterialProperty.MP_METALLIC, 0.0),
        (u.MaterialProperty.MP_SPECULAR, 0.52),
        (u.MaterialProperty.MP_OPACITY, 0.72),
    ):
        c = node(u.MaterialExpressionConstant)
        c.set_editor_property('r', val)
        out(c, '', prop)

    errors = [str(e) for e in LIB.recompile_material(mat)]
    if errors:
        raise RuntimeError('M_IceWall V5 compile failed:\n' + '\n'.join(errors))
    if not EAL.save_loaded_asset(mat, False):
        raise RuntimeError('M_IceWall V5 save failed')
    print('ICE_WALL_V5_MAT_SAVED', mat.get_path_name(), flush=True)
    return mat


def reimport_ice_wall_meshes_v5(mat):
    imported = []
    for idx in range(1, 5):
        name = f'SM_IceBlock_{idx:02d}'
        fbx = MESH_SRC / (name + '.fbx')
        if not fbx.is_file():
            raise RuntimeError('Missing sculpted FBX: ' + str(fbx))
        task = u.AssetImportTask()
        task.filename = str(fbx)
        task.destination_path = '/Game/Skills/IceWall/FabIceV3'
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        options = u.FbxImportUI()
        options.import_mesh = True
        options.import_materials = False
        options.import_textures = False
        options.automated_import_should_detect_type = False
        options.import_as_skeletal = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        data = options.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.convert_scene_unit = True
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
        task.options = options
        TOOLS.import_asset_tasks([task])

        asset_path = f'/Game/Skills/IceWall/FabIceV3/{name}'
        mesh = u.load_asset(asset_path)
        if not mesh:
            raise RuntimeError('Failed to load reimported mesh: ' + asset_path)
        mesh.set_material(0, mat)
        if not EAL.save_loaded_asset(mesh, False):
            raise RuntimeError('Failed to save mesh: ' + asset_path)
        tris = mesh.get_num_triangles(0) if hasattr(mesh, 'get_num_triangles') else -1
        print('ICE_WALL_V5_MESH_SAVED', asset_path, 'tris=', tris, flush=True)
        imported.append({'asset': asset_path, 'fbx': str(fbx), 'triangles': tris})
    return imported


def main():
    cmdline = u.SystemLibrary.get_command_line()
    spikes_only = '-IceSpikesOnly' in cmdline
    spike_before = backup_list(SPIKE_TARGETS, SPIKE_BEFORE)

    if not spikes_only:
        wall_before = backup_list(WALL_TARGETS, WALL_BEFORE)

        # 1) Rebuild IceWall V5 material + re-import sculpted SM_IceBlock_01..04 first (never locked by CDO)
        wall_mat = rebuild_ice_wall_material_v5()
        meshes = reimport_ice_wall_meshes_v5(wall_mat)

        wall_receipt = {
            'version': 'IceWallGlacialV5_20261127',
            'source_meshes': str(MESH_SRC),
            'backups': wall_before,
            'imported_meshes': meshes,
            'saved_assets': {
                ap: {
                    'disk': str(disk_path(ap)),
                    'bytes': disk_path(ap).stat().st_size,
                    'sha256': sha256(disk_path(ap)),
                }
                for ap in WALL_TARGETS
            },
            'reused_textures': [
                '/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor',
                '/Game/Ice/Textures/T_Ice1_normal',
                '/Game/Ice/Textures/T_Ice1_roughness',
                '/Game/Ice/Textures/T_Ice6_normal',
                '/Game/Ice/Textures/T_Ice6_AO',
                '/Game/Skills/IceSpike/T_IceCracks',
            ],
            'runtime_tested': False,
        }
        (WALL_PROD / 'published.json').write_text(json.dumps(wall_receipt, indent=2, ensure_ascii=False), encoding='utf-8')

        # 2) Fix Blizzard ISM spike materials (never locked by CDO)
        rebuild_ice_spike_material('/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceHeart', False, allow_delete=True)
        rebuild_ice_spike_material('/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceShell', True, allow_delete=True)

    # 3) Author clean V3 IceSpike FrostV2 materials (leaves legacy M_IceHeart/Shell untouched for M07MagicAttack CDO)
    rebuild_ice_spike_material('/Game/Skills/IceSpike/FrostV2/M_IceSpikeHeartV3', False, allow_delete=True)
    rebuild_ice_spike_material('/Game/Skills/IceSpike/FrostV2/M_IceSpikeShellV3', True, allow_delete=True)

    spike_receipt = {
        'version': 'IceSpikeColorFix_20261127',
        'root_causes_fixed': [
            'Legacy M_IceHeart and M_IceShell lacked MATUSAGE_INSTANCED_STATIC_MESHES (caused ISM WorldGridMaterial fallback on AbsoluteZero Buckets 1-2)',
            'FPSAbsoluteZeroNova Buckets 1-2 used hollow 25%-opaque translucent M_IceShell without opaque inner core over brown terrain',
            'Created clean ISM-enabled M_IceSpikeHeartV3/M_IceSpikeShellV3 (leaving legacy M_IceHeart/Shell untouched for M07MagicAttack CDO) and upgraded M_BlizzardIceHeart/M_BlizzardIceShell to luminance-driven pure glacier palette',
            'Unified all 108 AbsoluteZero radial spikes and shards onto opaque glacier M_IceSpikeHeartV3; updated IceSpikeVolley/IceSpikeComponent/PlayerSkillAssets to V3 materials',
        ],
        'backups': spike_before,
        'saved_assets': {
            ap: {
                'disk': str(disk_path(ap)),
                'bytes': disk_path(ap).stat().st_size,
                'sha256': sha256(disk_path(ap)),
            }
            for ap in SPIKE_TARGETS
        },
        'runtime_tested': False,
    }
    (SPIKE_PROD / 'published.json').write_text(json.dumps(spike_receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print('ALL_ICE_V5_AND_SPIKE_COLOR_FIX_DONE', flush=True)


if __name__ == '__main__':
    main()
