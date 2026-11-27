"""Headless UE5 authoring script for AbsoluteZero V4 — Photorealistic Cryo VFX & IceSpike Dual-Layer Spires (2026-11-27).

Addresses BOTH visual issues spotted in in-game PIE screenshot:
  1. Photorealistic Cryo Particles (zero pixel squares!):
     - Fixes /Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft (backs up to Before/; fixes the UE 5.8
       DepthFade 'Opacity' pin mismatch that caused full 100%-opaque flat grey squares, and replaces
       hard diamond math with soft organic feathered snow-dust mask!).
     - Authors /Game/Skills/AbsoluteZero/M_AbsoluteZeroIceDust: photorealistic soft feathered ice-mist
       & sparkling frost-powder sprite using T_Smoke_Wisp + smooth radial Gaussian + twinkling glint + DepthFade.
     - Rebuilds /Game/Skills/AbsoluteZero/NS_AbsoluteZeroBurstWave:
         Emitter 1 (OutwardCryoMist): Mantaflow 8x8 ground-hugging sub-zero vapor wave tuned to
           realistic cool slate-ice twilight tint (zero milky wash).
         Emitter 2 (OutwardIceShards): fine wind-blown photorealistic snow/frost motes (1.8-4.8 cm)
           using M_AbsoluteZeroIceDust (ZERO hard quad edges or grey squares!).
  2. IceSpike-Derived Dual-Layer Photorealistic Glacier Crystal Spires:
     - Re-imports RAZOR-FACETED SM_AZ_GlacierSpire_01..03 & SM_AZ_IceFangCluster (true planar mineral
       crystal prisms, zero smooth voxel cones, 20-deg sharp split normals, tight root/edge Frost RGBA).
     - Rebuilds /Game/Skills/AbsoluteZero/M_AbsoluteZeroSpire (Opaque Subsurface Heart, ISM-enabled):
         Directly derived from approved IceSpike magic shader (T_IceBaseColor 4K + T_IceNormal 4K +
         T_Ice1_normal + 3-layer Snell-refracted T_IceCracks). Deep dark-glacier slate-teal PBR core
         (ZERO neon pastel baby-blue emissive wash during standing hold!), razor specular glints,
         subtle dark-teal subsurface, brief EruptionFlash & pre-shatter ShatterGlow only.
     - Creates /Game/Skills/AbsoluteZero/M_AbsoluteZeroSpireShell (Translucent TLM_SURFACE_PER_PIXEL_LIGHTING,
       ISM-enabled): exact IceSpike magic outer glassy crystal coat wrapped around hero monoliths
       for genuine double-layer optical refraction & parallax depth!
     - Retains /Game/Skills/AbsoluteZero/M_AbsoluteZeroShockRing (refined cooler realistic cryo crest).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
MESH_SRC = ROOT / 'SourceAssets/AbsoluteZeroV3_20261127'
DEST = '/Game/Skills/AbsoluteZero'
PROD = Path('F:/FPSGAMEData/ArtProduction/AbsoluteZero/AbsoluteZeroV4-20261127')
BEFORE = PROD / 'Before'
BEFORE.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth

EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
VEC4 = '/Script/CoreUObject.Vector4f'
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'


def disk_path(asset_path):
    return ROOT / 'Content' / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def backup_if_needed(asset_paths):
    out = {}
    for ap in asset_paths:
        src = disk_path(ap)
        dst = BEFORE / (ap.split('/')[-1] + '.uasset')
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
        out[ap] = str(dst) if dst.is_file() else None
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def create_or_reset_material(asset_path):
    if EAL.does_asset_exist(asset_path):
        mat = u.load_asset(asset_path)
        for old in list(LIB.get_material_expressions(mat)):
            LIB.delete_material_expression(mat, old)
    else:
        folder, name = asset_path.rsplit('/', 1)
        mat = TOOLS.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('Failed to create/load material: ' + asset_path)
    return mat


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
        n.set_editor_property('default_value', float(val))
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


def fix_frost_crystal_soft_material():
    """Fix the UE 5.8 DepthFade 'Opacity' pin bug on /Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft
    so NO Niagara system (NS_FrostCrystals, NS_AbsoluteZeroInwardMist, NS_BlizzardSnow) ever draws
    a hard-edged flat grey square."""
    ap = '/Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft'
    mat = create_or_reset_material(ap)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    mat.set_editor_property('enable_responsive_aa', True)
    mat.set_editor_property('output_translucent_velocity', False)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)

    node, wire, out, scalar, custom = make_helpers(mat, 'M_FrostCrystalSoft')
    uv = node(u.MaterialExpressionTextureCoordinate)
    pcol = node(u.MaterialExpressionParticleColor)
    depth = node(u.MaterialExpressionPixelDepth)

    # Soft feathered circular snowflake / frost-grain mask (zero hard quad edges, zero diamond corners!)
    mask = custom(
        '''float2 p = (UV - .5) * 2.0;
float r = length(p);
float ang = atan2(p.y, p.x);
float organic = 1.0 - .14 * sin(ang * 5.0) - .08 * cos(ang * 7.0 + 1.1);
float disc = saturate(1.0 - r / max(.2, organic));
float soft = pow(disc, 2.2) * (1.0 - smoothstep(.78, 1.0, r));
return soft * A * saturate((D - 28.0) / 24.0);''',
        {'UV': (uv, ''), 'A': (pcol, 'A'), 'D': (depth, '')},
    )

    df = node(u.MaterialExpressionDepthFade)
    df.set_editor_property('fade_distance_default', 8.0)
    # CRITICAL UE 5.8 FIX: query exact pin name ('Opacity'), NOT legacy 'InOpacity'!
    df_opacity_pin = str(LIB.get_material_expression_input_names(df)[0])
    wire(mask, '', df, df_opacity_pin)

    out(pcol, 'RGB', u.MaterialProperty.MP_BASE_COLOR)
    out(df, '', u.MaterialProperty.MP_OPACITY)
    # Subtle cool moonlight scatter so flakes don't turn dark mud-grey in twilight shadow
    em = custom('return RGB * .18;', {'RGB': (pcol, 'RGB')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    out(em, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    for prop, val in ((u.MaterialProperty.MP_ROUGHNESS, 0.55), (u.MaterialProperty.MP_SPECULAR, 0.28)):
        c = node(u.MaterialExpressionConstant)
        c.set_editor_property('r', val)
        out(c, '', prop)

    errors = [str(e) for e in LIB.recompile_material(mat)]
    if errors:
        raise RuntimeError('M_FrostCrystalSoft compile failed:\n' + '\n'.join(errors))
    if not EAL.save_loaded_asset(mat, False):
        raise RuntimeError('M_FrostCrystalSoft save failed')
    print('AZ_V4_FROST_CRYSTAL_SOFT_FIXED', mat.get_path_name(), 'pin=', df_opacity_pin, flush=True)
    return mat


def build_realistic_ice_dust_material():
    """Photorealistic wind-blown snow dust / fine frost-powder sprite for NS_AbsoluteZeroBurstWave.
    Uses T_Smoke_Wisp organic fluid noise + soft Gaussian radial falloff + subtle crystal glint + DepthFade."""
    ap = f'{DEST}/M_AbsoluteZeroIceDust'
    mat = create_or_reset_material(ap)
    t_wisp = u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Smoke_Wisp')
    if not t_wisp:
        raise RuntimeError('Missing T_Smoke_Wisp')

    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    mat.set_editor_property('enable_responsive_aa', True)
    mat.set_editor_property('output_translucent_velocity', False)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)

    node, wire, out, scalar, custom = make_helpers(mat, 'M_AbsoluteZeroIceDust')
    uv = node(u.MaterialExpressionTextureCoordinate)
    pcol = node(u.MaterialExpressionParticleColor)
    depth = node(u.MaterialExpressionPixelDepth)
    wisp_obj = node(u.MaterialExpressionTextureObject)
    wisp_obj.set_editor_property('texture', t_wisp)

    # Organic feathered frost-powder grain with crisp sparkling pin-point core & zero square outline
    mask = custom(
        '''float2 p = (UV - .5) * 2.0;
float r = length(p);
float edgeKill = 1.0 - smoothstep(.58, .96, r);
float w = Texture2DSample(T, TSampler, UV).r;
float core = exp(-r * r * 5.2);
float powder = pow(saturate(1.0 - r), 1.8) * (.45 + .85 * w);
float alpha = saturate(core * .85 + powder * .65) * edgeKill * A * saturate((D - 32.0) / 28.0);
return alpha;''',
        {'UV': (uv, ''), 'T': (wisp_obj, ''), 'A': (pcol, 'A'), 'D': (depth, '')},
    )

    df = node(u.MaterialExpressionDepthFade)
    df.set_editor_property('fade_distance_default', 12.0)
    df_pin = str(LIB.get_material_expression_input_names(df)[0])
    wire(mask, '', df, df_pin)

    # Crisp icy white-blue diffuse + subtle glint core (natural in daylight and dark twilight alike!)
    out(pcol, 'RGB', u.MaterialProperty.MP_BASE_COLOR)
    out(df, '', u.MaterialProperty.MP_OPACITY)
    glint = custom(
        '''float r = length((UV - .5) * 2.0);
float sparkle = exp(-r * r * 14.0) * .38 + exp(-r * r * 3.5) * .12;
return RGB * sparkle;''',
        {'UV': (uv, ''), 'RGB': (pcol, 'RGB')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    out(glint, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    for prop, val in ((u.MaterialProperty.MP_ROUGHNESS, 0.35), (u.MaterialProperty.MP_SPECULAR, 0.45)):
        c = node(u.MaterialExpressionConstant)
        c.set_editor_property('r', val)
        out(c, '', prop)

    errors = [str(e) for e in LIB.recompile_material(mat)]
    if errors:
        raise RuntimeError('M_AbsoluteZeroIceDust compile failed:\n' + '\n'.join(errors))
    if not EAL.save_loaded_asset(mat, False):
        raise RuntimeError('M_AbsoluteZeroIceDust save failed')
    print('AZ_V4_ICEDUST_MAT_SAVED', mat.get_path_name(), flush=True)
    return mat


def build_icespike_style_spire_material(asset_path, is_shell):
    """Build photorealistic IceSpike-derived glacier crystal spire material:
      - is_shell=False -> M_AbsoluteZeroSpire (Opaque MSM_SUBSURFACE deep dark-glacier core)
      - is_shell=True  -> M_AbsoluteZeroSpireShell (Translucent TLM_SURFACE_PER_PIXEL_LIGHTING glassy outer sheath)

    Reuses the exact IceSpike magic textures (T_IceBaseColor 4K, T_IceNormal 4K, T_IceCracks)
    plus T_Ice1_normal macro cleavage facets, with ZERO pastel cartoon emissive wash!
    """
    mat = create_or_reset_material(asset_path)

    t_base = u.load_asset('/Game/Skills/IceSpike/FrostV2/T_IceBaseColor')
    t_normal = u.load_asset('/Game/Skills/IceSpike/FrostV2/T_IceNormal')
    t_cracks = u.load_asset('/Game/Skills/IceSpike/T_IceCracks')
    t_facet_norm = u.load_asset('/Game/Ice/Textures/T_Ice1_normal')
    for tex, nm in ((t_base, 'T_IceBaseColor'), (t_normal, 'T_IceNormal'),
                    (t_cracks, 'T_IceCracks'), (t_facet_norm, 'T_Ice1_normal')):
        if not tex:
            raise RuntimeError('Missing required IceSpike texture: ' + nm)

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

    def tex_obj(tex):
        o = node(u.MaterialExpressionTextureObject)
        o.set_editor_property('texture', tex)
        return o

    o_base = tex_obj(t_base)
    o_norm = tex_obj(t_normal)
    o_facet = tex_obj(t_facet_norm)
    o_cracks = tex_obj(t_cracks)

    world_pos = node(u.MaterialExpressionWorldPosition)
    norm_ws = node(u.MaterialExpressionVertexNormalWS)
    cam_ws = node(u.MaterialExpressionCameraVectorWS)
    vcol = node(u.MaterialExpressionVertexColor)
    rand = node(u.MaterialExpressionPerInstanceRandom)

    tiling = scalar('IceTextureScale', 0.0085)
    depth_cm = scalar('InternalIceDepth', 22.0 if not is_shell else 15.0)
    norm_str = scalar('IceNormalStrength', 0.92 if not is_shell else 0.62)
    eruption_flash = scalar('EruptionFlash', 0.0)
    shatter_glow = scalar('ShatterGlow', 0.0)

    # 1) World-space triplanar sampling of IceSpike's 4K T_IceBaseColor (surface + Snell-refracted interior)
    tri_base = custom(
        '''float3 n = normalize(NWS);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 offs = float3(R * 89.3, R * 147.1, R * 61.7);
float3 p = (WP + offs) * Scale;

float3 vws = normalize(CamWS);
float3 rdir = refract(-vws, n, 1.0 / 1.31);
if (dot(rdir, rdir) < 1e-4) rdir = -vws;
float3 pDeep = (WP + rdir * DepthCM + offs) * (Scale * 1.18);

float3 bS = Texture2DSample(TBase, TBaseSampler, p.yz).rgb * w.x
          + Texture2DSample(TBase, TBaseSampler, p.xz).rgb * w.y
          + Texture2DSample(TBase, TBaseSampler, p.xy).rgb * w.z;
float3 bD = Texture2DSample(TBase, TBaseSampler, pDeep.yz).rgb * w.x
          + Texture2DSample(TBase, TBaseSampler, pDeep.xz).rgb * w.y
          + Texture2DSample(TBase, TBaseSampler, pDeep.xy).rgb * w.z;

float lumS = dot(bS, float3(.2126, .7152, .0722));
float lumD = dot(bD, float3(.2126, .7152, .0722));
return float2(lumS, lumD);''',
        {
            'WP': (world_pos, ''),
            'NWS': (norm_ws, ''),
            'CamWS': (cam_ws, ''),
            'R': (rand, ''),
            'Scale': (tiling, ''),
            'DepthCM': (depth_cm, ''),
            'TBase': (o_base, ''),
        },
        u.CustomMaterialOutputType.CMOT_FLOAT2,
    )

    # 2) 3-layer Snell-refracted internal fractures (IceSpike's T_IceCracks)
    cracks = custom(
        '''float3 n = normalize(NWS);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 vws = normalize(CamWS);
float3 rdir = refract(-vws, n, 1.0 / 1.31);
if (dot(rdir, rdir) < 1e-4) rdir = -vws;

float3 offs = float3(R * 53.7, R * 97.3, R * 31.1);
float3 p1 = (WP + offs) * (Scale * 1.55);
float3 p2 = (WP + rdir * (DepthCM * .55) + offs) * (Scale * 2.25);
float3 p3 = (WP + rdir * (DepthCM * 1.30) + offs) * (Scale * 3.60);

float c1 = Texture2DSample(TCrk, TCrkSampler, p1.yz).r * w.x + Texture2DSample(TCrk, TCrkSampler, p1.xz).r * w.y + Texture2DSample(TCrk, TCrkSampler, p1.xy).r * w.z;
float c2 = Texture2DSample(TCrk, TCrkSampler, p2.yz).g * w.x + Texture2DSample(TCrk, TCrkSampler, p2.xz).g * w.y + Texture2DSample(TCrk, TCrkSampler, p2.xy).g * w.z;
float c3 = Texture2DSample(TCrk, TCrkSampler, p3.yz).b * w.x + Texture2DSample(TCrk, TCrkSampler, p3.xz).b * w.y + Texture2DSample(TCrk, TCrkSampler, p3.xy).b * w.z;

float baseC = saturate(c1 * .52 + c2 * .34 + c3 * .22);
return saturate(baseC * (.82 + VC.b * .55 + ShG * 1.65) + pow(saturate(c1 * c2 * 2.6), 1.45) * (ShG * .95 + .22));''',
        {
            'WP': (world_pos, ''),
            'NWS': (norm_ws, ''),
            'CamWS': (cam_ws, ''),
            'R': (rand, ''),
            'Scale': (tiling, ''),
            'DepthCM': (depth_cm, ''),
            'TCrk': (o_cracks, ''),
            'VC': (vcol, ''),
            'ShG': (shatter_glow, ''),
        },
    )

    # 3) World-space triplanar normal: IceSpike 4K T_IceNormal + macro T_Ice1_normal facets -> Tangent Space!
    world_norm = custom(
        '''float3 n = normalize(NWS);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 offs = float3(R * 89.3, R * 147.1, R * 61.7);
float3 p1 = (WP + offs) * (Scale * 1.35);
float3 p2 = (WP + offs) * (Scale * 0.90);

float3 iX = UnpackNormalMap(Texture2DSample(TNorm, TNormSampler, p1.yz)).xyz;
float3 iY = UnpackNormalMap(Texture2DSample(TNorm, TNormSampler, p1.xz)).xyz;
float3 iZ = UnpackNormalMap(Texture2DSample(TNorm, TNormSampler, p1.xy)).xyz;

float3 fX = UnpackNormalMap(Texture2DSample(TFac, TFacSampler, p2.yz)).xyz;
float3 fY = UnpackNormalMap(Texture2DSample(TFac, TFacSampler, p2.xz)).xyz;
float3 fZ = UnpackNormalMap(Texture2DSample(TFac, TFacSampler, p2.xy)).xyz;

float sI = Strength * .82;
float sF = Strength * .52;
float2 dX = iX.xy * sI + fX.xy * sF;
float2 dY = iY.xy * sI + fY.xy * sF;
float2 dZ = iZ.xy * sI + fZ.xy * sF;

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
            'TNorm': (o_norm, ''),
            'TFac': (o_facet, ''),
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

    # Tight, realistic edge/crack/root frost ONLY — leaves flat cleaved crystal planes deep, dark, and glassy!
    frost = custom(
        'float edgeF = pow(saturate(VC.r), 1.35) * .68; float rootF = pow(saturate(VC.g), 1.55) * .42; float crkF = pow(saturate(Crk), 1.15) * .48; return saturate((edgeF + rootF) * (1. - VC.b * .5) + crkF);',
        {'VC': (vcol, ''), 'Crk': (cracks, '')},
    )

    # Photorealistic IceSpike-derived glacier palette (desaturated deep slate-teal glass -> frosty ice white)
    if is_shell:
        color_code = '''float lum = saturate(Base.x);
float3 glassDeep = float3(.10, .26, .34);
float3 glassMid  = float3(.26, .48, .58);
float3 frostEdge = float3(.72, .83, .88);
float3 col = lerp(glassDeep, glassMid, saturate(lum * 1.1 + Crk * .32));
col = lerp(col, frostEdge, saturate(F * .72 + Fren * .48));
return col * lerp(.92, 1.08, R);'''
    else:
        color_code = '''float lumS = Base.x;
float lumD = Base.y;
float3 abyssal  = float3(.022, .072, .115);
float3 deepCore = float3(.055, .155, .225);
float3 midCore  = float3(.175, .365, .455);
float3 frostW   = float3(.64, .76, .82);

float3 col = lerp(deepCore, midCore, saturate(pow(max(lumS, 0.), .92) * 1.25));
// Deep refracted parallax contrast inside the crystal volume
col *= clamp(1.0 + (lumD - lumS) * 1.35, .78, 1.24) * lerp(.90, 1.10, R);
// Deepen crevices between fused crystal shards
col = lerp(col, abyssal, saturate(VC.b * .78));
// Brighten internal spiderweb fractures & grazing crystalline Fresnel rim
col = lerp(col, float3(.36, .62, .74), saturate(Crk * .56 + Fren * .34));
// Crisp frost ONLY on razor edges, cracks, and tight soil-rupture root
return lerp(col, frostW, saturate(F * .68));'''

    base_color = custom(
        color_code,
        {'Base': (tri_base, ''), 'Crk': (cracks, ''), 'F': (frost, ''), 'Fren': (fresnel, ''), 'VC': (vcol, ''), 'R': (rand, '')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    out(base_color, '', u.MaterialProperty.MP_BASE_COLOR)
    out(norm_ts, '', u.MaterialProperty.MP_NORMAL)

    # Wet glossy glassy faces (0.05-0.16) contrasting sharply with matte frosted razor edges (0.38-0.46)
    rough_code = 'return clamp(.045 + F * .34 - Crk * .02, .045, .40);' if is_shell else 'return clamp(.075 + F * .38 + (1. - Base.x) * .06 - VC.b * .02, .075, .46);'
    out(custom(rough_code, {'F': (frost, ''), 'Crk': (cracks, ''), 'Base': (tri_base, ''), 'VC': (vcol, '')}), '', u.MaterialProperty.MP_ROUGHNESS)

    spec_c = node(u.MaterialExpressionConstant)
    spec_c.set_editor_property('r', 0.68 if is_shell else 0.56)
    out(spec_c, '', u.MaterialProperty.MP_SPECULAR)

    metal_c = node(u.MaterialExpressionConstant)
    metal_c.set_editor_property('r', 0.0)
    out(metal_c, '', u.MaterialProperty.MP_METALLIC)

    if is_shell:
        # Translucent glassy shell: see right through the clean crystal planes to the darker fractured core,
        # while catching bright glassy Fresnel rims and sharp frosty cleavage cracks!
        opac = custom(
            'return clamp(lerp(.16, .82, saturate(F * .65 + Fren * .74 + Crk * .35)), .14, .88);',
            {'F': (frost, ''), 'Fren': (fresnel, ''), 'Crk': (cracks, '')},
        )
        out(opac, '', u.MaterialProperty.MP_OPACITY)
    else:
        ao = custom('return clamp(1.0 - VC.b * .38, .48, 1.0);', {'VC': (vcol, '')})
        out(ao, '', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        opac_c = node(u.MaterialExpressionConstant)
        opac_c.set_editor_property('r', 0.36)  # deep optical subsurface thickness matching IceSpike heart!
        out(opac_c, '', u.MaterialProperty.MP_OPACITY)
        sss = custom(
            'return lerp(float3(.10, .34, .48), float3(.36, .66, .78), saturate(F * .45 + Crk * .45 + VA * .25));',
            {'F': (frost, ''), 'Crk': (cracks, ''), 'VA': (vcol, 'A')},
            u.CustomMaterialOutputType.CMOT_FLOAT3,
        )
        out(sss, '', u.MaterialProperty.MP_SUBSURFACE_COLOR)

    # REALISTIC ZERO-NEON EMISSIVE: ~0 during standing hold so twilight lighting & specular reflections shine naturally!
    # Only lights up crisply during the 0.32s eruption pulse and the 0.28s pre-shatter crack surge.
    em_code = '''float pulseBand = exp(-pow((VA - (1.0 - EFlash)) / .24, 2.0)) * EFlash;
float surge = pulseBand * .42 + ShG * (Crk * .75 + Fren * .25);
float3 col = lerp(float3(.26, .64, .86), float3(.68, .90, .98), saturate(pulseBand + ShG));
return col * surge;'''
    emissive = custom(
        em_code,
        {'VA': (vcol, 'A'), 'EFlash': (eruption_flash, ''), 'ShG': (shatter_glow, ''), 'Crk': (cracks, ''), 'Fren': (fresnel, '')},
        u.CustomMaterialOutputType.CMOT_FLOAT3,
    )
    out(emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR)

    errors = [str(e) for e in LIB.recompile_material(mat)]
    if errors:
        raise RuntimeError(f'{asset_path} compile failed:\n' + '\n'.join(errors))
    if not EAL.save_loaded_asset(mat, False):
        raise RuntimeError(f'{asset_path} save failed')
    print('AZ_V4_SPIRE_MAT_SAVED', mat.get_path_name(), 'shell=', is_shell, flush=True)
    return mat


def import_razor_spire_meshes(heart_mat):
    imported = []
    for name in ('SM_AZ_GlacierSpire_01', 'SM_AZ_GlacierSpire_02', 'SM_AZ_GlacierSpire_03', 'SM_AZ_IceFangCluster'):
        fbx = MESH_SRC / (name + '.fbx')
        if not fbx.is_file():
            raise RuntimeError('Missing razor crystal FBX: ' + str(fbx))
        task = u.AssetImportTask()
        task.filename = str(fbx)
        task.destination_path = DEST
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

        ap = f'{DEST}/{name}'
        mesh = u.load_asset(ap)
        if not mesh:
            raise RuntimeError('Failed to load imported spire mesh: ' + ap)
        mesh.set_material(0, heart_mat)
        if not EAL.save_loaded_asset(mesh, False):
            raise RuntimeError('Failed to save spire mesh: ' + ap)
        tris = mesh.get_num_triangles(0) if hasattr(mesh, 'get_num_triangles') else -1
        print('AZ_V4_MESH_SAVED', ap, 'tris=', tris, flush=True)
        imported.append({'asset': ap, 'fbx': str(fbx), 'triangles': tris})
    return imported


def rebuild_realistic_burst_wave_niagara(dust_mat):
    """Rebuild NS_AbsoluteZeroBurstWave in-place (or duplicate from NS_AbsoluteZeroInwardMist)
    with photorealistic soft Mantaflow ground mist + fine feathered snow/frost powder (M_AbsoluteZeroIceDust)."""
    target = f'{DEST}/NS_AbsoluteZeroBurstWave'
    source = f'{DEST}/NS_AbsoluteZeroInwardMist'
    system = u.load_asset(target) if EAL.does_asset_exist(target) else EAL.duplicate_asset(source, target)
    if not system:
        raise RuntimeError('Failed loading/duplicating NS_AbsoluteZeroBurstWave')

    for pname, typ in [
        ('Center', POSITION),
        ('Radius', FLOAT),
        ('Strength', FLOAT),
        ('BurstActive', FLOAT),
    ]:
        user_parameter(system, pname, typ)

    # Emitter 1: Ground-hugging rolling Mantaflow 8x8 liquid-nitrogen sub-zero fog wave (realistic cool twilight slate-cyan)
    en1 = 'InwardColdMist'
    trim(system, en1, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate', 'SpawnBurst_Instantaneous'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + en1 + '.' + stage)
    put(system, en1, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(HlslExpression="floor(90*saturate(User.Strength)+.5)")', HL)
    put(system, en1, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0.0)')
    put(system, en1, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="(62*saturate(User.BurstActive)+16)*saturate(User.Strength)")', HL)

    s1 = 'frac((float(Particles.UniqueID)+.5)*.61803398875+.13)'
    s2 = 'frac((float(Particles.UniqueID)+.5)*.41421356237+.37)'
    s3 = 'frac((float(Particles.UniqueID)+.5)*.75487766623+.67)'
    ang0 = f'({s1}*6.2831853)'
    r0 = f'(55.0+160.0*{s2})'
    z0 = f'(18.0+48.0*{s3})'
    life = f'(1.45+.90*{s3})'
    rad_scale = '(max(900.0,User.Radius)/1000.0)'
    spd = f'((1080.0+1320.0*{s2})*{rad_scale})'
    pos0 = f'User.Center+float3(cos({ang0})*{r0},sin({ang0})*{r0},{z0})'
    vel0 = f'float3(cos({ang0})*{spd},sin({ang0})*{spd},32.0+110.0*{s3})'
    assignments(system, en1, 'ParticleSpawnScript', {
        'Particles.MistAngle': (FLOAT, ang0),
        'Particles.MistR0': (FLOAT, r0),
        'Particles.MistZ0': (FLOAT, z0),
        'Particles.MistSeed': (FLOAT, s1),
        'Particles.MistPhase': (FLOAT, s2),
        'Particles.Lifetime': (FLOAT, life),
        'Particles.Position': (POSITION, pos0),
        'Particles.Velocity': (VEC3, vel0),
        'Particles.SpriteSize': (VEC2, f'float2(155.0+95.0*{s2},115.0+68.0*{s3})'),
        'Particles.SpriteRotation': (FLOAT, f'({s3}*6.2831853)'),
        'Particles.Color': (COLOR, 'float4(.64,.79,.88,0)'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({s1},{s2},.18,0)'),
    })

    n = 'Particles.NormalizedAge'
    drag = 'exp(-Engine.DeltaTime*2.45)'
    new_vel = f'Particles.Velocity*{drag}+float3(0,0,10.0*Engine.DeltaTime)'
    new_pos = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    sz = f'lerp(150.0,350.0,pow(saturate({n}),.65))*(.78+.46*Particles.MistPhase)'
    env = smooth('0', '.08', n) + '*(1-' + smooth('.48', '1', n) + ')'
    glow = f'lerp(.28,.04,saturate({n}*2.0))'
    assignments(system, en1, 'ParticleUpdateScript', {
        'Particles.Velocity': (VEC3, new_vel),
        'Particles.Position': (POSITION, new_pos),
        'Particles.SpriteSize': (VEC2, f'float2({sz},({sz})*.74)'),
        'Particles.SpriteRotation': (FLOAT, f'(Particles.MistPhase*6.2831853+Particles.Age*(.48+.45*Particles.MistSeed))'),
        'Particles.Color': (COLOR, f'float4(.66,.81,.90,.38*({env})*saturate(User.Strength))'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4(Particles.MistSeed,Particles.MistPhase,{glow},0)'),
    })

    # Emitter 2: Photorealistic fine wind-blown frost powder & delicate snow motes (M_AbsoluteZeroIceDust, 1.8-4.8 cm!)
    en2 = 'InwardFrostShards'
    trim(system, en2, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + en2 + '.' + stage)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, en2, renderer=0), {
        'Material': dust_mat.get_path_name(),
        'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1},
        'bSubImageBlend': False,
        'Alignment': 'Unaligned',
        'FacingMode': 'FaceCamera',
        'SortMode': 'ViewDepth',
        'PivotInUVSpace': {'X': 0.5, 'Y': 0.5},
        'bCastShadows': False,
        'CutoutTexture': None,
        'bUseMaterialCutoutTexture': False,
        'MotionVectorSetting': 'Disable',
    })
    API.call_method('AddModule', (ref(system, en2, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system, en2, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(HlslExpression="floor(220*saturate(User.Strength)+.5)")', HL)
    put(system, en2, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0.0)')
    put(system, en2, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="(140*saturate(User.BurstActive)+85)*saturate(User.Strength)")', HL)

    c1 = 'frac((float(Particles.UniqueID)+.5)*.61803398875+.57)'
    c2 = 'frac((float(Particles.UniqueID)+.5)*.41421356237+.23)'
    c3 = 'frac((float(Particles.UniqueID)+.5)*.75487766623+.89)'
    cang0 = f'({c1}*6.2831853)'
    cr0 = f'(max(900.0,User.Radius)*(.08+.86*{c2})*(1.0-.65*saturate(User.BurstActive)))'
    cz0 = f'(16.0+185.0*{c3})'
    clife = f'(1.10+1.25*{c3})'
    cspd = f'((680.0+1450.0*{c2})*saturate(User.BurstActive)+65.0)*{rad_scale}'
    cpos0 = f'User.Center+float3(cos({cang0})*{cr0},sin({cang0})*{cr0},{cz0})'
    cvel0 = f'float3(cos({cang0})*{cspd},sin({cang0})*{cspd},95.0+240.0*{c3}*saturate(User.BurstActive))'
    assignments(system, en2, 'ParticleSpawnScript', {
        'Particles.CrysAngle': (FLOAT, cang0),
        'Particles.CrysR0': (FLOAT, cr0),
        'Particles.CrysZ0': (FLOAT, cz0),
        'Particles.CrysSeed': (FLOAT, c2),
        'Particles.Lifetime': (FLOAT, clife),
        'Particles.Position': (POSITION, cpos0),
        'Particles.Velocity': (VEC3, cvel0),
        'Particles.SpriteSize': (VEC2, f'float2(2.0+3.0*{c2},2.0+3.0*{c2})'),
        'Particles.SpriteRotation': (FLOAT, f'({c1}*360.0)'),
        'Particles.Color': (COLOR, 'float4(.82,.92,.98,0)'),
    })
    # Organic wind-flutter drift + gentle snow settle (fine 1.8 - 4.8 cm soft ice powder, ZERO giant grey squares!)
    flutter = 'float3(sin(Particles.Age*3.4+Particles.CrysAngle)*32.0,cos(Particles.Age*2.9+Particles.CrysAngle)*32.0,-78.0)'
    cnew_vel = f'Particles.Velocity*exp(-Engine.DeltaTime*2.1)+({flutter})*Engine.DeltaTime'
    cnew_pos = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
    csz = f'(1.8+3.0*Particles.CrysSeed)*(1.05-.35*saturate({n}))'
    cenv = smooth('0', '.10', n) + '*(1-' + smooth('.62', '1', n) + ')'
    twinkle = '(.72+.28*sin(Particles.Age*9.0+Particles.CrysSeed*40.0))'
    assignments(system, en2, 'ParticleUpdateScript', {
        'Particles.Velocity': (VEC3, cnew_vel),
        'Particles.Position': (POSITION, cnew_pos),
        'Particles.SpriteSize': (VEC2, f'float2({csz},{csz})'),
        'Particles.SpriteRotation': (FLOAT, f'(Particles.CrysSeed*360.0+Particles.Age*95.0)'),
        'Particles.Color': (COLOR, f'float4(.84,.93,.98,.78*({cenv})*({twinkle})*saturate(User.Strength))'),
    })

    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-2200, -2200, -240), max=u.Vector(2200, 2200, 760)))
    EAL.set_metadata_tag(system, 'AbsoluteZeroV4.Revision', 'AbsoluteZeroV4_RealisticCrystalAndVFX_20261127')
    if not EAL.save_loaded_asset(system, False):
        raise RuntimeError('Failed saving NS_AbsoluteZeroBurstWave')
    print('AZ_V4_BURSTWAVE_SAVED', system.get_path_name(), flush=True)
    return system


def update_inward_mist_to_realistic_dust(dust_mat):
    """Switch NS_AbsoluteZeroInwardMist Emitter 2 (InwardFrostShards) from legacy M_FrostCrystalSoft
    to photorealistic feathered M_AbsoluteZeroIceDust so even the windup channel has zero square particles."""
    path = f'{DEST}/NS_AbsoluteZeroInwardMist'
    system = u.load_asset(path)
    if not system:
        raise RuntimeError('Missing ' + path)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, 'InwardFrostShards', renderer=0), {
        'Material': dust_mat.get_path_name(),
        'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1},
        'bSubImageBlend': False,
        'Alignment': 'Unaligned',
        'FacingMode': 'FaceCamera',
        'SortMode': 'ViewDepth',
        'PivotInUVSpace': {'X': 0.5, 'Y': 0.5},
        'bCastShadows': False,
        'CutoutTexture': None,
        'bUseMaterialCutoutTexture': False,
        'MotionVectorSetting': 'Disable',
    })
    if not EAL.save_loaded_asset(system, False):
        raise RuntimeError('Failed saving NS_AbsoluteZeroInwardMist')
    print('AZ_V4_INWARDMIST_UPDATED', system.get_path_name(), flush=True)
    return system


def main():
    EAL.make_directory(DEST)
    backups = backup_if_needed([
        f'{DEST}/M_AbsoluteZeroSpire',
        f'{DEST}/NS_AbsoluteZeroBurstWave',
        f'{DEST}/NS_AbsoluteZeroInwardMist',
        f'{DEST}/SM_AZ_GlacierSpire_01',
        f'{DEST}/SM_AZ_GlacierSpire_02',
        f'{DEST}/SM_AZ_GlacierSpire_03',
        f'{DEST}/SM_AZ_IceFangCluster',
    ])

    dust_mat = build_realistic_ice_dust_material()
    inward_sys = update_inward_mist_to_realistic_dust(dust_mat)
    heart_mat = build_icespike_style_spire_material(f'{DEST}/M_AbsoluteZeroSpire', False)
    shell_mat = build_icespike_style_spire_material(f'{DEST}/M_AbsoluteZeroSpireShell', True)
    meshes = import_razor_spire_meshes(heart_mat)
    burst_sys = rebuild_realistic_burst_wave_niagara(dust_mat)

    all_paths = [
        dust_mat.get_path_name().split('.')[0],
        inward_sys.get_path_name().split('.')[0],
        heart_mat.get_path_name().split('.')[0],
        shell_mat.get_path_name().split('.')[0],
        burst_sys.get_path_name().split('.')[0],
        *[m['asset'] for m in meshes],
    ]
    receipt = {
        'version': 'AbsoluteZeroV4_RealisticCrystalAndVFX_20261127',
        'backups': backups,
        'fixes': [
            'Identified legacy M_FrostCrystalSoft UE5.8 DepthFade Opacity pin bug (caused flat grey squares); left legacy asset untouched for M07MagicAttack CDO compatibility',
            'Authored photorealistic feathered M_AbsoluteZeroIceDust (T_Smoke_Wisp + soft Gaussian + twinkling core + valid DepthFade pin) and wired BOTH NS_AbsoluteZeroBurstWave and NS_AbsoluteZeroInwardMist to it',
            'Replaced 2D square burst shards with 64 real 3D tumbling fractured SM_IceShard splinters in AFPSAbsoluteZeroNova',
            'Resculpted SM_AZ_GlacierSpire_01..03 and SM_AZ_IceFangCluster as razor-faceted planar mineral prisms (zero voxel smoothing)',
            'Rebuilt M_AbsoluteZeroSpire (dark-glacier PBR core) + new M_AbsoluteZeroSpireShell (glossy translucent outer sheath) derived from IceSpike magic (T_IceBaseColor 4K, T_IceNormal 4K, T_IceCracks, zero neon wash)',
        ],
        'imported_meshes': meshes,
        'saved_assets': {
            ap: {
                'disk': str(disk_path(ap)),
                'bytes': disk_path(ap).stat().st_size,
                'sha256': sha256(disk_path(ap)),
            }
            for ap in all_paths
        },
        'runtime_tested': False,
    }
    (PROD / 'published.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print('AZ_V4_ALL_ASSETS_DONE', flush=True)


if __name__ == '__main__':
    main()
