"""Author StormDomainV4 (Scheme C Tiered Volumetric + Mantaflow Rolling Storm Cloud).

Produces two complementary, independently-addressable Niagara systems under
/Game/Skills/ElectricMagic/StormDomainV4 (leaving StormDomainV3 untouched for rollback):

1. NS_StormDomainVolume + M_StormDomainVolume + MI_StormDomainVolume (Tier 1 Top-Tier Core):
   - True 3D Niagara Fluid gas solver (Grid3D_Gas_SimpleParticleSource + NiagaraVolumeRenderer),
     reusing the Dragon Breath VolumeV8R6 proven pipeline (RG16F local-grid sampling, single
     EyeAdaptationInverse on emissive, Compensate For Actor Motion, Max Streak Samples = 1,
     GDF wall/ceiling collision, Strength=0 invisible background warmup contract).
   - Swirling cyclonic + convective GPU fuel injectors produce thick brooding slate-indigo
     3D billowing smoke with volumetric self-shadowing (zero 2D billboard flatness even 24 cm
     overhead) and localized Temperature spikes driven by User.FlashPos/FlashPulse +
     User.FlashPos2/FlashPulse2 whenever NS_StormCloudArc discharges inside the cloud.

2. NS_StormDomainSmoke + M_StormDomainSmoke (Dual-Role: Tier 1 Rim Wisps & Tier 2 Full Cloud):
   - Reuses approved 64-frame Mantaflow 8x8 smoke atlas (/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14)
     and Substrate translucent volumetric non-directional shading with custom rolling fluid HLSL
     (dual-frame interpolation, per-particle rotation/flip/phase stagger, internal UV curl,
     wispy erosion, and subsurface electric flash scatter).
   - Controlled by User.WispOnly:
       * WispOnly < 0.5 (Tier 2 — Low quality / Remote players / Warmup instant fallback):
         SmokeCoreRoll + SmokeBellyBillow + SmokeRimWisps + FallingElectricSparks.
       * WispOnly >= 0.5 (Tier 1 Companion — Medium+ Local Caster alongside NS_StormDomainVolume):
         SmokeRimWisps + FallingElectricSparks only, adding wispy tendrils around the 3D fluid core.

Run via AuthorHost/DragonBreathAuthor.uproject with DX12/SM6:
  UnrealEditor-Cmd.exe ".../DragonBreathAuthor.uproject" -run=pythonscript -script=".../build_storm_domain_v4.py"
  -d3d12 -sm6 -RenderOffscreen -AllowCommandletRendering -unattended -multiprocess
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
        raise RuntimeError('Run build_storm_domain_v4.py in DragonBreathAuthor.uproject')
    u.RainAssetEditor = u.DragonBreathAuthorLibrary

from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_fireball_slow_burn import smooth
from build_electric_magic_assets import sprite, ENUM, TEMPLATE, SEED, SEED2, SEED3

DEST = '/Game/Skills/ElectricMagic/StormDomainV4'
REVISION = 'StormDomainV4_VolumetricTiered_20261126'
OUT = ROOT / 'SourceAssets/StormDomainCloudV4_20261126'
BATCH_ROOT = Path(r'F:\FPSGAMEData\ArtProduction\StormDomainCloud\StormDomainV4-20261126')

FLUID_TEMPLATE = '/NiagaraFluids/Templates/Gas/3D/Systems/Grid3D_Gas_SimpleParticleSource'
GAS_MAT_BASE = '/NiagaraFluids/Materials/Grid3D/M_3DGas_Base'
GAS_MI_BASE = '/NiagaraFluids/Materials/Grid3D/Instances/MI_3DGas_Base'
SMOKE_ATLAS = '/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14'
NE_CORE = '/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'
LIFECYCLE_SRC = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'
SPARK_MAT = '/Game/Skills/ElectricMagic/M_ElectricSpark'
CLOUD_ARC_PATH = '/Game/Skills/ElectricMagic/StormDomainV3/NS_StormCloudArc'

GRID = 'Grid3D_Gas_Master_Emitter'
INT = '/Script/Niagara.NiagaraInt32'
BOOL = '/Script/Niagara.NiagaraBool'
VEC4 = '/Script/CoreUObject.Vector4f'
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'

EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SAVED = []


def dup(source, name):
    path = DEST + '/' + name
    if EAL.does_asset_exist(path):
        asset = u.load_asset(path)
    else:
        src = u.load_asset(source)
        if not src:
            raise RuntimeError('Missing source asset: ' + source)
        asset = TOOLS.duplicate_asset(name, DEST, src)
    if not asset:
        raise RuntimeError('Failed to create/load ' + path)
    return asset


def create_material(name):
    path = DEST + '/' + name
    if EAL.does_asset_exist(path):
        m = u.load_asset(path)
    else:
        m = TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    if not m:
        raise RuntimeError('Failed to create material ' + path)
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


def constant(m, value):
    n = node(m, u.MaterialExpressionConstant)
    n.set_editor_property('r', float(value))
    return n


def custom_expr(m, code, inputs, width=1, desc=''):
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


def expr_by_desc(m, cls, desc):
    for n in u.ObjectIterator(cls):
        if n.get_outer() == m and str(n.get_editor_property('desc')) == desc:
            return n
    n = LIB.create_material_expression(m, cls)
    n.set_editor_property('desc', desc)
    return n


def compile_and_save_materials(assets):
    for a in assets:
        if isinstance(a, u.Material):
            errors = LIB.recompile_material(a)
            if errors:
                raise RuntimeError(f'Material compile error on {a.get_path_name()}: {errors}')
    if hasattr(u, 'DragonBreathAuthorLibrary'):
        if not u.DragonBreathAuthorLibrary.compile_material_assets(assets):
            raise RuntimeError('DragonBreathAuthorLibrary.compile_material_assets failed')
    for a in assets:
        if not EAL.save_loaded_asset(a, False):
            raise RuntimeError('Failed saving ' + a.get_path_name())
        SAVED.append(a.get_path_name())
        u.log('STORM_V4_SAVED ' + a.get_path_name())


def compile_and_save_system(system):
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Niagara full compile failed: ' + system.get_path_name())
    if not EAL.save_loaded_asset(system, False):
        raise RuntimeError('Failed saving ' + system.get_path_name())
    SAVED.append(system.get_path_name())
    u.log('STORM_V4_SAVED ' + system.get_path_name())


# ==============================================================================
# PART 1: Tier 1 — 3D Volumetric Fluid Cloud (M_StormDomainVolume / NS_StormDomainVolume)
# ==============================================================================

def build_volume_material():
    base = dup(GAS_MAT_BASE, 'M_StormDomainVolume')
    if EAL.get_metadata_tag(base, 'StormV4.Exposure') != 'V1':
        emission = LIB.get_material_property_input_node(base, u.MaterialProperty.MP_EMISSIVE_COLOR)
        if not emission:
            raise RuntimeError('M_3DGas_Base has no MP_EMISSIVE_COLOR input')
        inverse = LIB.create_material_expression(base, u.MaterialExpressionEyeAdaptationInverse)
        inv_pin = str(LIB.get_material_expression_input_names(inverse)[0])
        wire(emission, inverse, inv_pin)
        prop(base, inverse, 'EMISSIVE_COLOR')
        EAL.set_metadata_tag(base, 'StormV4.Exposure', 'V1')

    texture = u.find_object(None, base.get_path_name() + ':MaterialExpressionTextureSampleParameterVolume_0')
    selection = u.find_object(None, base.get_path_name() + ':MaterialExpressionStaticSwitchParameter_2')
    if not texture or not selection:
        raise RuntimeError('Missing native VolumeTex / thermal-color switch nodes in M_StormDomainVolume')

    ramp = expr_by_desc(base, u.MaterialExpressionCustom, 'StormV4.LightningScatterRamp')
    pins = []
    for pname in ['Temperature', 'ColorMin', 'ColorMax']:
        p = u.CustomInput()
        p.set_editor_property('input_name', pname)
        pins.append(p)
    ramp.set_editor_property('inputs', pins)
    ramp.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    ramp.set_editor_property('code', (OUT / 'StormCloudVolumeColor.hlsl').read_text(encoding='utf-8'))
    wire((texture, 'G'), ramp, 'Temperature')

    for pname, default_val in [('ColorMin', 0.08), ('ColorMax', 5.20)]:
        sc = expr_by_desc(base, u.MaterialExpressionScalarParameter, 'StormV4.' + pname)
        sc.set_editor_property('parameter_name', 'Storm' + pname)
        sc.set_editor_property('default_value', default_val)
        wire(sc, ramp, pname)

    for branch in ['True', 'False']:
        wire(ramp, selection, branch)

    EAL.set_metadata_tag(base, 'StormV4.Revision', REVISION)

    mi = dup(GAS_MI_BASE, 'MI_StormDomainVolume')
    LIB.set_material_instance_parent(mi, base)
    for sw_name, sw_val in [
        ('Use Legacy Transform', False),
        ('UseLegacyVolumeSample', False),
        ('Use Blackbody Curve', True),
    ]:
        LIB.set_material_instance_static_switch_parameter_value(mi, sw_name, sw_val)
    for sc_name, sc_val in [('StormColorMin', 0.08), ('StormColorMax', 5.20)]:
        LIB.set_material_instance_scalar_parameter_value(mi, sc_name, sc_val)
    LIB.update_material_instance(mi)
    EAL.set_metadata_tag(mi, 'StormV4.Revision', REVISION)

    compile_and_save_materials([base, mi])
    return base, mi


def build_volume_sources(system):
    en = 'ParticleSourceEmitter'
    trim(system, en, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + en + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, en), {
        'bLocalSpace': False,
        'SimTarget': 'GPUComputeSim',
        'InterpolatedSpawnMode': 'NoInterpolation',
    })
    top = API.call_method('GetEmitterTopology', (ref(system, en),))
    for r in reversed(top.get_editor_property('renderers')):
        API.call_method('RemoveRenderer', (ref(system, en, renderer=r.get_editor_property('renderer_index')),))

    expression(system, en, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
               '520*saturate(User.EmissionScale)')

    s1 = 'frac((float(Particles.UniqueID)+.5)*.61803398875)'
    s2 = 'frac((float(Particles.UniqueID)+.5)*.41421356237)'
    s3 = 'frac((float(Particles.UniqueID)+.5)*.75487766623)'
    # 38% dense zenith core + 62% billowing oblate body -> zero hollow center, lush anvil rim.
    rad = f'(({s1}<.38)?(pow(max(.0001,{s2}),.55)*.42):(.24+pow(max(.0001,{s2}),.72)*.64))'
    ang = f'({s1}*6.2831853+{s3}*3.1415926)'
    dome = f'sqrt(max(.16,1.0-({rad})*({rad})*.72))'
    zfrac = f'(.5+({s3}-.5)*.78*({dome}))'
    spin = f'((.34+.46*{s2})*(({s1}<.5)?1.0:.62))'
    init_z = f'(User.CloudHeight-User.CloudThickness*(1.0-{zfrac}))'
    init_pos = (f'User.CurrentPosition+float3(cos({ang})*User.RadiusX*({rad}),'
                f'sin({ang})*User.RadiusY*({rad}),{init_z})')

    assignments(system, en, 'ParticleSpawnScript', {
        'Particles.CloudAngle': (FLOAT, ang),
        'Particles.CloudRadial': (FLOAT, rad),
        'Particles.CloudZFrac': (FLOAT, zfrac),
        'Particles.CloudSpin': (FLOAT, spin),
        'Particles.Lifetime': (FLOAT, f'.42+.30*{s3}'),
        'Particles.Position': (POSITION, init_pos),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.Color': (COLOR, 'float4(1,1,1,1)'),
    })

    cur_ang = '(Particles.CloudAngle+Particles.Age*Particles.CloudSpin)'
    # Toroidal thunderhead roll: upper layers curl gently outward, lower belly pulls inward.
    cur_rad = 'clamp(Particles.CloudRadial+Particles.Age*((Particles.CloudZFrac>.5)?.09:-.04),.02,.90)'
    z_wave = 'sin(Particles.Age*5.2+Particles.CloudAngle*3.0)*min(10.0,User.CloudThickness*.14)'
    cur_z = f'(User.CloudHeight-User.CloudThickness*(1.0-Particles.CloudZFrac)+{z_wave})'
    cur_pos = (f'User.CurrentPosition+float3(cos({cur_ang})*User.RadiusX*({cur_rad}),'
               f'sin({cur_ang})*User.RadiusY*({cur_rad}),{cur_z})')
    tang = f'float3(-sin({cur_ang}),cos({cur_ang}),0)'
    outw = f'float3(cos({cur_ang}),sin({cur_ang}),0)'
    vert = '((Particles.CloudRadial<.45)?28.0:-14.0)'
    vel = (f'{tang}*(55.0+75.0*({cur_rad}))+'
           f'{outw}*((Particles.CloudZFrac>.5)?36.0:-18.0)+'
           f'float3(0,0,{vert})+User.Wind*.35')

    assignments(system, en, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, cur_pos),
        'Particles.Velocity': (VEC3, vel),
    })

    API.call_method('AddModule', (
        ref(system, en, 'ParticleUpdateScript'),
        u.load_asset('/NiagaraFluids/Modules/Particles/SetFluidSourceAttributes'),
    ))
    sc = 'ParticleUpdateScript'
    mod = 'SetFluidSourceAttributes'
    life_env = '(saturate(Particles.NormalizedAge*4.5)*saturate((1.0-Particles.NormalizedAge)*3.2))'
    rad_w = '(1.0-.48*saturate(Particles.CloudRadial))'
    d1 = '(Particles.Position-User.FlashPos)'
    d2 = '(Particles.Position-User.FlashPos2)'
    frad_sq = 'max(3600.0,pow(min(User.RadiusX,User.RadiusY)*.38,2.0))'
    flash = (f'(saturate(User.FlashPulse)*exp(-dot({d1},{d1})/{frad_sq})*6.8+'
             f'saturate(User.FlashPulse2)*exp(-dot({d2},{d2})/{frad_sq})*5.6)')
    ambient = '(.035*(1.0-saturate(Particles.CloudRadial)))'

    expression(system, en, sc, mod, 'Density', f'(.94*{rad_w}*{life_env})')
    expression(system, en, sc, mod, 'Temperature', f'(({ambient}+{flash})*{life_env})')
    expression(system, en, sc, mod, 'Velocity', 'Particles.Velocity')
    expression(system, en, sc, mod, 'Velocity Scale', '.68')
    expression(system, en, sc, mod, 'Radius', 'max(User.CellSize*2.15,min(User.CloudThickness*.34,26.0))')
    put(system, en, sc, mod, 'Divergence', '(Value=0.0)')
    put(system, en, sc, mod, 'Transform To WorldSpace', '(Value=0)', BOOL)


def configure_volume_solver(system):
    changes = []

    def val(module, name, text):
        changes.append({'emitter': GRID, 'module': module, 'input': name, 'value': text})

    def num(module, name, value):
        val(module, name, f'(Value={value})')

    def expr(module, name, text):
        changes.append({'emitter': GRID, 'module': module, 'input': name, 'expression': text})

    q = 'Grid3D_Gas_QualityOverrides'
    expr(q, 'Resolution Max Axis', 'User.ResolutionMaxAxis')
    expr(q, 'Override.Resolution Max Axis', 'User.ResolutionMaxAxis')
    num(q, 'Pressure Solve Iterations', 6)
    num(q, 'Override.Pressure Solve Iterations', 6)
    num(q, 'Attribute Resolution Multiplier', 1)
    num(q, 'Override.Attribute Resolution Multiplier', 1)

    init = 'Grid3D_Gas_InitializeEmitter'
    expr(init, 'World Size', 'User.WorldSpaceSize')
    num(init, 'Internal Scale Multiplier', 1)

    up = 'Grid3D_Gas_UpdateEmitter'
    num(up, 'Compensate For Actor Motion', -1)
    num(up, 'Draw Guides', 0)
    val(up, 'Local Pivot', '(X=0,Y=0,Z=0)')

    src = 'Grid3D_Gas_InitializeParticleSource'
    num(src, 'Use Radius Falloff', -1)
    # Prevent motion streaking while keeping the active single-sample splat path (DragonBreath R1 rule).
    num(src, 'Use Streaking', -1)
    num(src, 'Max Streak Samples', 1)
    num(src, 'Streak Rate', 1)
    num(src, 'Attributes Comp Mode', 1)
    num(src, 'Velocity Comp Mode', 0)

    mc = 'Grid3D_Gas_MaterialControls'
    val(mc, 'Smoke Color', '(R=0.22,G=0.26,B=0.38,A=1.0)')
    num(mc, 'Apply Color Grid To Smoke', 0)
    val(mc, 'Density Range', '(X=0.0,Y=1.0)')
    expr(mc, 'Density Gain', '0.96*saturate(User.Strength)')
    num(mc, 'Density Albedo', 0.36)
    val(mc, 'Temperature Range', '(X=0.08,Y=5.2)')
    expr(mc, 'Temperature Color Gain', '0.80*saturate(User.Strength)')
    expr(mc, 'Temperature Opacity Gain', '0.26*saturate(User.Strength)')

    num('Grid3D_ComputeBoundary', 'Use Global Distance Field Collisions', -1)
    num('Grid3D_RigidMesh_FindColliders', 'FindColliders', 0)

    num('Grid3D_Gas_Buoyancy', 'DensityBuoyancy', -0.015)
    num('Grid3D_Gas_Buoyancy', 'TemperatureBuoyancy', 0.025)
    num('DissipateVector', 'DissipationRate', 0.55)

    adv = 'Grid3D_Advect_FluidAttribute'
    num(adv, 'Dissipation Rate Density', 0.72)
    num(adv, 'Subtraction Amount Density', 0.025)
    num(adv, 'Dissipation Rate Temperature', 6.8)
    num(adv, 'Subtraction Amount Temperature', 0.18)

    turb = 'Grid3D_Turbulence001'
    val(turb, 'Turbulence Gain', '(X=135,Y=135,Z=82)')
    val(turb, 'Turbulence Frequency', '(X=0.14,Y=0.14,Z=0.18)')
    num(turb, 'Turbulence Speed', 0.78)
    num('Grid3D_SmallScaleForce', 'Gain', 26)
    num('Grid3D_VorticityConfinementForce', 'VorticityMult', 3.2)

    if not u.DragonBreathAuthorLibrary.configure_fluid_inputs(system, json.dumps(changes)):
        raise RuntimeError('configure_fluid_inputs incomplete for NS_StormDomainVolume')
    return changes


def build_volume_system():
    _, mi = build_volume_material()
    system = dup(FLUID_TEMPLATE, 'NS_StormDomainVolume')
    u.DragonBreathAuthorLibrary.prepare_fluid_stack(system)

    defaults = [
        ('CurrentPosition', POSITION, '(X=0,Y=0,Z=0)'),
        ('RadiusX', FLOAT, '(Value=240)'),
        ('RadiusY', FLOAT, '(Value=200)'),
        ('CloudHeight', FLOAT, '(Value=216)'),
        ('CloudThickness', FLOAT, '(Value=96)'),
        ('WorldSpaceSize', VEC3, '(X=620,Y=540,Z=185)'),
        ('ResolutionMaxAxis', INT, '(Value=80)'),
        ('CellSize', FLOAT, '(Value=7.75)'),
        ('Strength', FLOAT, '(Value=1)'),
        ('EmissionScale', FLOAT, '(Value=1)'),
        ('Wind', VEC3, '(X=0,Y=0,Z=0)'),
        ('FlashPos', POSITION, '(X=0,Y=0,Z=0)'),
        ('FlashPulse', FLOAT, '(Value=0)'),
        ('FlashPos2', POSITION, '(X=0,Y=0,Z=0)'),
        ('FlashPulse2', FLOAT, '(Value=0)'),
        ('DrawBounds', BOOL, '(Value=0)'),
    ]
    payload = [{'name': 'User.' + n, 'type': t, 'value': v} for n, t, v in defaults]
    if not u.DragonBreathAuthorLibrary.set_fluid_user_defaults(system, json.dumps(payload)):
        raise RuntimeError('Failed installing fluid user defaults on NS_StormDomainVolume')

    build_volume_sources(system)
    configure_volume_solver(system)

    # Disable debug slice renderer 0; bind volume renderer 1 to our storm volume MI.
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, GRID, renderer=0), {'bIsEnabled': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, GRID, renderer=1), {
        'StepFactor': 0.85,
        'LightingDownsampleFactor': 2.0,
        'ShadowStepFactor': 2.5,
        'Material': mi.get_path_name(),
    })
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-700, -700, -250), max=u.Vector(700, 700, 250)))
    EAL.set_metadata_tag(system, 'StormV4.Revision', REVISION)
    EAL.set_metadata_tag(system, 'StormV4.Source', FLUID_TEMPLATE)
    compile_and_save_system(system)
    return system, mi


# ==============================================================================
# PART 2: Mantaflow 8x8 Continuous Rolling Smoke (M_StormDomainSmoke / NS_StormDomainSmoke)
# ==============================================================================

def build_smoke_material():
    m = create_material('M_StormDomainSmoke')
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('material_domain', u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    m.set_editor_property('output_translucent_velocity', False)
    m.set_editor_property('is_translucency_velocity_from_depth', False)
    m.set_editor_property('allow_front_layer_translucency', False)
    m.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    m.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    LIB.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)

    hlsl = (OUT / 'StormDomainRollingSmoke.hlsl').read_text(encoding='utf-8')
    existing = next((n for n in LIB.get_material_expressions(m)
                     if isinstance(n, u.MaterialExpressionCustom)
                     and str(n.get_editor_property('description')) == 'StormV4.RollingSmoke'), None)
    if existing:
        existing.set_editor_property('code', hlsl)
        EAL.set_metadata_tag(m, 'StormV4.Revision', REVISION)
        compile_and_save_materials([m])
        return m

    uv = node(m, u.MaterialExpressionTextureCoordinate)
    tex = node(m, u.MaterialExpressionTextureObjectParameter)
    tex.set_editor_property('parameter_name', 'DensityAtlas')
    atlas = u.load_asset(SMOKE_ATLAS)
    if not atlas:
        raise RuntimeError('Missing approved Mantaflow smoke atlas: ' + SMOKE_ATLAS)
    tex.set_editor_property('texture', atlas)
    tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)

    color = node(m, u.MaterialExpressionParticleColor)
    age = node(m, u.MaterialExpressionParticleRelativeTime)
    dynamic = node(m, u.MaterialExpressionDynamicParameter)
    dynamic.set_editor_property('param_names', ['SmokeSeed', 'SmokePhase', 'FlashGlow', 'UnusedW'])

    field = custom_expr(
        m, hlsl,
        {
            'UV': uv,
            'Atlas': tex,
            'Age': age,
            'Dynamic': (dynamic, 'RGBA'),
            'Alpha': (color, 'A'),
        },
        width=2,
        desc='StormV4.RollingSmoke',
    )
    opacity_raw = custom_expr(m, 'return F.x;', {'F': field}, width=1, desc='StormV4.OpacityOut')
    emissive_out = custom_expr(
        m,
        'return float3(0.46, 0.62, 2.35) * F.y;',
        {'F': field},
        width=3,
        desc='StormV4.FlashEmissiveOut',
    )
    tint = custom_expr(m, 'return Tint;', {'Tint': (color, 'RGB')}, width=3, desc='StormV4.BaseTint')

    fade = node(m, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 24.0)
    wire(opacity_raw, fade, str(LIB.get_material_expression_input_names(fade)[0]))

    slab = node(m, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    slab_inputs = {str(n) for n in LIB.get_material_expression_input_names(slab)}
    rough = constant(m, 1.0)
    spec = constant(m, 0.0)

    prop(m, tint, 'BASE_COLOR')
    wire(tint, slab, 'BaseColor')
    prop(m, rough, 'ROUGHNESS')
    wire(rough, slab, 'Roughness')
    prop(m, spec, 'SPECULAR')
    wire(spec, slab, 'Specular')
    prop(m, fade, 'OPACITY')
    wire(fade, slab, 'Opacity')
    prop(m, emissive_out, 'EMISSIVE_COLOR')
    if 'EmissiveColor' in slab_inputs:
        wire(emissive_out, slab, 'EmissiveColor')
    prop(m, slab, 'FRONT_MATERIAL')

    EAL.set_metadata_tag(m, 'StormV4.Revision', REVISION)
    compile_and_save_materials([m])
    return m


def smoke_lifecycle():
    src = u.load_asset(LIFECYCLE_SRC)
    mode = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(src, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    return mode, loop


def add_rolling_smoke_emitter(system, mat, spec, lc):
    (name, rate, burst, life_min, life_max, rad_min, rad_max, rad_exp,
     z_min, z_max, size_min, size_max, grow, rgb, alpha, swirl_dir, wisp_mode, salt) = spec

    API.call_method('AddEmitter', (system, u.load_asset(NE_CORE), name))
    trim(system, name, {
        'EmitterUpdateScript': ['EmitterState'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)

    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {
        'bLocalSpace': False,
        'SimTarget': 'CPUSim',
        'InterpolatedSpawnMode': 'NoInterpolation',
        'CalculateBoundsMode': 'Dynamic',
    })
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': mat.get_path_name(),
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

    mode, loop = lc
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)

    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))

    detail = '(1-saturate(User.DetailReduction)*.35)'
    if wisp_mode == 'core':
        tier_gate = '(User.WispOnly<.5?1.0:0.0)'
        rate_expr = f'{rate}*saturate(User.CloudEmission)*saturate(User.Strength)*{tier_gate}*{detail}'
        burst_expr = f'floor({burst}*saturate(User.CloudEmission)*{tier_gate}*{detail}+.5)'
        alpha_expr = f'{alpha}'
    else:
        # Rim wisps render in BOTH Tier 1 (delicate wisps hugging 3D fluid) and Tier 2 (full rolling edge).
        rate_expr = f'((User.WispOnly>=.5)?{round(rate * 1.15, 2)}:{rate})*saturate(User.CloudEmission)*saturate(User.Strength)*{detail}'
        burst_expr = f'floor({burst}*saturate(User.CloudEmission)*{detail}+.5)'
        alpha_expr = f'((User.WispOnly>=.5)?{round(alpha * 0.78, 3)}:{alpha})'

    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', f'(HlslExpression="{rate_expr}")', HL)
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count', f'(HlslExpression="{burst_expr}")', HL)
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0.0)')

    s1 = f'frac((float(Particles.UniqueID)+.5)*.61803398875+{salt})'
    s2 = f'frac((float(Particles.UniqueID)+.5)*.41421356237+{salt}*.73)'
    s3 = f'frac((float(Particles.UniqueID)+.5)*.75487766623+{salt}*.41)'

    rad0 = f'({rad_min}+pow(max(.0001,{s2}),{rad_exp})*{round(rad_max - rad_min, 4)})'
    ang0 = f'({s1}*6.2831853+{s3}*3.1415926)'
    zfrac0 = f'({z_min}+{s3}*{round(z_max - z_min, 4)})'
    rot0 = f'({s3}*6.2831853)'
    spin0 = f'(({s2}-.5)*.82+({swirl_dir})*.18)'
    life = f'({life_min}+{s3}*{round(life_max - life_min, 4)})'
    base_size = f'min(User.RadiusX,User.RadiusY)*({size_min}+{s2}*{round(size_max - size_min, 4)})'
    init_pos = (f'User.CurrentPosition+(User.Side*cos({ang0})*User.RadiusX+'
                f'User.Up*sin({ang0})*User.RadiusY)*({rad0})+'
                f'User.SurfaceNormal*(User.CloudHeight-User.CloudThickness*({zfrac0}))')

    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.SmokeAngle': (FLOAT, ang0),
        'Particles.SmokeRadial': (FLOAT, rad0),
        'Particles.SmokeZFrac': (FLOAT, zfrac0),
        'Particles.SmokeSeed': (FLOAT, s1),
        'Particles.SmokePhase': (FLOAT, s2),
        'Particles.SmokeRot0': (FLOAT, rot0),
        'Particles.SmokeSpin': (FLOAT, spin0),
        'Particles.SmokeSize0': (FLOAT, base_size),
        'Particles.Lifetime': (FLOAT, life),
        'Particles.Position': (POSITION, init_pos),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, f'float2({base_size},min(({base_size})*.80,max(14,User.CloudThickness)*.92))'),
        'Particles.SpriteRotation': (FLOAT, rot0),
        'Particles.Color': (COLOR, f'float4({rgb[0]},{rgb[1]},{rgb[2]},0)'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({s1},{s2},0,0)'),
    })

    a = 'Particles.Age'
    n = 'Particles.NormalizedAge'
    ang = f'(Particles.SmokeAngle+{a}*(.28+.24*Particles.SmokeSeed)*({swirl_dir}))'
    # Continuous turbulent radial billow + vertical roll so every puff genuinely curls through the cloud.
    out_drift = f'({a}*.065)' if wisp_mode == 'wisp' else f'({a}*.045*(Particles.SmokeZFrac<.55?1.0:-.35))'
    rad = f'clamp(Particles.SmokeRadial+{out_drift},.01,1.06)'
    curl = (f'(User.Side*sin({a}*2.1+Particles.SmokeSeed*6.2831853)+'
            f'User.Up*cos({a}*1.85+Particles.SmokePhase*6.2831853))*(10.0+16.0*{n})')
    z_bob = f'(sin({a}*2.6+Particles.SmokePhase*6.2831853)*min(11.0,User.CloudThickness*.16))'
    z_height = f'(User.CloudHeight-User.CloudThickness*Particles.SmokeZFrac+{z_bob})'
    wind_drift = f'(User.Wind*{a}*{"0.32" if wisp_mode == "wisp" else "0.14"})'
    pos = (f'User.CurrentPosition+(User.Side*cos({ang})*User.RadiusX+'
           f'User.Up*sin({ang})*User.RadiusY)*({rad})+'
           f'User.SurfaceNormal*({z_height})+{curl}+{wind_drift}')

    scale = f'(1.0+{grow}*sqrt(saturate({n})))'
    w = f'(Particles.SmokeSize0*{scale})'
    h = f'min(({w})*.82,max(16.0,User.CloudThickness)*({".96" if wisp_mode == "core" else ".86"}))'
    env = smooth('0', '.24', n) + '*(1-' + smooth('.54', '1', n) + ')'
    d1 = '(Particles.Position-User.FlashPos)'
    d2 = '(Particles.Position-User.FlashPos2)'
    frad_sq = 'max(4200.0,pow(min(User.RadiusX,User.RadiusY)*.44,2.0))'
    flash_glow = (f'saturate(saturate(User.FlashPulse)*exp(-dot({d1},{d1})/{frad_sq})*1.15+'
                  f'saturate(User.FlashPulse2)*exp(-dot({d2},{d2})/{frad_sq})*.95)')
    shade = f'(.84+.32*Particles.SmokePhase)'
    col = f'float4({rgb[0]}*{shade},{rgb[1]}*{shade},{rgb[2]}*{shade},({alpha_expr})*({env})*saturate(User.Strength))'

    assignments(system, name, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, pos),
        'Particles.SpriteSize': (VEC2, f'float2({w},{h})'),
        'Particles.SpriteRotation': (FLOAT, f'Particles.SmokeRot0+{a}*Particles.SmokeSpin'),
        'Particles.Color': (COLOR, col),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4(Particles.SmokeSeed,Particles.SmokePhase,{flash_glow},0)'),
    })


def build_smoke_system():
    mat = build_smoke_material()
    system = dup(TEMPLATE, 'NS_StormDomainSmoke')
    for ename in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, ename),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + ename + '.' + stage)

    for pname, typ in [
        ('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3),
        ('SurfaceNormal', VEC3), ('Wind', VEC3),
        ('RadiusX', FLOAT), ('RadiusY', FLOAT),
        ('CloudHeight', FLOAT), ('CloudThickness', FLOAT),
        ('StormDuration', FLOAT), ('CloudEmission', FLOAT),
        ('Strength', FLOAT), ('DetailReduction', FLOAT),
        ('WispOnly', FLOAT),
        ('FlashPos', POSITION), ('FlashPulse', FLOAT),
        ('FlashPos2', POSITION), ('FlashPulse2', FLOAT),
    ]:
        user_parameter(system, pname, typ)

    expression(system, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration',
               'max(.6,User.StormDuration+.6)')

    lc = smoke_lifecycle()
    # Continuous Mantaflow 8x8 rolling smoke emitters:
    #   (name, rate, burst, life_min, life_max, rad_min, rad_max, rad_exp,
    #    z_min, z_max, size_min, size_max, grow, rgb, alpha, swirl_dir, wisp_mode, salt)
    layers = [
        ('SmokeCoreRoll',    18.0, 20, 2.3, 3.2, 0.00, 0.58, 0.68, 0.24, 0.78, 0.56, 0.84, 0.42, (0.062, 0.076, 0.118), 0.34,  1.0, 'core', 0.113),
        ('SmokeBellyBillow', 22.0, 16, 1.6, 2.4, 0.14, 0.80, 0.72, 0.42, 0.90, 0.44, 0.70, 0.55, (0.105, 0.128, 0.195), 0.28, -1.0, 'core', 0.379),
        ('SmokeRimWisps',    15.0,  9, 1.3, 2.0, 0.50, 0.94, 0.75, 0.36, 0.94, 0.32, 0.54, 0.62, (0.165, 0.195, 0.285), 0.22,  1.0, 'wisp', 0.671),
    ]
    for spec in layers:
        add_rolling_smoke_emitter(system, mat, spec, lc)

    # Preserve violet-blue electric sparks shedding from the storm belly in BOTH tiers.
    spark = u.load_asset(SPARK_MAT)
    if not spark:
        raise RuntimeError('Missing shared spark material: ' + SPARK_MAT)
    emission = 'saturate(User.CloudEmission)*saturate(User.Strength)*(1-saturate(User.DetailReduction))'
    theta = f'{SEED}*6.2831853'
    radial = f'sqrt(max(.0001,{SEED2}))*.56'
    spark_pos = (
        f'User.CurrentPosition+(User.Side*cos({theta})*User.RadiusX+'
        f'User.Up*sin({theta})*User.RadiusY)*({radial})+'
        f'User.SurfaceNormal*(User.CloudHeight-User.CloudThickness*(.52+{SEED3}*.38))'
    )
    sprite(
        system, 'FallingElectricSparks', spark,
        rate=f'16*{emission}', life=0.38,
        position=spark_pos + '-User.SurfaceNormal*Particles.Age*62',
        size='float2(2.4,min(9.5,User.CloudThickness*.15))',
        color='float4(.52,.36,1,User.Strength)', rotation='0',
        loop_seconds='max(.6,User.StormDuration+.6)',
    )
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, 'FallingElectricSparks'), {
        'bLocalSpace': False,
        'SimTarget': 'CPUSim',
        'InterpolatedSpawnMode': 'NoInterpolation',
        'CalculateBoundsMode': 'Dynamic',
    })
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, 'FallingElectricSparks', renderer=0), {
        'FacingMode': 'FaceCamera',
        'Alignment': 'Unaligned',
    })

    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-900, -900, -120), max=u.Vector(900, 900, 420)))
    EAL.set_metadata_tag(system, 'StormV4.Revision', REVISION)
    compile_and_save_system(system)
    return system, mat


def run():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved StormDomainV4 assets')
    EAL.make_directory(DEST)

    vol_sys, vol_mi = build_volume_system()
    smoke_sys, smoke_mat = build_smoke_system()

    def digest(pkg_path):
        rel = pkg_path.split('.')[0].replace('/Game/', '') + '.uasset'
        disk = ROOT / 'Content' / rel
        return hashlib.sha256(disk.read_bytes()).hexdigest() if disk.is_file() else None

    receipt = {
        'revision': REVISION,
        'dest': DEST,
        'tier1_volume_system': vol_sys.get_path_name(),
        'tier1_volume_material': vol_mi.get_path_name(),
        'tier2_and_wisp_smoke_system': smoke_sys.get_path_name(),
        'tier2_and_wisp_smoke_material': smoke_mat.get_path_name(),
        'reused_smoke_atlas': SMOKE_ATLAS,
        'reused_cloud_lightning_arc': CLOUD_ARC_PATH,
        'reused_spark_material': SPARK_MAT,
        'saved_assets': SAVED,
        'sha256': {Path(p.split('.')[0]).name + '.uasset': digest(p) for p in SAVED},
        'features': [
            'Tier1 Grid3D_Gas 3D volumetric billowing storm cloud (Medium=64, High=80, Epic=96)',
            'Tier1 + Tier2 real-time dual-slot internal lightning scatter (User.FlashPos/FlashPulse + FlashPos2/FlashPulse2)',
            'Tier1 companion rim wisps + Tier2 full Mantaflow 8x8 continuous rolling smoke (User.WispOnly)',
            'Non-blocking background warmup with instant Tier2 fallback during warmup',
            'Reused NS_StormCloudArc high-frequency branching cloud lightning',
        ],
        'gameplay_tested': False,
        'rendered': False,
    }
    for out_dir in (BATCH_ROOT, OUT):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'published.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('STORM_DOMAIN_V4_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    run()
