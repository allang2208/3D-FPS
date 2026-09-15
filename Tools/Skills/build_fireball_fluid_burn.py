"""Install the original baked-combustion fireball and its secondary layers.

UE Python asset authoring/compilation only. No gameplay or preview run.
Run after SourceAssets/FireballFluidBurn20260914/pack_fluid_atlases.py.
"""
import json
import shutil
import sys
from pathlib import Path
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_slow_burn import smooth
from build_fireball_outer_flame import enable_sprite_usage, connect, scalar, multiply

ROOT = Path(unreal.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/FireballFluidBurn20260914'
DEST = '/Game/Skills/Fireball/FluidBurn20260914'
CORE = '/Game/Skills/Fireball/NS_FireballSlowBurnCore'
TRAIL = '/Game/Skills/Fireball/NS_FireballVelocityTrail'


def own_copy(source, name):
    path = DEST + '/' + name
    return unreal.load_asset(path) or unreal.EditorAssetLibrary.duplicate_asset(source, path)


def import_atlas(label):
    name = 'T_FireballFluid_' + label
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(SOURCE / 'Textures' / (name + '.png')),
                           destination_path=DEST, destination_name=name,
                           automated=True, replace_existing=True, save=True).items():
        task.set_editor_property(key, value)
    TOOLS.import_asset_tasks([task])
    texture = unreal.load_asset(DEST + '/' + name)
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_BC7)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_EFFECTS)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    save(texture)
    return texture


def compensate_emission(material, emission):
    inverse = LIB.create_material_expression(material, unreal.MaterialExpressionEyeAdaptationInverse, 160, -160)
    connect(emission, inverse, str(LIB.get_material_expression_input_names(inverse)[0]))
    return inverse


def moving_translucency(material, clip=.035):
    # Keep scene depth: UE 5.8's AfterMotionBlur pass disables depth testing.
    # DepthFade samples SceneDepth, which cannot coexist with translucent depth/
    # velocity output in this engine. NullRHI compilation does not reveal that conflict.
    material.set_editor_property('translucency_pass', unreal.MaterialTranslucencyPass.MTP_AFTER_DOF)
    material.set_editor_property('output_translucent_velocity', False)
    material.set_editor_property('is_translucency_velocity_from_depth', False)
    material.set_editor_property('opacity_mask_clip_value', clip)
    material.set_editor_property('enable_responsive_aa', True)  # TAA fallback; TSR uses AfterDOF.
    material.set_editor_property('disable_depth_test', False)


def combustion_material(texture, label):
    name = 'M_FireballFluid_' + label
    mat = unreal.load_asset(DEST + '/' + name) or TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ALPHA_COMPOSITE)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    enable_sprite_usage(mat)
    moving_translucency(mat)
    tex = LIB.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameterSubUV, -800, 0)
    tex.set_editor_property('parameter_name', 'CombustionAtlas')
    tex.set_editor_property('texture', texture)
    tex.set_editor_property('blend', True)
    tex.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    particle = LIB.create_material_expression(mat, unreal.MaterialExpressionParticleColor, -800, 220)
    gain = scalar(mat, 'EmissionGain', 2.0, -450, -180)
    opacity = scalar(mat, 'CoverageGain', .82, -450, 480)
    coverage = LIB.create_material_expression(mat, unreal.MaterialExpressionMultiply, -450, 260)
    connect(tex, coverage, 'A', str(LIB.get_material_expression_output_names(tex)[4]))
    connect(particle, coverage, 'B', str(LIB.get_material_expression_output_names(particle)[4]))
    coverage_gain = multiply(mat, coverage, opacity, -150, 260)
    fade = LIB.create_material_expression(mat, unreal.MaterialExpressionDepthFade, 80, 260)
    fade.set_editor_property('fade_distance_default', 6.0)
    connect(coverage_gain, fade, str(LIB.get_material_expression_input_names(fade)[0]))
    rgb = multiply(mat, tex, particle, -450, 0)
    bright = multiply(mat, rgb, gain, -150, 0)
    # The old Epic parent compensated emissive for the gameplay camera's
    # exposure. Raw 0..2 luminance becomes a black alpha silhouette in daylight.
    exposed = compensate_emission(mat, bright)
    premultiplied = multiply(mat, exposed, fade, 300, 0)
    LIB.connect_material_property(premultiplied, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(fade, '', unreal.MaterialProperty.MP_OPACITY)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError('Combustion material build failed: ' + '; '.join(errors))
    save(mat)
    return mat


def secondary_materials():
    flame = own_copy('/Game/Skills/Fireball/MI_FireballOuterFireFlame', 'MI_FluidShortFlames')
    flame_parent = own_copy('/Game/Skills/Fireball/M_FireballOuterFireFlame', 'M_FluidShortFlamesExposure')
    if not any(isinstance(node, unreal.MaterialExpressionEyeAdaptationInverse) for node in LIB.get_material_expressions(flame_parent)):
        output = LIB.get_material_property_input_node(flame_parent, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        corrected = compensate_emission(flame_parent, output)
        if not LIB.connect_material_property(corrected, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError('Cannot connect short-flame exposure correction')
    enable_sprite_usage(flame_parent)
    moving_translucency(flame_parent)
    LIB.recompile_material(flame_parent)
    save(flame_parent)
    LIB.set_material_instance_parent(flame, flame_parent)
    for key, value in [('OpacityGain', .48), ('EmissiveGain', 1.35)]:
        LIB.set_material_instance_scalar_parameter_value(flame, key, value)
    haze = heat_halo_material()
    smoke = own_copy('/Game/NiagaraExamples/Materials/MI_SmokeWispy_8x8_Emissive', 'MI_FluidThinWisp')
    source_smoke = unreal.load_asset('/Game/NiagaraExamples/Materials/MI_SmokeWispy_8x8_Emissive')
    smoke_parent = own_copy(source_smoke.get_editor_property('parent').get_path_name(), 'M_FluidThinWispMotion')
    moving_translucency(smoke_parent, .003)
    enable_sprite_usage(smoke_parent)
    LIB.recompile_material(smoke_parent)
    save(smoke_parent)
    LIB.set_material_instance_parent(smoke, smoke_parent)
    for key, value in [('Opacity Gain', .18), ('Emissive Gain', .03),
                       ('Near Fade Distance', 10), ('Depth Fade Distance', 8),
                       ('Opacity Clip Value', 0), ('SubUV Speed', .45)]:
        LIB.set_material_instance_scalar_parameter_value(smoke, key, value)
    for key in ['Use Material SubUV', 'Use Particle Alpha As Threshold']:
        if key in {str(name) for name in LIB.get_static_switch_parameter_names(smoke)}:
            LIB.set_material_instance_static_switch_parameter_value(smoke, key, False)
    for material in [flame, smoke]:
        LIB.set_material_usage_override(material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True, True)
        LIB.update_material_instance(material)
        save(material)
    return flame, haze, smoke


def heat_halo_material():
    name = 'M_FluidHoverHeatHalo'
    mat = unreal.load_asset(DEST + '/' + name) if unreal.EditorAssetLibrary.does_asset_exist(DEST + '/' + name) else TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    for key, value in {
        'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
        'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
        'two_sided': True, 'disable_depth_test': False,
        'refraction_method': unreal.RefractionMode.RM_INDEX_OF_REFRACTION,
        'translucency_pass': unreal.MaterialTranslucencyPass.MTP_BEFORE_DOF,
        'refraction_depth_bias': 1.5, 'enable_responsive_aa': True,
        'output_translucent_velocity': False,
    }.items():
        mat.set_editor_property(key, value)
    enable_sprite_usage(mat)

    def node(cls, **values):
        result = LIB.create_material_expression(mat, cls)
        for key, value in values.items():
            result.set_editor_property(key, value)
        return result

    def custom(code, inputs, kind=unreal.CustomMaterialOutputType.CMOT_FLOAT1):
        pins = []
        for key in inputs:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', key)
            pins.append(pin)
        result = node(unreal.MaterialExpressionCustom, code=code, output_type=kind, inputs=pins)
        for key, (source, output) in inputs.items():
            LIB.connect_material_expressions(source, output, result, key)
        return result

    uv = node(unreal.MaterialExpressionTextureCoordinate)
    time = node(unreal.MaterialExpressionTime)
    particle = node(unreal.MaterialExpressionParticleColor)
    strength = node(unreal.MaterialExpressionScalarParameter, parameter_name='HeatStrength', default_value=.035)
    # Same locally owned noise and IOR mechanism as WristRiftV3/M_RuneRift.
    noise = unreal.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A')
    if not noise:
        raise RuntimeError('Missing sword-rift noise normal')
    noise_uv = custom('return UV*float2(2.2,2.6)+float2(Time*.14,-Time*.38);',
                      {'UV': (uv, ''), 'Time': (time, '')}, unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    sample = node(unreal.MaterialExpressionTextureSample, texture=noise, sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    LIB.connect_material_expressions(noise_uv, '', sample, 'UVs')
    mask = custom('float2 p=UV-.5; float r=length(p)+.018*N.x; '
                  'float band=smoothstep(.19,.30,r)*(1-smoothstep(.37,.49,r)); '
                  'return band*(.70+.30*saturate(N.y*.5+.5))*Alpha;',
                  {'UV': (uv, ''), 'N': (sample, 'RGB'), 'Alpha': (particle, 'A')})
    fade = node(unreal.MaterialExpressionDepthFade, fade_distance_default=12.)
    connect(mask, fade, str(LIB.get_material_expression_input_names(fade)[0]))
    normal = custom('return normalize(float3(N.xy*.45,max(.35,N.z)));',
                    {'N': (sample, 'RGB')}, unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    ior = custom('return 1+Mask*Strength;', {'Mask': (fade, ''), 'Strength': (strength, '')})
    opacity = custom('return Mask*.025;', {'Mask': (fade, '')})
    for expr, prop in [(normal, unreal.MaterialProperty.MP_NORMAL), (ior, unreal.MaterialProperty.MP_REFRACTION),
                       (opacity, unreal.MaterialProperty.MP_OPACITY)]:
        LIB.connect_material_property(expr, '', prop)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError('Heat halo material build failed: ' + '; '.join(errors))
    save(mat)
    return mat


def heat_halo_layer(system, material, lifecycle):
    name = 'FireballHoverHeatHalo'
    emitter(system, name, material, lifecycle, 1.25, .5, False)
    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    age, n = 'Particles.Age', 'Particles.NormalizedAge'
    fade = smooth('0', '.18', n) + '*(1-' + smooth('.64', '1', n) + ')'
    hover = '(1-saturate(User.Flight)*' + smooth('.04', '.22', 'User.FlightAge') + ')'
    common = {
        'Particles.Position': (POSITION, f'float3(0,0,6+{age}*2)'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteAlignment': (VEC3, 'float3(0,0,1)'),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, f'float2(60,68)*(1+.025*sin({age}*2.1+{seed}*6.28))'),
        'Particles.SubImageIndex': (FLOAT, '0'),
        'Particles.Color': (COLOR, f'float4(1,1,1,.70*{fade}*{hover})'),
    }
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, '1.6'), **common})
    assignments(system, name, 'ParticleUpdateScript', common)


def emitter(system, name, material, lifecycle, rate, pivot=.5, atlas=True, local=True):
    if name not in emitters(system):
        API.call_method('AddEmitter', (system, unreal.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
                        'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        unreal.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', unreal.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': local, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', unreal.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8 if atlas else 1, 'Y': 8 if atlas else 1}, 'bSubImageBlend': atlas,
        'Alignment': 'CustomAlignment', 'FacingMode': 'FaceCamera',
        'PivotInUVSpace': {'X': .5, 'Y': pivot}, 'bCastShadows': False,
        # NE_Core carries an explosion-specific octagonal cutout. Its geometry
        # clips these unrelated flame atlases even when their alpha is valid.
        'bUseMaterialCutoutTexture': False, 'CutoutTexture': None,
        'MotionVectorSetting': 'Precise',
    })
    for key, value in lifecycle.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    topology = API.call_method('GetScriptStackTopology', (ref(system, name, 'EmitterUpdateScript'),))
    if not any(str(module.get_editor_property('module_name')) == 'SpawnRate' for module in topology.get_editor_property('modules')):
        API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), unreal.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(Value=' + str(rate) + ')')


def core_layer(system, name, material, lifecycle, kind):
    body, outer, smoke = kind in ['A', 'B'], kind == 'flame', kind == 'smoke'
    rate = {'A': 2.1, 'B': 1.7, 'flame': 6, 'smoke': 1.3, 'haze': 1.5}[kind]
    emitter(system, name, material, lifecycle, rate, .71 if body else (.82 if outer else .5), kind != 'haze')
    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    variant = 'frac(float(Particles.UniqueID)*.41421356237)'
    phase = f'(6.2831853*{variant})'
    age, n = 'Particles.Age', 'Particles.NormalizedAge'
    blend = smooth('0', '.06', 'User.FlightAge') + '*saturate(User.Flight)'
    rise = 0 if body else (9 if outer else 16)
    radius = 2.0 if body else (6 if outer else 3)
    root = f'float3(cos({phase})*{radius},sin({phase})*{radius},{age}*{rise})'
    if not body:
        root += f'+float3(1.5*sin({age}*3.1+{phase}),1.2*sin({age}*2.3+{phase}),0)'
    rear = f'float3(-3-{n}*' + ('9' if body else ('18' if outer else '26')) + f',cos({phase})*{radius},sin({phase})*{radius})'
    axis = f'normalize(lerp(float3(.12*cos({phase}),.12*sin({phase}),1),float3(-1,0,0),{blend}))'
    size = f'float2(38+4*{seed},40+4*{variant})' if body else (
        f'float2(9+4*{seed},13+7*{variant})' if outer else f'float2(20+8*{seed},25+6*{variant})')
    if outer:
        size += f'*(1-.30*{n})'
    elif not body:
        size += f'*(.75+.45*{n})'
    alpha = '.72' if kind == 'A' else ('.52' if kind == 'B' else ('.52' if outer else '.12'))
    envelope = smooth('0', '.16', n) + '*(1-' + smooth('.55', '1', n) + ')'
    common = {
        'Particles.Position': (POSITION, f'lerp({root},{rear},{blend})'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteAlignment': (VEC3, axis),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SubImageIndex': (FLOAT, f'fmod({variant}*64+{age}*(22+4*{seed}),64)' if kind != 'haze' else '0'),
        'Particles.Color': (COLOR, f'float4(' + ('.40,.30,.22' if smoke else '1,1,1') + f',{alpha}*{envelope})'),
        'Particles.DynamicMaterialParameter': ('/Script/CoreUObject.Vector4f', 'float4(1,1,1,1)'),
    }
    life = f'.85+.35*{seed}' if body else (f'.38+.28*{seed}' if outer else f'.6+.25*{seed}')
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, life), **common})
    assignments(system, name, 'ParticleUpdateScript', common)


def update_trail(system, material, lifecycle):
    name = 'RocketTrail'
    emitter(system, name, material, lifecycle, 1, .70, True, False)
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="clamp(User.FlightSpeed/14,0,240)")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    n = 'Particles.NormalizedAge'
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'.08+.055*{seed}'),
        'Particles.Position': (POSITION, f'lerp(User.PreviousPosition,User.CurrentPosition,{seed})'),
        'Particles.Velocity': (VEC3, '-User.FlightDirection*55'),
        'Particles.SpriteAlignment': (VEC3, '-User.FlightDirection'),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, f'float2(16+5*{seed},26+6*{seed})'),
        'Particles.SubImageIndex': (FLOAT, f'{seed}*64'),
        'Particles.Color': (COLOR, 'float4(1,1,1,.38)'),
    })
    assignments(system, name, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize': (VEC2, f'float2(16+5*{seed},26+6*{seed})*(1-.65*{n})'),
        'Particles.SubImageIndex': (FLOAT, f'fmod({seed}*64+Particles.Age*26,64)'),
        'Particles.Color': (COLOR, f'float4(1,lerp(1,.55,{n}),lerp(1,.35,{n}),.38*(1-{n})*(1-{n}))'),
    })
    save(system)


def build():
    unreal.EditorAssetLibrary.make_directory(DEST)
    materials = [combustion_material(import_atlas(label), label) for label in ['A', 'B']]
    short_flame, haze, smoke = secondary_materials()
    system = unreal.load_asset(CORE)
    source_emitter = emitters(system)[0]
    lifecycle = {key: unreal.RainAssetEditor.read_input(system, source_emitter, 'EmitterUpdateScript', 'EmitterState', key)
                 for key in ['Life Cycle Mode', 'Loop Behavior']}
    backup = ROOT / 'trash/skills-magic-20260915/SourceAssets/FireballFluidBurn20260914/BeforeFluidBurn'
    backup.mkdir(parents=True, exist_ok=True)
    for name in ['NS_FireballSlowBurnCore', 'NS_FireballVelocityTrail']:
        target = backup / (name + '.uasset')
        if not target.exists():
            shutil.copy2(ROOT / 'Content/Skills/Fireball' / (name + '.uasset'), target)
    # The runtime paths remain stable; replace only the fireball presentation.
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    for name, material, kind in [('FireballFluidBodyA', materials[0], 'A'),
                                  ('FireballFluidBodyB', materials[1], 'B'),
                                  ('FireballFluidShortFlames', short_flame, 'flame'),
                                  ('FireballFluidThinWisp', smoke, 'smoke')]:
        core_layer(system, name, material, lifecycle, kind)
    heat_halo_layer(system, haze, lifecycle)
    system.set_editor_property('fixed_bounds', unreal.Box(min=unreal.Vector(-85,-55,-45), max=unreal.Vector(55,55,75)))
    save(system)
    update_trail(unreal.load_asset(TRAIL), materials[1], lifecycle)
    (SOURCE / 'integration.json').write_text(json.dumps({
        'runtime_core': CORE, 'runtime_trail': TRAIL,
        'original_simulation': 'author_fluid.py / Fireball_Fluid_Editable.blend / Cache',
        'atlas_bake': 'pack_fluid_atlases.py / Textures / atlas.json',
        'textures_and_materials': DEST,
        'body': 'Two original combustion views, offset phases, independent RGBA coverage; old round FireBall sprite removed',
        'hover': 'Baked buoyant rolling flame, small independent source offsets, short uneven outer tongues',
        'flight': 'All upward texture axes rotate to local -X over the existing 60 ms handoff; world-space trail retains birth direction',
        'trail': '8-13.5 centiseconds, 14 cm spacing, cap 240 particles/sec, variable short broken flames',
        'secondary': 'Sparse thin smoke and hover-only annular sword-rift heat refraction; fades out by 220 ms after launch',
        'motion': 'AfterDOF and TAA ResponsiveAA; precise Niagara vectors retained, material velocity output disabled for DepthFade compatibility',
        'emissive_exposure': 'Body and short flames use EyeAdaptationInverse; opacity/depth fade stay independent',
        'sprite_cutout': 'Inherited explosion CutoutTexture cleared on every core/trail renderer; flame alpha controls coverage',
        'dependencies': ['Epic Niagara Examples emitter templates and thin smoke', 'Dr.Game Free Spline VFX short flame texture and project material', 'Realistic Starter VFX Pack Vol2 T_NoiseNormal_A, as used by RuneSword WristRiftV3'],
        'authoring_backup': 'trash/skills-magic-20260915/SourceAssets/FireballFluidBurn20260914/BeforeFluidBurn/*.uasset',
        'gameplay': 'No changes to gestures, collision, damage, costs, progression, save or quickbar',
        'status': 'Assets authored, imported and compiled; no gameplay/visual acceptance or automated tests',
    }, indent=2), encoding='utf-8')
    unreal.log('FIREBALL_FLUID_BURN_INSTALLED')


if __name__ == '__main__':
    build()
