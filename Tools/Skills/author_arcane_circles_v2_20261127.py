"""Headless UE5 authoring script for Arcane Circles V2 (ThunderLance + AbsoluteZero, 2026-11-27).

Applies the unified "Enlarged Clean-Aperture + Organic Blue/Violet/Cyan Random Color Flow" design to BOTH:
  1. ThunderLance Charge Assembly (/Game/Skills/ElectricMagic/):
     - M_ThunderLanceCircle: r < 0.58 strictly 0 opacity (glass-clear aim window), grand counter-rotating
       arcane runes/ticks/diamonds on r in [0.64, 0.96], smooth non-repeating Blue/Violet/Cyan random walk
       driven by (Time + ColorSeed) + dual-ring iridescent accent shimmer.
     - M_ThunderLanceIris: adds ColorSeed input & strict hollow aperture (r < 0.52 zero opacity) from LanceIris.hlsl.
     - NS_ThunderLanceGather: peripheral outer-ring particles (r = 32..46 cm, fading cleanly before r = 24 cm)
       with organic Blue/Violet/Cyan per-particle hue variety so nothing crowds the crosshair center.
     - NS_ThunderCharge: removes blinding center EnergyCore fog ball; keeps subtle crisp staff-tip sparks/rings
       with Blue/Violet/Cyan color variety.
  2. AbsoluteZero Ground Casting Sigil (/Game/Skills/AbsoluteZero/M_AbsoluteZeroSigil):
     - Rebuilt from upgraded AbsoluteZeroSigil.hlsl with ColorSeed scalar parameter:
       enlarged 5.2 m terrain-conforming ring with clean unobstructed center (rn < 0.48 strictly zero),
       grand outer frost runes & 8-point crystalline crown on rn in [0.56, 0.96], and matching organic
       Blue/Violet/Cyan random color walk.

Saves pre-edit backups and full SHA-256 receipt to:
  F:/FPSGAMEData/ArtProduction/Skills/ArcaneCirclesV2-20261127/
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
RAY_ROOT = ROOT / 'SourceAssets/ThunderLanceRay20261005'
AZ_ROOT = ROOT / 'SourceAssets/AbsoluteZeroV2_20261126'
PROD = Path('F:/FPSGAMEData/ArtProduction/Skills/ArcaneCirclesV2-20261127')
BEFORE = PROD / 'Before'
BEFORE.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import expression

EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
SEED = 'frac(float(Particles.UniqueID)*.618033989)'
SEED2 = 'frac(float(Particles.UniqueID)*.754877666)'
SEED3 = 'frac(float(Particles.UniqueID)*.569840296)'
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
TEMPLATE = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'

TARGETS = [
    '/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle',
    '/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris',
    '/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather',
    '/Game/Skills/ElectricMagic/NS_ThunderCharge',
    '/Game/Skills/AbsoluteZero/M_AbsoluteZeroSigil',
]


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
    for ap in TARGETS:
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
    elif isinstance(asset, u.NiagaraSystem):
        if not u.RainAssetEditor.compile_rain(asset):
            raise RuntimeError(f'Niagara compile failed {asset.get_path_name()}')
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError(f'Save failed {asset.get_path_name()}')
    print('ARCANE_CIRCLE_V2_SAVED', asset.get_path_name(), flush=True)


def rebuild_thunder_circle():
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

    # Single Float4 Custom returns (emissive.rgb, opacity) with strict r < 0.58 glass-clear aim aperture
    # and organic non-repeating Blue / Violet / Cyan random color walk.
    code = '''
float2 p = (UV - 0.5) * 2.0;
float r = length(p), a = atan2(p.y, p.x), c = saturate(Charge);
float aa = max(fwidth(r) * 1.35, 0.003);

// Strict clean central aiming aperture: r < 0.58 is 100% transparent!
float centerClear = smoothstep(0.56, 0.64, r);
float outerFade   = pow(saturate(1.0 - smoothstep(0.86, 1.00, r)), 1.35);
float rimMask     = centerClear * outerFade;

// Counter-rotating arcane rune rings pushed to outer peripheral band r in [0.64, 0.96].
float rate = 1.0 + c * 0.75;
float turn = a - Time * 0.36 * rate;
float back = a + Time * 0.28 * rate;

float outerRing = 1.0 - smoothstep(0.012, 0.012 + aa * 1.6, abs(r - 0.925));
float midRing   = 1.0 - smoothstep(0.010, 0.010 + aa * 1.5, abs(r - 0.675));
float aimLip    = (1.0 - smoothstep(0.007, 0.007 + aa * 1.5, abs(r - (0.635 - 0.018 * c))))
                  * (0.35 + 0.65 * pow(saturate(0.5 + 0.5 * cos(turn * 8.0)), 8.0));

float notches = pow(saturate(0.5 + 0.5 * cos(turn * 28.0)), 15.0);
float ticks   = notches * (1.0 - smoothstep(0.022, 0.022 + aa * 1.4, abs(r - 0.870)));

float q = abs(frac((back + 3.14159265) * 12.0 / 6.2831853) - 0.5);
float stave   = (1.0 - smoothstep(0.018, 0.036, q)) * (1.0 - smoothstep(0.044, 0.044 + aa * 1.4, abs(r - 0.785)));
float diamond = (1.0 - smoothstep(0.012, 0.012 + aa * 1.4, abs(abs(r - 0.785) + q * 0.30 - 0.048)))
                * (1.0 - smoothstep(0.14, 0.19, q));

// Sweeping 6-point peripheral lightning crest confined strictly to outer band [0.68, 0.91].
float arcR = lerp(0.69, 0.90, pow(abs(cos(turn * 3.0)), 2.2));
float arcCrest = (1.0 - smoothstep(0.009, 0.009 + aa * 1.5, abs(r - arcR))) * (0.42 + 0.58 * c);

float outerGrp = saturate(outerRing * 0.85 + ticks * 0.68 + arcCrest * 0.72);
float innerGrp = saturate(midRing * 0.78 + aimLip * 0.65 + stave * 0.72 + diamond * 0.82);
float pattern  = saturate(outerGrp + innerGrp);
float halo     = exp(-pow((r - 0.79) / 0.10, 2.0)) * (0.09 + 0.07 * c) * rimMask;

// Organic non-repeating random color walk across Blue / Violet / Cyan.
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

float blend = saturate(innerGrp / max(0.001, outerGrp + innerGrp));
float3 chroma = lerp(primaryCol, accentCol, blend * 0.72);
float3 finalRgb = lerp(chroma, float3(0.92, 0.97, 1.0), saturate(pattern * (0.14 + 0.28 * c)));

float pulse = 0.93 + 0.07 * sin(Time * 3.6 + a * 2.0);
float op = (pattern * rimMask + halo) * lerp(0.36, 0.56, c) * pulse;
return float4(finalRgb * (3.6 + 1.4 * c), op);
'''
    custom = node(u.MaterialExpressionCustom, description='ThunderLanceCircle.ApertureV2',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4, code=code)
    pins = []
    for name in ('UV', 'Time', 'Charge', 'ColorSeed'):
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    custom.set_editor_property('inputs', pins)
    for name, expr in (('UV', uv), ('Time', time), ('Charge', charge), ('ColorSeed', seed)):
        if not LIB.connect_material_expressions(expr, '', custom, name):
            raise RuntimeError('Circle input ' + name)

    rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    LIB.connect_material_expressions(custom, '', rgb, str(LIB.get_material_expression_input_names(rgb)[0]))
    LIB.connect_material_expressions(custom, '', alpha, str(LIB.get_material_expression_input_names(alpha)[0]))
    LIB.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
    EAL.set_metadata_tag(mat, 'ArcaneCirclesV2.Revision', 'ArcaneCirclesV2_20261127')
    save_asset(mat)
    return mat


def rebuild_thunder_iris():
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
    inputs = {
        'UV': node(u.MaterialExpressionTextureCoordinate),
        'Strength': node(u.MaterialExpressionScalarParameter, parameter_name='Strength', default_value=0.0),
        'Clock': node(u.MaterialExpressionScalarParameter, parameter_name='Clock', default_value=0.0),
        'FirePower': node(u.MaterialExpressionScalarParameter, parameter_name='FirePower', default_value=0.0),
        'ColorSeed': node(u.MaterialExpressionScalarParameter, parameter_name='ColorSeed', default_value=0.0),
        'Exposure': node(u.MaterialExpressionEyeAdaptation),
        'InstanceAlpha': interp,
    }
    custom = node(u.MaterialExpressionCustom, description='ThunderLanceIris.ApertureV2',
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
    EAL.set_metadata_tag(mat, 'ArcaneCirclesV2.Revision', 'ArcaneCirclesV2_20261127')
    save_asset(mat)
    return mat


def rebuild_thunder_gather():
    path = '/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather'
    system = u.load_asset(path)
    speck = u.load_asset('/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceGatherSpeck')
    streak = u.load_asset('/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceGatherStreak')
    if not system or not speck or not streak:
        raise RuntimeError('Missing Gather assets')

    # Outer peripheral ring orbits (r = 25..44 cm) with Blue/Violet/Cyan palette — zero center clutter!
    recipes = [
        ('GatheringSparks', 48, 0.44, 46.0, 26.0, 2.8, 2.4, speck),
        ('ChargingFilaments', 16, 0.30, 44.0, 27.0, 12.0, 1.6, streak),
        ('GatheringRings', 20, 0.36, 38.0, 25.0, 1.9, 1.9, speck),
    ]
    for name, rate, life, r_outer, r_inner, length, width, mat in recipes:
        trim(system, name, {'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
                            'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
                {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
            'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
            'Alignment': 'VelocityAligned' if name == 'ChargingFilaments' else 'Unaligned',
            'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth', 'bCastShadows': False, 'MotionVectorSetting': 'Disable',
            'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'SubImageSize': {'X': 1, 'Y': 1}})
        expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
                   f'{rate}*(.30+.70*saturate(User.Charge))')
        age = 'saturate(Particles.NormalizedAge)'
        charge = 'saturate(User.Charge)'
        theta = f'({SEED}*6.2831853+Particles.Age*(3.4+{charge}*3.8))'
        radius = f'lerp({r_outer},{r_inner},pow({age},1.35))*(.92+.16*{charge})'
        position = f'float3(0.5,cos({theta})*{radius},sin({theta})*{radius})'
        velocity = f'float3(0.0,-sin({theta}),cos({theta}))*120.0'
        size = f'float2({width},{length})*(.72+.28*{charge})*(1.0-.32*{age})'
        edge_fade = f'saturate({age}*4.5)*pow(saturate((1.0-{age})*2.8),1.4)'
        alpha = f'(.18+.22*{charge})*{edge_fade}'
        # Organic per-particle Blue / Violet / Cyan color shifting
        hue_mix = f'frac({SEED2}+Particles.Age*0.65)'
        cr = f'lerp(lerp(.16,.68,saturate({hue_mix}*3.0)),.08,saturate(({hue_mix}-.50)*2.5))'
        cg = f'lerp(lerp(.52,.24,saturate({hue_mix}*3.0)),.94,saturate(({hue_mix}-.50)*2.5))'
        color = f'float4({cr},{cg},1.0,{alpha})'
        values = {'Particles.Lifetime': (FLOAT, str(life)), 'Particles.Position': (POSITION, position),
                  'Particles.Velocity': (VEC3, velocity), 'Particles.SpriteSize': (VEC2, size),
                  'Particles.Color': (COLOR, color), 'Particles.SpriteRotation': (FLOAT, '0'),
                  'Particles.SubImageIndex': (FLOAT, '0')}
        assignments(system, name, 'ParticleSpawnScript', values)
        assignments(system, name, 'ParticleUpdateScript', {k: v for k, v in values.items() if k != 'Particles.Lifetime'})
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-65, -65, -65), max=u.Vector(65, 65, 65)))
    EAL.set_metadata_tag(system, 'ArcaneCirclesV2.Revision', 'ArcaneCirclesV2_20261127')
    save_asset(system)
    return system


def rebuild_thunder_charge():
    path = '/Game/Skills/ElectricMagic/NS_ThunderCharge'
    system = u.load_asset(path)
    if not system:
        raise RuntimeError('Missing ' + path)
    spark = u.load_asset('/Game/Skills/ElectricMagic/M_ElectricSpark')
    filament = u.load_asset('/Game/Skills/ElectricMagic/M_ElectricFilament')
    ring = u.load_asset('/Game/Skills/ElectricMagic/M_ElectricRing')
    for em in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, em),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + em + '.' + stage)

    source = u.load_asset(TEMPLATE)
    lc = {k: u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', k)
          for k in ('Life Cycle Mode', 'Loop Behavior')}
    lc['Life Cycle Mode'] = lc['Life Cycle Mode'].replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')

    def add_sprite(name, mat, rate, life, pos, size, color, rot='0'):
        API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
        trim(system, name, {'EmitterUpdateScript': ['EmitterState'], 'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
            'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
            'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
            'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth',
            'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable'})
        for k, v in lc.items():
            put(system, name, 'EmitterUpdateScript', 'EmitterState', k, v, ENUM)
        expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '1')
        API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
        expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', str(rate))
        fade = 'saturate(Particles.NormalizedAge*5)*pow(saturate((1-Particles.NormalizedAge)*2.4),1.6)'
        assignments(system, name, 'ParticleSpawnScript', {
            'Particles.Lifetime': (FLOAT, str(life)), 'Particles.Position': (POSITION, pos),
            'Particles.SpriteSize': (VEC2, size), 'Particles.Color': (COLOR, f'({color})*float4(1,1,1,0)'),
            'Particles.SpriteRotation': (FLOAT, rot), 'Particles.SubImageIndex': (FLOAT, '0')})
        assignments(system, name, 'ParticleUpdateScript', {
            'Particles.Position': (POSITION, pos), 'Particles.SpriteSize': (VEC2, size),
            'Particles.Color': (COLOR, f'({color})*float4(1,1,1,{fade})'), 'Particles.SubImageIndex': (FLOAT, '0')})

    # Clean staff-tip crackling halo (EnergyCore fog ball removed so crosshair stays 100% clear!),
    # tinted dynamically across Blue / Violet / Cyan.
    theta = f'{SEED}*6.2831853+Particles.Age*(9+User.Charge*7)'
    radius = '(10+User.Charge*11)*(1-Particles.NormalizedAge*.45)'
    pos = f'float3(cos({theta})*{radius},sin({theta})*{radius},({SEED2}-.5)*10)'
    hm = f'frac({SEED2}+Particles.Age*0.75)'
    cr = f'lerp(lerp(.18,.68,saturate({hm}*3.0)),.08,saturate(({hm}-.50)*2.5))'
    cg = f'lerp(lerp(.54,.24,saturate({hm}*3.0)),.94,saturate(({hm}-.50)*2.5))'
    add_sprite('GatheringSparks', spark, 42, .30, pos, 'float2(1.6+User.Charge*1.8,5.0+User.Charge*3.8)', f'float4({cr},{cg},1,.32)', f'{SEED3}*360')
    add_sprite('ChargingFilaments', filament, 14, .16, pos, 'float2(12+User.Charge*12,6.5)', f'float4({cr},{cg},1,.34)', f'{SEED2}*360')
    add_sprite('GatheringRings', ring, 3.0, .38, 'float3(0,0,0)', 'float2(34,34)*(1-Particles.NormalizedAge*.38)', f'float4({cr},{cg},1,.16)')
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-55, -55, -55), max=u.Vector(55, 55, 55)))
    EAL.set_metadata_tag(system, 'ArcaneCirclesV2.Revision', 'ArcaneCirclesV2_20261127')
    save_asset(system)
    return system


def rebuild_absolute_zero_sigil():
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

    hlsl = (AZ_ROOT / 'AbsoluteZeroSigil.hlsl').read_text(encoding='utf-8')
    packed = node(u.MaterialExpressionCustom, description='AbsoluteZeroSigil.ApertureV2',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4, code=hlsl)
    inputs = {'UV': uv, 'Time': tm, 'Progress': progress, 'Fade': fade, 'Synergy': synergy, 'ColorSeed': seed}
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
    EAL.set_metadata_tag(mat, 'ArcaneCirclesV2.Revision', 'ArcaneCirclesV2_20261127')
    save_asset(mat)
    return mat


def main():
    backups = backup_targets()
    rebuild_thunder_circle()
    rebuild_thunder_iris()
    rebuild_thunder_gather()
    rebuild_thunder_charge()
    rebuild_absolute_zero_sigil()

    saved = {}
    for ap in TARGETS:
        dp = disk_path(ap)
        if not dp.is_file():
            raise RuntimeError('Missing saved asset: ' + str(dp))
        saved[ap] = {'disk': str(dp), 'bytes': dp.stat().st_size, 'sha256': sha256(dp)}

    receipt = {
        'version': 'ArcaneCirclesV2_20261127',
        'backups': backups,
        'saved_assets': saved,
        'design': {
            'thunder_lance': 'Aim-centered enlarged aperture (0.70->0.78 @ 66cm), r<0.58 strict zero opacity, tangential rim arcs, Blue/Violet/Cyan random walk via ColorSeed',
            'absolute_zero': 'Enlarged 5.2m ground sigil (40x7 conforming disc), rn<0.48 strict zero opacity clean center, synced replicated NetSigilColorSeed + shifting ChannelLight in Blue/Violet/Cyan',
        },
        'runtime_tested': False,
    }
    PROD.mkdir(parents=True, exist_ok=True)
    rp = PROD / 'published.json'
    rp.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print('ARCANE_CIRCLES_V2_ALL_PASS', str(rp), 'count=', len(saved), flush=True)


if __name__ == '__main__':
    main()
