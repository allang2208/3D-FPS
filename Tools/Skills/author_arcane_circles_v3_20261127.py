"""Headless UE5 authoring script for Arcane Circles V3 (ThunderLance + AbsoluteZero, 2026-11-27).

Upgrades BOTH arcane circles from rudimentary 5-primitive polar math to razor-crisp, museum-grade
2048x2048 4-channel linear BC7 vector textures + 3-layer counter-rotation + travelling mana-current
pulse + sequential charge ignition + true 3D holographic parallax:
  1. Imports 2K 4-channel RGBA PNGs (4K supersampled -> Lanczos 2K, sRGB=False, TC_BC7, TA_CLAMP,
     TF_TRILINEAR, TMGS_Sharpen2, TEXTUREGROUP_Effects):
       - /Game/Skills/ElectricMagic/ThunderLanceV2/T_ThunderLanceArcaneV3
       - /Game/Skills/AbsoluteZero/T_AbsoluteZeroArcaneV3
  2. Rebuilds:
       - /Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle
       - /Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris (3D parallax secondary seal)
       - /Game/Skills/AbsoluteZero/M_AbsoluteZeroSigil (5.2m ground glacial astrolabe)
  3. Preserves:
       - Strict 100% clean central aiming/foot aperture (r < 0.562 ThunderLance, rn < 0.482 AbsoluteZero)
       - Organic Blue / Violet / Cyan non-repeating random color walk via ColorSeed
       - MATUSAGE_INSTANCED_STATIC_MESHES + PerInstanceCustomData on M_ThunderLanceIris for Lance Column
  4. Saves pre-edit backups and full SHA-256 receipt to:
       F:/FPSGAMEData/ArtProduction/Skills/ArcaneCirclesV3-20261127/
"""
import hashlib
import json
import os
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
SRC_TEX = ROOT / 'SourceAssets/ArcaneCirclesV3_20261127'
RAY_ROOT = ROOT / 'SourceAssets/ThunderLanceRay20261005'
AZ_ROOT = ROOT / 'SourceAssets/AbsoluteZeroV2_20261126'
PROD = Path('F:/FPSGAMEData/ArtProduction/Skills/ArcaneCirclesV3-20261127')
BEFORE = PROD / 'Before'
BEFORE.mkdir(parents=True, exist_ok=True)

EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary

TEXTURE_SPECS = [
    (SRC_TEX / 'T_ThunderLanceArcaneV3.png', '/Game/Skills/ElectricMagic/ThunderLanceV2', 'T_ThunderLanceArcaneV3'),
    (SRC_TEX / 'T_AbsoluteZeroArcaneV3.png', '/Game/Skills/AbsoluteZero', 'T_AbsoluteZeroArcaneV3'),
]

MATERIAL_TARGETS = [
    '/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle',
    '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris',
    '/Game/Skills/AbsoluteZero/M_AbsoluteZeroSigil',
]

ALL_TARGETS = [f'{dest}/{name}' for _, dest, name in TEXTURE_SPECS] + MATERIAL_TARGETS


def disk_path(asset_path: str) -> Path:
    return ROOT / 'Content' / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_targets():
    out = {}
    for ap in ALL_TARGETS:
        src = disk_path(ap)
        dst = BEFORE / (ap.split('/')[-1] + '.uasset')
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
        out[ap] = str(dst) if dst.is_file() else None
    return out


def clear_expressions(mat):
    for old in list(LIB.get_material_expressions(mat)):
        LIB.delete_material_expression(mat, old)


def save_asset(asset):
    if isinstance(asset, u.Material):
        errors = [str(e) for e in LIB.recompile_material(asset)]
        if errors:
            raise RuntimeError(f'Material compile failed {asset.get_path_name()}: {errors}')
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError(f'Save failed {asset.get_path_name()}')
    print('ARCANE_CIRCLE_V3_SAVED', asset.get_path_name(), flush=True)


def import_linear_arcane_texture(png_path: Path, dest_folder: str, asset_name: str):
    if not png_path.is_file():
        raise RuntimeError(f'Missing source PNG: {png_path}')
    asset_path = f'{dest_folder}/{asset_name}'
    task = u.AssetImportTask()
    task.filename = str(png_path)
    task.destination_path = dest_folder
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    tex = EAL.load_asset(asset_path)
    if not tex:
        raise RuntimeError(f'Failed to load imported texture: {asset_path}')

    # Linear 4-channel BC7, clamped edges (zero wrap bleed on UV rotation), crisp trilinear + Sharpen2 mips.
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
    tex.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
    tex.set_editor_property('filter', u.TextureFilter.TF_TRILINEAR)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_EFFECTS)
    tex.set_editor_property('max_texture_size', 2048)
    tex.set_editor_property('never_stream', True)
    # Try UE5.8 sharp mip enum gracefully
    for enum_name in ('TMGS_SHARPEN2', 'TMGS_SHARPEN_2', 'TMGS_SHARPEN1', 'TMGS_FROM_TEXTURE_GROUP'):
        if hasattr(u.TextureMipGenSettings, enum_name):
            tex.set_editor_property('mip_gen_settings', getattr(u.TextureMipGenSettings, enum_name))
            print(f'TEX_MIP_SETTING {asset_name} -> {enum_name}', flush=True)
            break
    EAL.set_metadata_tag(tex, 'ArcaneCirclesV3.Revision', 'ArcaneCirclesV3_20261127')
    save_asset(tex)
    return tex


def rebuild_thunder_circle(tex_thunder):
    path = '/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle'
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing ' + path)
    clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('enable_responsive_aa', True)
    mat.set_editor_property('output_translucent_velocity', True)

    def node(cls, **props):
        n = LIB.create_material_expression(mat, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    uv = node(u.MaterialExpressionTextureCoordinate)
    time = node(u.MaterialExpressionTime)
    charge = node(u.MaterialExpressionScalarParameter, parameter_name='Charge', default_value=0.0)
    seed = node(u.MaterialExpressionScalarParameter, parameter_name='ColorSeed', default_value=0.0)
    tex_obj = node(u.MaterialExpressionTextureObject)
    tex_obj.set_editor_property('texture', tex_thunder)

    # 3-layer counter-rotating 2K vector arcane circle with strict r < 0.562 glass-clear aim aperture,
    # sequential rune ignition, travelling dual-helix energy current, white-hot engraved core + tight
    # Blue/Violet/Cyan chromatic halo (band-isolated glow -> ZERO counter-rotation ghosting!).
    code = '''
float2 p = (UV - 0.5) * 2.0;
float r = length(p), a = atan2(p.y, p.x), c = saturate(Charge);

// Strict glass-clear central aiming aperture: r < 0.562 is 100% zero opacity!
float centerClear = smoothstep(0.560, 0.574, r);
float outerClip   = step(r, 0.994) * (1.0 - smoothstep(0.978, 0.994, r));
float validMask   = centerClear * outerClip;

// 3 independent counter-rotating arcane layers.
float rate  = 1.0 + c * 0.85;
float aOut  = Time * 0.24 * rate;
float aRune = -Time * 0.36 * rate;
float aIn   = Time * 0.14 * rate;

float cO = cos(aOut),  sO = sin(aOut);
float cR = cos(aRune), sR = sin(aRune);
float cI = cos(aIn),   sI = sin(aIn);

// Subtle charge-breathing micro-contraction on inner aim-window filigree (never crosses r < 0.565!).
float2 pIn = p * (1.0 + 0.012 * c * sin(Time * 2.6));
float2 uvOut  = 0.5 + 0.5 * float2(p.x * cO - p.y * sO, p.x * sO + p.y * cO);
float2 uvRune = 0.5 + 0.5 * float2(p.x * cR - p.y * sR, p.x * sR + p.y * cR);
float2 uvIn   = 0.5 + 0.5 * float2(pIn.x * cI - pIn.y * sI, pIn.x * sI + pIn.y * cI);

float4 texOut  = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvOut);
float4 texRune = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvRune);
float4 texIn   = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvIn);

// Band masks matching generate_arcane_circle_textures_v3.py band_splits=(0.682, 0.870).
float mIn   = 1.0 - smoothstep(0.674, 0.690, r);
float mOut  = smoothstep(0.862, 0.878, r);
float mRune = smoothstep(0.674, 0.690, r) * (1.0 - smoothstep(0.862, 0.878, r));

// Sequential charge ignition: outer astrolabe & inner sight lip ignite first; 24 runes sweep on with Charge.
float ignOut  = lerp(0.58, 1.0, smoothstep(0.00, 0.26, c));
float ignIn   = lerp(0.52, 1.0, smoothstep(0.04, 0.36, c));
float aNorm   = frac((a + 3.14159265) / 6.2831853 + Time * 0.09);
float ignRune = lerp(0.30, 1.0, smoothstep(aNorm - 0.22, aNorm + 0.05, c * 1.24 + 0.16));

float coreOut  = texOut.r  * ignOut;
float coreRune = texRune.g * ignRune;
float coreIn   = texIn.b   * ignIn;
float coreMask = saturate(max(max(coreOut, coreRune), coreIn));
float glowMask = saturate(texOut.a * mOut * ignOut + texRune.a * mRune * ignRune + texIn.a * mIn * ignIn);

// Travelling dual-helix high-voltage mana current along the strokes.
float wave1 = pow(saturate(0.5 + 0.5 * cos(a * 3.0 - Time * (3.6 + 2.8 * c))), 4.0);
float wave2 = pow(saturate(0.5 + 0.5 * cos(a * 6.0 + Time * (2.4 + 2.0 * c))), 5.0);
float energyFlow = 1.0 + (wave1 * 0.56 + wave2 * 0.36) * (0.32 + 0.68 * c);

// Organic non-repeating random color walk across Electric Blue / Arcane Violet / Aurora Cyan.
float3 cBlue   = float3(0.16, 0.52, 1.00);
float3 cViolet = float3(0.68, 0.24, 1.00);
float3 cCyan   = float3(0.08, 0.94, 1.00);

float tWalk = Time * 1.15 + ColorSeed * 1.73;
float seg = floor(tWalk);
float fracT = smoothstep(0.08, 0.92, frac(tWalk));
float h0 = frac(sin(seg * 127.1 + ColorSeed * 311.7) * 43758.5453);
float h1 = frac(sin((seg + 1.0) * 127.1 + ColorSeed * 311.7) * 43758.5453);
float i0 = floor(min(2.999, h0 * 3.0));
float i1 = floor(min(2.999, h1 * 3.0));
if (abs(i1 - i0) < 0.5) i1 = fmod(i0 + 1.0 + floor(frac(h1 * 7.3) * 2.0), 3.0);
float3 colA = (i0 < 0.5) ? cBlue : ((i0 < 1.5) ? cViolet : cCyan);
float3 colB = (i1 < 0.5) ? cBlue : ((i1 < 1.5) ? cViolet : cCyan);
float3 primaryCol = lerp(colA, colB, fracT);

float tWalk2 = tWalk + 0.42 + 0.16 * sin(a * 2.0 - Time * 1.4);
float seg2 = floor(tWalk2);
float fracT2 = smoothstep(0.08, 0.92, frac(tWalk2));
float h2a = frac(sin(seg2 * 127.1 + ColorSeed * 311.7) * 43758.5453);
float h2b = frac(sin((seg2 + 1.0) * 127.1 + ColorSeed * 311.7) * 43758.5453);
float j0 = floor(min(2.999, h2a * 3.0));
float j1 = floor(min(2.999, h2b * 3.0));
if (abs(j1 - j0) < 0.5) j1 = fmod(j0 + 1.0, 3.0);
float3 accA = (j0 < 0.5) ? cBlue : ((j0 < 1.5) ? cViolet : cCyan);
float3 accB = (j1 < 0.5) ? cBlue : ((j1 < 1.5) ? cViolet : cCyan);
float3 accentCol = lerp(accA, accB, fracT2);

float3 innerTint = lerp(primaryCol, accentCol, 0.55);
float wSum = max(0.001, coreOut + coreRune + coreIn);
float3 strokeChroma = (primaryCol * coreOut + accentCol * coreRune + innerTint * coreIn) / wSum;
float3 auraChroma = lerp(primaryCol, accentCol, mRune * 0.72 + mIn * 0.42);

// Razor-sharp white-hot engraved core inside vibrant Blue/Violet/Cyan stroke aura.
float3 hotCore = lerp(strokeChroma, float3(0.95, 0.98, 1.0), pow(coreMask, 1.08) * (0.42 + 0.30 * c));
float3 finalRgb = lerp(auraChroma * 1.15, hotCore * 1.38, saturate(coreMask * 1.35));

float gain = (3.3 + 1.65 * c) * energyFlow;
float op = saturate(coreMask * 0.90 + glowMask * 0.34) * lerp(0.42, 0.66, c) * validMask;
return float4(finalRgb * gain, op);
'''
    custom = node(u.MaterialExpressionCustom, description='ThunderLanceCircle.ArcaneV3',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4, code=code)
    inputs = {'UV': uv, 'Time': time, 'Charge': charge, 'ColorSeed': seed, 'ArcaneTex': tex_obj}
    pins = []
    for name in inputs:
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    custom.set_editor_property('inputs', pins)
    for name, expr in inputs.items():
        if not LIB.connect_material_expressions(expr, '', custom, name):
            raise RuntimeError('Circle input ' + name)

    rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    LIB.connect_material_expressions(custom, '', rgb, str(LIB.get_material_expression_input_names(rgb)[0]))
    LIB.connect_material_expressions(custom, '', alpha, str(LIB.get_material_expression_input_names(alpha)[0]))
    LIB.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
    EAL.set_metadata_tag(mat, 'ArcaneCirclesV3.Revision', 'ArcaneCirclesV3_20261127')
    save_asset(mat)
    return mat


def rebuild_thunder_iris(tex_thunder):
    path = '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris'
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing ' + path)
    clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    def node(cls, **props):
        n = LIB.create_material_expression(mat, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def wire(a, b, pin):
        if isinstance(pin, int):
            pin = str(LIB.get_material_expression_input_names(b)[pin])
        if not LIB.connect_material_expressions(a, '', b, pin):
            raise RuntimeError('Iris wire failed ' + str(pin))

    data = node(u.MaterialExpressionPerInstanceCustomData, data_index=0, const_default_value=1.0)
    interp = node(u.MaterialExpressionVertexInterpolator)
    wire(data, interp, 0)
    tex_obj = node(u.MaterialExpressionTextureObject)
    tex_obj.set_editor_property('texture', tex_thunder)

    inputs = {
        'UV': node(u.MaterialExpressionTextureCoordinate),
        'Strength': node(u.MaterialExpressionScalarParameter, parameter_name='Strength', default_value=0.0),
        'Clock': node(u.MaterialExpressionScalarParameter, parameter_name='Clock', default_value=0.0),
        'FirePower': node(u.MaterialExpressionScalarParameter, parameter_name='FirePower', default_value=0.0),
        'ColorSeed': node(u.MaterialExpressionScalarParameter, parameter_name='ColorSeed', default_value=0.0),
        'Exposure': node(u.MaterialExpressionEyeAdaptation),
        'InstanceAlpha': interp,
        'ArcaneTex': tex_obj,
    }
    custom = node(u.MaterialExpressionCustom, description='ThunderLanceIris.ArcaneV3',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
                  code=(RAY_ROOT / 'Authoring/LanceIris.hlsl').read_text(encoding='utf-8'))
    pins = []
    for k in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', k); pins.append(p)
    custom.set_editor_property('inputs', pins)
    for k, src in inputs.items():
        wire(src, custom, k)

    rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(custom, rgb, 0)
    wire(custom, alpha, 0)
    fade = node(u.MaterialExpressionDepthFade, fade_distance_default=0.35)
    wire(alpha, fade, 0)
    LIB.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    EAL.set_metadata_tag(mat, 'ArcaneCirclesV3.Revision', 'ArcaneCirclesV3_20261127')
    save_asset(mat)
    return mat


def rebuild_absolute_zero_sigil(tex_az):
    path = '/Game/Skills/AbsoluteZero/M_AbsoluteZeroSigil'
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing ' + path)
    clear_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('material_domain', u.MaterialDomain.MD_SURFACE)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('output_translucent_velocity', False)
    mat.set_editor_property('is_translucency_velocity_from_depth', False)
    mat.set_editor_property('allow_front_layer_translucency', False)
    mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)

    def node(cls, **props):
        n = LIB.create_material_expression(mat, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def wire(a, b, pin):
        if isinstance(pin, int):
            pin = str(LIB.get_material_expression_input_names(b)[pin])
        if not LIB.connect_material_expressions(a, '', b, pin):
            raise RuntimeError('Sigil wire failed ' + str(pin))

    uv = node(u.MaterialExpressionTextureCoordinate)
    tm = node(u.MaterialExpressionTime)
    progress = node(u.MaterialExpressionScalarParameter, parameter_name='Progress', default_value=0.5)
    fade = node(u.MaterialExpressionScalarParameter, parameter_name='Fade', default_value=1.0)
    synergy = node(u.MaterialExpressionScalarParameter, parameter_name='Synergy', default_value=0.0)
    seed = node(u.MaterialExpressionScalarParameter, parameter_name='ColorSeed', default_value=0.0)
    tex_obj = node(u.MaterialExpressionTextureObject)
    tex_obj.set_editor_property('texture', tex_az)

    hlsl = (AZ_ROOT / 'AbsoluteZeroSigil.hlsl').read_text(encoding='utf-8')
    packed = node(u.MaterialExpressionCustom, description='AbsoluteZeroSigil.ArcaneV3',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4, code=hlsl)
    inputs = {
        'UV': uv, 'Time': tm, 'Progress': progress, 'Fade': fade,
        'Synergy': synergy, 'ColorSeed': seed, 'ArcaneTex': tex_obj,
    }
    pins = []
    for k in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', k); pins.append(p)
    packed.set_editor_property('inputs', pins)
    for k, src in inputs.items():
        wire(src, packed, k)

    em_rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    op_raw = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(packed, em_rgb, 0)
    wire(packed, op_raw, 0)

    df = node(u.MaterialExpressionDepthFade, fade_distance_default=8.0)
    wire(op_raw, df, 0)
    LIB.connect_material_property(em_rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(df, '', u.MaterialProperty.MP_OPACITY)
    EAL.set_metadata_tag(mat, 'ArcaneCirclesV3.Revision', 'ArcaneCirclesV3_20261127')
    save_asset(mat)
    return mat


def main():
    if os.environ.get('ARCANE_V3_NEVER_STREAM_ONLY') == '1':
        for _, dest, name in TEXTURE_SPECS:
            ap = f'{dest}/{name}'
            tex = EAL.load_asset(ap)
            if not tex:
                raise RuntimeError('Missing texture: ' + ap)
            tex.set_editor_property('never_stream', True)
            save_asset(tex)
            print('NEVER_STREAM_VERIFIED', ap, bool(tex.get_editor_property('never_stream')), flush=True)
        rp = PROD / 'published.json'
        receipt = json.loads(rp.read_text(encoding='utf-8')) if rp.is_file() else {'version': 'ArcaneCirclesV3_20261127', 'saved_assets': {}}
        for ap in ALL_TARGETS:
            dp = disk_path(ap)
            if not dp.is_file():
                raise RuntimeError('Missing saved asset: ' + str(dp))
            receipt['saved_assets'][ap] = {'disk': str(dp), 'bytes': dp.stat().st_size, 'sha256': sha256(dp)}
        receipt['never_stream'] = True
        rp.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
        print('ARCANE_CIRCLES_V3_NEVER_STREAM_PASS', str(rp), flush=True)
        return

    backups = backup_targets()
    tex_thunder = import_linear_arcane_texture(*TEXTURE_SPECS[0])
    tex_az = import_linear_arcane_texture(*TEXTURE_SPECS[1])

    rebuild_thunder_circle(tex_thunder)
    rebuild_thunder_iris(tex_thunder)
    rebuild_absolute_zero_sigil(tex_az)

    # Also log SM_ThunderLanceIris bounds so we verify 3D parallax radius exactness!
    iris_mesh = EAL.load_asset('/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceIris')
    iris_bounds = None
    if iris_mesh:
        try:
            b = iris_mesh.get_bounds()
            iris_bounds = {
                'origin': [float(b.origin.x), float(b.origin.y), float(b.origin.z)],
                'extent': [float(b.box_extent.x), float(b.box_extent.y), float(b.box_extent.z)],
                'sphere_radius': float(b.sphere_radius),
            }
        except Exception:
            bb = iris_mesh.get_bounding_box()
            iris_bounds = {
                'min': [float(bb.min.x), float(bb.min.y), float(bb.min.z)],
                'max': [float(bb.max.x), float(bb.max.y), float(bb.max.z)],
            }
        print('SM_THUNDER_LANCE_IRIS_BOUNDS', json.dumps(iris_bounds), flush=True)

    saved = {}
    for ap in ALL_TARGETS:
        dp = disk_path(ap)
        if not dp.is_file():
            raise RuntimeError('Missing saved asset: ' + str(dp))
        saved[ap] = {'disk': str(dp), 'bytes': dp.stat().st_size, 'sha256': sha256(dp)}

    source_pngs = {}
    for png, _, name in TEXTURE_SPECS:
        source_pngs[name] = {'disk': str(png), 'bytes': png.stat().st_size, 'sha256': sha256(png)}

    receipt = {
        'version': 'ArcaneCirclesV3_20261127',
        'backups': backups,
        'source_pngs': source_pngs,
        'saved_assets': saved,
        'iris_mesh_bounds': iris_bounds,
        'design': {
            'thunder_lance': '2K 4-ch BC7 vector arcane astrolabe + 12-pt lightning hexagram + 24 bespoke calligraphic runes + inner sight filigree, band-isolated co-rotating glow, strict r<0.562 clean aim aperture, dual-helix mana current, sequential charge ignition, 3D holographic parallax ChargeIris (+16cm forward), organic Blue/Violet/Cyan random walk',
            'absolute_zero': '2K 4-ch BC7 vector glacial astrolabe + 8-pt octagram + 16 branching snowflake dendrites + 32 bespoke frost runes + inner frost-lotus lattice, band-isolated co-rotating glow, strict rn<0.482 clean center, 64x9 terrain-conforming 5.2m ground disc, IceArmor synergy boost, replicated NetSigilColorSeed Blue/Violet/Cyan random walk',
        },
        'runtime_tested': False,
    }
    PROD.mkdir(parents=True, exist_ok=True)
    rp = PROD / 'published.json'
    rp.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print('ARCANE_CIRCLES_V3_ALL_PASS', str(rp), 'count=', len(saved), flush=True)


if __name__ == '__main__':
    main()
