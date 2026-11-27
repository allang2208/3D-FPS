"""Author shared Terrain-Conforming Frost Sheet + AbsoluteZero Sigil & Inward Cold Mist.

Writes ONLY under /Game/Skills/AbsoluteZero (preserving all existing Blizzard/IceWall/IceSpike/StormDomain assets):
1. M_FrostSurfaceSheet:
   - Shared translucent crystalline frost surface material for Blizzard & AbsoluteZero
     terrain-conforming draped meshes (immune to terrain materials, bReceivesDecals=false,
     higher-SortOrder decals, and 5x5 height-band truncation).
   - Reuses approved /Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor with dual-scale world XY tiling.
2. M_AbsoluteZeroSigil:
   - Procedural 8-pointed crystalline frost sigil for terrain-conforming windup disc beneath caster.
3. NS_AbsoluteZeroInwardMist:
   - Dedicated inward-suction cold mist & frost-shard Niagara system reusing approved
     /Game/Skills/ElectricMagic/StormDomainV4/M_StormDomainSmoke (Mantaflow 8x8 rolling fluid)
     and /Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft.

Run via AuthorHost/DragonBreathAuthor.uproject with DX12/SM6:
  UnrealEditor-Cmd.exe ".../DragonBreathAuthor.uproject" -run=pythonscript
  -script=".../build_absolute_zero_v2_assets.py" -d3d12 -sm6 -RenderOffscreen
  -AllowCommandletRendering -unattended -multiprocess
"""
import hashlib
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
if not hasattr(u, 'RainAssetEditor'):
    if not hasattr(u, 'DragonBreathAuthorLibrary'):
        raise RuntimeError('Run build_absolute_zero_v2_assets.py in DragonBreathAuthor.uproject')
    u.RainAssetEditor = u.DragonBreathAuthorLibrary

from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_electric_magic_assets import ENUM, TEMPLATE

DEST = '/Game/Skills/AbsoluteZero'
REVISION = 'AbsoluteZeroV2_FrostCoverageAndPose_20261126'
OUT = ROOT / 'SourceAssets/AbsoluteZeroV2_20261126'
BATCH_ROOT = Path(r'F:\FPSGAMEData\ArtProduction\AbsoluteZero\AbsoluteZeroV2-20261126')

ICE_TEX = '/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor'
MIST_MAT = '/Game/Skills/ElectricMagic/StormDomainV4/M_StormDomainSmoke'
CRYSTAL_MAT = '/Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft'
NE_CORE = '/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'
LIFECYCLE_SRC = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'

VEC4 = '/Script/CoreUObject.Vector4f'
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SAVED = []


def create_or_reset_material(name):
    path = DEST + '/' + name
    if EAL.does_asset_exist(path):
        m = u.load_asset(path)
        LIB.delete_all_material_expressions(m)
    else:
        m = TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    if not m:
        raise RuntimeError('Cannot create material ' + path)
    return m


def node(m, cls):
    return LIB.create_material_expression(m, cls)


def wire(src, dst, pin):
    obj, out = src if isinstance(src, tuple) else (src, '')
    if not LIB.connect_material_expressions(obj, out, dst, pin):
        raise RuntimeError(f'Material wire failed -> {pin}')


def prop(m, src, name):
    obj, out = src if isinstance(src, tuple) else (src, '')
    if not LIB.connect_material_property(obj, out, getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Material property bind failed: ' + name)


def scalar(m, name, default_val):
    n = node(m, u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', float(default_val))
    return n


def constant(m, val):
    n = node(m, u.MaterialExpressionConstant)
    n.set_editor_property('r', float(val))
    return n


def custom(m, code, inputs, width=1, desc=''):
    n = node(m, u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    if desc:
        n.set_editor_property('description', desc)
    n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for pname in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', pname)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for pname, val in inputs.items():
        wire(val, n, pname)
    return n


def compile_and_save_materials(assets):
    for a in assets:
        if isinstance(a, u.Material):
            errs = LIB.recompile_material(a)
            if errs:
                raise RuntimeError(f'Material compile failed {a.get_path_name()}: {errs}')
    if not u.DragonBreathAuthorLibrary.compile_material_assets(assets):
        raise RuntimeError('DragonBreathAuthorLibrary.compile_material_assets failed')
    for a in assets:
        if not EAL.save_loaded_asset(a, False):
            raise RuntimeError('Failed saving ' + a.get_path_name())
        SAVED.append(a.get_path_name())
        u.log('AZ_V2_SAVED ' + a.get_path_name())


def build_frost_surface_material():
    m = create_or_reset_material('M_FrostSurfaceSheet')
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('material_domain', u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    m.set_editor_property('output_translucent_velocity', False)
    m.set_editor_property('is_translucency_velocity_from_depth', False)
    m.set_editor_property('allow_front_layer_translucency', False)
    m.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE)
    m.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)

    ice_tex = u.load_asset(ICE_TEX)
    if not ice_tex:
        raise RuntimeError('Missing approved ice texture: ' + ICE_TEX)
    tex = node(m, u.MaterialExpressionTextureObjectParameter)
    tex.set_editor_property('parameter_name', 'IceSurfaceColor')
    tex.set_editor_property('texture', ice_tex)
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)

    world_pos = node(m, u.MaterialExpressionWorldPosition)
    vcol = node(m, u.MaterialExpressionVertexColor)
    fade = scalar(m, 'Fade', 1.0)
    reveal = scalar(m, 'RevealRadius', 1.25)
    density = scalar(m, 'FrostDensity', 0.88)
    em_boost = scalar(m, 'EmissiveBoost', 0.25)

    hlsl = (OUT / 'FrostSurfaceSheet.hlsl').read_text(encoding='utf-8')
    packed = custom(
        m, hlsl,
        {
            'WorldPos': world_pos,
            'IceTex': tex,
            'VRGB': (vcol, ''),
            'VA': (vcol, 'A'),
            'Fade': fade,
            'RevealRadius': reveal,
            'FrostDensity': density,
            'EmissiveBoost': em_boost,
        },
        width=4,
        desc='FrostSurfaceSheet.Core',
    )
    base_rgb = custom(m, 'return P.rgb;', {'P': packed}, width=3, desc='FrostSurfaceSheet.BaseRGB')
    op_raw = custom(m, 'return P.a;', {'P': packed}, width=1, desc='FrostSurfaceSheet.OpacityRaw')
    rough_out = custom(
        m,
        'return lerp(0.36, 0.16, saturate((P.r + P.g + P.b) * 0.333));',
        {'P': packed},
        width=1,
        desc='FrostSurfaceSheet.Roughness',
    )
    # Crisp leading frost crest glow + subtle ambient rime luminosity so ice reads clearly in dark dungeons.
    em_code = (
        'float rNorm = VRGB.r; '
        'float rimMod = lerp(0.84, 1.00, VRGB.g); '
        'float outerF = 1.0 - smoothstep(rimMod - 0.15, rimMod, rNorm); '
        'float waveM = 1.0 - smoothstep(RevealRadius - 0.11, RevealRadius + 0.015, rNorm); '
        'float crest = exp(-pow((rNorm - (RevealRadius - 0.03)) / 0.055, 2.0)) * saturate(1.0 - smoothstep(0.95, 1.12, RevealRadius)); '
        'float mask = VA * outerF * waveM * Fade; '
        'return float3(0.45, 0.86, 1.0) * crest * 1.85 * EmissiveBoost * mask + float3(0.11, 0.16, 0.21) * mask;'
    )
    em_out = custom(
        m, em_code,
        {'VRGB': (vcol, ''), 'VA': (vcol, 'A'), 'RevealRadius': reveal, 'Fade': fade, 'EmissiveBoost': em_boost},
        width=3,
        desc='FrostSurfaceSheet.Emissive',
    )

    df = node(m, u.MaterialExpressionDepthFade)
    df.set_editor_property('fade_distance_default', 10.0)
    wire(op_raw, df, str(LIB.get_material_expression_input_names(df)[0]))

    slab = node(m, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    slab_inputs = {str(n) for n in LIB.get_material_expression_input_names(slab)}
    spec = constant(m, 0.72)

    prop(m, base_rgb, 'BASE_COLOR')
    wire(base_rgb, slab, 'BaseColor')
    prop(m, rough_out, 'ROUGHNESS')
    wire(rough_out, slab, 'Roughness')
    prop(m, spec, 'SPECULAR')
    wire(spec, slab, 'Specular')
    prop(m, df, 'OPACITY')
    wire(df, slab, 'Opacity')
    prop(m, em_out, 'EMISSIVE_COLOR')
    if 'EmissiveColor' in slab_inputs:
        wire(em_out, slab, 'EmissiveColor')
    prop(m, slab, 'FRONT_MATERIAL')

    EAL.set_metadata_tag(m, 'AbsoluteZeroV2.Revision', REVISION)
    return m


def build_sigil_material():
    m = create_or_reset_material('M_AbsoluteZeroSigil')
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('material_domain', u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    m.set_editor_property('output_translucent_velocity', False)
    m.set_editor_property('is_translucency_velocity_from_depth', False)
    m.set_editor_property('allow_front_layer_translucency', False)
    m.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)

    uv = node(m, u.MaterialExpressionTextureCoordinate)
    tm = node(m, u.MaterialExpressionTime)
    progress = scalar(m, 'Progress', 0.5)
    fade = scalar(m, 'Fade', 1.0)
    synergy = scalar(m, 'Synergy', 0.0)

    hlsl = (OUT / 'AbsoluteZeroSigil.hlsl').read_text(encoding='utf-8')
    packed = custom(
        m, hlsl,
        {'UV': uv, 'Time': tm, 'Progress': progress, 'Fade': fade, 'Synergy': synergy},
        width=4,
        desc='AbsoluteZeroSigil.Core',
    )
    em_rgb = custom(m, 'return P.rgb;', {'P': packed}, width=3, desc='AbsoluteZeroSigil.Emissive')
    op_raw = custom(m, 'return P.a;', {'P': packed}, width=1, desc='AbsoluteZeroSigil.Opacity')

    df = node(m, u.MaterialExpressionDepthFade)
    df.set_editor_property('fade_distance_default', 8.0)
    wire(op_raw, df, str(LIB.get_material_expression_input_names(df)[0]))

    prop(m, em_rgb, 'EMISSIVE_COLOR')
    prop(m, df, 'OPACITY')

    EAL.set_metadata_tag(m, 'AbsoluteZeroV2.Revision', REVISION)
    return m


def infinite_lifecycle():
    src = u.load_asset(LIFECYCLE_SRC)
    mode = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    return mode, loop


def build_inward_mist_system():
    path = DEST + '/NS_AbsoluteZeroInwardMist'
    if EAL.does_asset_exist(path):
        system = u.load_asset(path)
    else:
        src = u.load_asset(TEMPLATE)
        system = TOOLS.duplicate_asset('NS_AbsoluteZeroInwardMist', DEST, src)
    if not system:
        raise RuntimeError('Failed creating NS_AbsoluteZeroInwardMist')

    for ename in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, ename),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + ename + '.' + stage)

    for pname, typ in [
        ('Center', POSITION),
        ('Progress', FLOAT),
        ('Strength', FLOAT),
        ('Radius', FLOAT),
        ('Synergy', FLOAT),
    ]:
        user_parameter(system, pname, typ)

    mode, loop = infinite_lifecycle()
    mist_mat = u.load_asset(MIST_MAT)
    crys_mat = u.load_asset(CRYSTAL_MAT)
    if not mist_mat or not crys_mat:
        raise RuntimeError(f'Missing reused materials: mist={mist_mat} crystal={crys_mat}')

    # Emitter 1: InwardColdMist — ground-hugging Mantaflow rolling frost plumes sucked rapidly inward into caster.
    en = 'InwardColdMist'
    API.call_method('AddEmitter', (system, u.load_asset(NE_CORE), en))
    trim(system, en, {
        'EmitterUpdateScript': ['EmitterState'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, en), {
        'bLocalSpace': False,
        'SimTarget': 'CPUSim',
        'InterpolatedSpawnMode': 'NoInterpolation',
        'CalculateBoundsMode': 'Dynamic',
    })
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, en, renderer=0), {
        'Material': mist_mat.get_path_name(),
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
    put(system, en, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, en, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)
    API.call_method('AddModule', (ref(system, en, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    API.call_method('AddModule', (ref(system, en, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system, en, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="(38+24*saturate(User.Progress))*saturate(User.Strength)")', HL)
    put(system, en, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(HlslExpression="floor(18*saturate(User.Strength)+.5)")', HL)
    put(system, en, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0.0)')

    s1 = 'frac((float(Particles.UniqueID)+.5)*.61803398875+.17)'
    s2 = 'frac((float(Particles.UniqueID)+.5)*.41421356237+.43)'
    s3 = 'frac((float(Particles.UniqueID)+.5)*.75487766623+.71)'
    ang0 = f'({s1}*6.2831853)'
    r0 = f'(max(180.0,User.Radius)*(.68+.38*{s2}))'
    z0 = f'(16.0+42.0*{s3})'
    life = f'(.46+.24*{s3})'
    pos0 = f'User.Center+float3(cos({ang0})*{r0},sin({ang0})*{r0},{z0})'
    assignments(system, en, 'ParticleSpawnScript', {
        'Particles.MistAngle': (FLOAT, ang0),
        'Particles.MistR0': (FLOAT, r0),
        'Particles.MistZ0': (FLOAT, z0),
        'Particles.MistSeed': (FLOAT, s1),
        'Particles.MistPhase': (FLOAT, s2),
        'Particles.Lifetime': (FLOAT, life),
        'Particles.Position': (POSITION, pos0),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, 'float2(96,68)'),
        'Particles.SpriteRotation': (FLOAT, f'({s3}*6.2831853)'),
        'Particles.Color': (COLOR, 'float4(.72,.90,1,0)'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({s1},{s2},.2,0)'),
    })
    n = 'Particles.NormalizedAge'
    # Accelerating inward spiral pull: ease-in curve sucks mist faster as it nears the staff!
    pull = f'(1.0-pow(saturate({n}),1.55))'
    ang = f'(Particles.MistAngle+Particles.Age*(1.35+1.45*saturate(User.Progress)))'
    rad = f'(max(10.0,Particles.MistR0*{pull}))'
    # Rises gently toward the staff grip height as it converges at center.
    z = f'lerp(Particles.MistZ0,75.0+35.0*Particles.MistPhase,pow(saturate({n}),1.4))'
    pos = f'User.Center+float3(cos({ang})*{rad},sin({ang})*{rad},{z})'
    sz = f'lerp(118.0,42.0,saturate({n}))*(.82+.36*Particles.MistPhase)'
    env = smooth('0', '.18', n) + '*(1-' + smooth('.72', '1', n) + ')'
    glow = f'(.22+.55*saturate(User.Progress)+.25*saturate(User.Synergy))*saturate({n})'
    assignments(system, en, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, pos),
        'Particles.SpriteSize': (VEC2, f'float2({sz},({sz})*.72)'),
        'Particles.SpriteRotation': (FLOAT, f'(Particles.MistPhase*6.2831853+Particles.Age*1.8)'),
        'Particles.Color': (COLOR, f'float4(.76,.91,1.0,(.36+.14*saturate(User.Progress))*({env})*saturate(User.Strength))'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4(Particles.MistSeed,Particles.MistPhase,{glow},0)'),
    })

    # Emitter 2: InwardFrostShards — bright crystalline frost motes streaming rapidly inward into the staff.
    en2 = 'InwardFrostShards'
    API.call_method('AddEmitter', (system, u.load_asset(NE_CORE), en2))
    trim(system, en2, {
        'EmitterUpdateScript': ['EmitterState'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, en2), {
        'bLocalSpace': False,
        'SimTarget': 'CPUSim',
        'InterpolatedSpawnMode': 'NoInterpolation',
        'CalculateBoundsMode': 'Dynamic',
    })
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, en2, renderer=0), {
        'Material': crys_mat.get_path_name(),
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
    put(system, en2, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, en2, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)
    API.call_method('AddModule', (ref(system, en2, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(system, en2, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="(55+40*saturate(User.Progress)+20*saturate(User.Synergy))*saturate(User.Strength)")', HL)

    c1 = 'frac((float(Particles.UniqueID)+.5)*.61803398875+.61)'
    c2 = 'frac((float(Particles.UniqueID)+.5)*.41421356237+.29)'
    c3 = 'frac((float(Particles.UniqueID)+.5)*.75487766623+.83)'
    cang0 = f'({c1}*6.2831853)'
    cr0 = f'(max(220.0,User.Radius)*(.74+.42*{c2}))'
    cz0 = f'(12.0+72.0*{c3})'
    clife = f'(.34+.20*{c3})'
    cpos0 = f'User.Center+float3(cos({cang0})*{cr0},sin({cang0})*{cr0},{cz0})'
    assignments(system, en2, 'ParticleSpawnScript', {
        'Particles.CrysAngle': (FLOAT, cang0),
        'Particles.CrysR0': (FLOAT, cr0),
        'Particles.CrysZ0': (FLOAT, cz0),
        'Particles.CrysSeed': (FLOAT, c2),
        'Particles.Lifetime': (FLOAT, clife),
        'Particles.Position': (POSITION, cpos0),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, 'float2(6,6)'),
        'Particles.SpriteRotation': (FLOAT, f'({c1}*360.0)'),
        'Particles.Color': (COLOR, 'float4(.72,.94,1,0)'),
    })
    cpull = f'(1.0-pow(saturate({n}),1.75))'
    cang = f'(Particles.CrysAngle+Particles.Age*(2.2+2.0*saturate(User.Progress)))'
    crad = f'(max(6.0,Particles.CrysR0*{cpull}))'
    cz = f'lerp(Particles.CrysZ0,108.0+32.0*Particles.CrysSeed,pow(saturate({n}),1.35))'
    cpos = f'User.Center+float3(cos({cang})*{crad},sin({cang})*{crad},{cz})'
    csz = f'(4.5+5.5*Particles.CrysSeed)*(1.15-.55*saturate({n}))'
    cenv = smooth('0', '.14', n) + '*(1-' + smooth('.78', '1', n) + ')'
    assignments(system, en2, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, cpos),
        'Particles.SpriteSize': (VEC2, f'float2({csz},{csz})'),
        'Particles.SpriteRotation': (FLOAT, f'(Particles.CrysSeed*360.0+Particles.Age*240.0)'),
        'Particles.Color': (COLOR, f'float4(.78,.95,1.0,(.85+.15*saturate(User.Synergy))*({cenv})*saturate(User.Strength))'),
    })

    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-700, -700, -120), max=u.Vector(700, 700, 320)))
    EAL.set_metadata_tag(system, 'AbsoluteZeroV2.Revision', REVISION)
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Niagara compile failed: ' + system.get_path_name())
    if not EAL.save_loaded_asset(system, False):
        raise RuntimeError('Save failed: ' + system.get_path_name())
    SAVED.append(system.get_path_name())
    u.log('AZ_V2_SAVED ' + system.get_path_name())
    return system


def run():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved AbsoluteZero assets')
    EAL.make_directory(DEST)

    frost_mat = build_frost_surface_material()
    sigil_mat = build_sigil_material()
    compile_and_save_materials([frost_mat, sigil_mat])
    mist_sys = build_inward_mist_system()

    def digest(pkg_path):
        rel = pkg_path.split('.')[0].replace('/Game/', '') + '.uasset'
        disk = ROOT / 'Content' / rel
        return hashlib.sha256(disk.read_bytes()).hexdigest() if disk.is_file() else None

    receipt = {
        'revision': REVISION,
        'dest': DEST,
        'frost_surface_material': frost_mat.get_path_name(),
        'sigil_material': sigil_mat.get_path_name(),
        'inward_mist_system': mist_sys.get_path_name(),
        'reused_assets': [ICE_TEX, MIST_MAT, CRYSTAL_MAT],
        'saved_assets': SAVED,
        'sha256': {Path(p.split('.')[0]).name + '.uasset': digest(p) for p in SAVED},
        'gameplay_tested': False,
        'rendered': False,
    }
    for d in (BATCH_ROOT, OUT):
        d.mkdir(parents=True, exist_ok=True)
        (d / 'published.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ABSOLUTE_ZERO_V2_ASSETS_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    run()
