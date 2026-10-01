"""Author Blizzard's layered local storm cloud and spatial ice landing sound.

Only writes /Game/Skills/Blizzard/StormV2; source Normandy clouds, frost FX and
ice audio stay read-only. Execute through the serialized editor bridge or a
background commandlet. No game, audio playback or rendering.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments, save, CREATED
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_blizzard_assets import custom

DEST = '/Game/Skills/Blizzard/StormV2'
EAL = u.EditorAssetLibrary
CLOUD_PARENT = '/Game/UnrealNormandy/Materials/M_Master_StormCloud'
CLOUD_INSTANCE = '/Game/UnrealNormandy/MaterialInstances/MI_StormCloud_00A'
ICE_SOUND = '/Game/Skills/IceSpike/S_IceImpact'
TEMPLATE = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'


def own(source, name):
    path = DEST + '/' + name
    result = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not result:
        raise RuntimeError('Missing installed source: ' + source)
    return result


def cloud_material():
    material = own(CLOUD_PARENT, 'M_BlizzardStormCloud')
    if not EAL.get_metadata_tag(material, 'Blizzard.StormV2.SoftBoundary'):
        opacity = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_OPACITY)
        opacity_output = LIB.get_material_property_input_node_output_name(material, u.MaterialProperty.MP_OPACITY)
        tint = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_BASE_COLOR)
        tint_output = LIB.get_material_property_input_node_output_name(material, u.MaterialProperty.MP_BASE_COLOR)
        if not opacity or not tint:
            raise RuntimeError('Normandy cloud material outputs unavailable')
        uv = LIB.create_material_expression(material, u.MaterialExpressionTextureCoordinate)
        soft = custom(material,
                      'float2 p=(UV-.5)*2;float e=saturate((1-dot(p,p))*5);return e*e*(3-2*e);',
                      {'UV': (uv, '')})
        masked = LIB.create_material_expression(material, u.MaterialExpressionMultiply)
        LIB.connect_material_expressions(opacity, opacity_output, masked, 'A')
        LIB.connect_material_expressions(soft, '', masked, 'B')
        LIB.connect_material_property(masked, '', u.MaterialProperty.MP_OPACITY)
        # The source already multiplies opacity by ParticleColor.A, but its
        # base color is a constant parameter. Add per-layer RGB only once.
        particle = LIB.create_material_expression(material, u.MaterialExpressionParticleColor)
        colored = LIB.create_material_expression(material, u.MaterialExpressionMultiply)
        LIB.connect_material_expressions(tint, tint_output, colored, 'A')
        LIB.connect_material_expressions(particle, 'RGB', colored, 'B')
        LIB.connect_material_property(colored, '', u.MaterialProperty.MP_BASE_COLOR)
        EAL.set_metadata_tag(material, 'Blizzard.StormV2.SoftBoundary', '1')
    material.set_editor_property('two_sided', True)
    LIB.set_material_usage(material, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Cloud material compilation failed: ' + str(errors))
    save(material)
    instance = own(CLOUD_INSTANCE, 'MI_BlizzardStormCloud')
    LIB.set_material_instance_parent(instance, material)
    for name, value in {'Opacity': .88, 'Fade': 35., 'DistanceFade_Distance': 25.,
                        'DistanceFade_FallOff': 65., 'Emissive_Multiplier': 0.,
                        'Cloud_Speed': .065, 'AdditionalNoise_SpeedX': .035,
                        'AdditionalNoise_SpeedY': .07}.items():
        LIB.set_material_instance_scalar_parameter_value(instance, name, value)
    LIB.set_material_instance_vector_parameter_value(instance, 'BaseColor', u.LinearColor(1, 1, 1, 1))
    LIB.update_material_instance(instance)
    save(instance)
    return instance


def layer(system, material, name, count, spread, size_min, size_max, level, rgb, alpha, lifecycle):
    fringe = count == 0
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                        'ParticleSpawnScript': ['InitializeParticle'],
                        'ParticleUpdateScript': ['ParticleState']})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False, 'Alignment': 'Unaligned',
        'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth', 'bCastShadows': False,
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable',
    })
    for key, value in lifecycle.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    spawn = 'SpawnRate' if fringe else 'SpawnBurst_Instantaneous'
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/' + spawn)))
    if fringe:
        expression(system, name, 'EmitterUpdateScript', spawn, 'SpawnRate',
                   '7.142857*saturate(User.CloudEmission)*saturate(User.Strength)*(1-saturate(User.DetailReduction))')
    else:
        expression(system, name, 'EmitterUpdateScript', spawn, 'Spawn Count',
                   f'floor({count}*(1-saturate(User.DetailReduction)*.35)+.5)')
        put(system, name, 'EmitterUpdateScript', spawn, 'Spawn Time', '(Value=0)')
    a = 'frac(float(Particles.UniqueID)*.618033989)'
    b = 'frac(float(Particles.UniqueID)*.754877666)'
    c = 'frac(float(Particles.UniqueID)*.569840296)'
    thickness = 'min(User.RadiusY*.55,User.CloudHeight*.28)'
    width = f'User.RadiusX*({size_min}+{c}*({size_max}-{size_min}))'
    if fringe:
        width = f'min(180,max(90,User.RadiusX*.48))*(1+{c}*.2)'
    height = f'min(({width})*.65,User.CloudHeight*.4)'
    size = f'float2({width},{height})'
    radial = f'(.90+{b}*.35)' if fringe else f'sqrt({b})*{spread}'
    theta = f'({a}*6.2831853+{level}+.045*sin(Particles.Age*.65+{c}*6.2831853))'
    position = (f'User.CurrentPosition+(User.Side*cos({theta})*User.RadiusX*1.15+'
                f'User.Up*sin({theta})*User.RadiusY)*({radial})+'
                f'User.SurfaceNormal*(User.CloudHeight-({height})*.5-({thickness})*{level})')
    if fringe:
        position += '+User.Wind*Particles.Age*.15'
    lifetime = f'1.5+{c}*1.1' if fringe else 'max(.6,User.StormDuration+.6)'
    color = f'float4({rgb[0]},{rgb[1]},{rgb[2]},{alpha}*saturate(User.Strength))'
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, lifetime), 'Particles.Position': (POSITION, position),
        'Particles.SpriteSize': (VEC2, size), 'Particles.SpriteRotation': (FLOAT, f'{c}*360'),
        'Particles.Color': (COLOR, color), 'Particles.SubImageIndex': (FLOAT, '0'),
    })
    fade = 'saturate(Particles.NormalizedAge*6)*saturate((1-Particles.NormalizedAge)*4)' if fringe else '1'
    animated_color = f'float4({rgb[0]},{rgb[1]},{rgb[2]},{alpha}*saturate(User.Strength)*({fade}))'
    assignments(system, name, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, position),
        'Particles.SpriteSize': (VEC2, size + (f'*(1+Particles.NormalizedAge*.25)' if fringe else f'*(1+.025*sin(Particles.Age*.73+{c}*6.2831853))')),
        'Particles.Color': (COLOR, animated_color), 'Particles.SubImageIndex': (FLOAT, '0'),
    })


def cloud_system(material):
    source = u.load_asset(TEMPLATE)
    system = own(TEMPLATE, 'NS_BlizzardStormCloud')
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    for name, typ in [('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3),
                      ('SurfaceNormal', VEC3), ('Wind', VEC3), ('RadiusX', FLOAT), ('RadiusY', FLOAT),
                      ('CloudHeight', FLOAT), ('StormDuration', FLOAT), ('CloudEmission', FLOAT),
                      ('Strength', FLOAT), ('DetailReduction', FLOAT)]:
        user_parameter(system, name, typ)
    lifecycle = {key: u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
                 for key in ['Life Cycle Mode', 'Loop Behavior']}
    lifecycle['Life Cycle Mode'] = lifecycle['Life Cycle Mode'].replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    lifecycle['Loop Behavior'] = lifecycle['Loop Behavior'].replace('NewEnumerator0', 'NewEnumerator1').replace('"Infinite"', '"Once"')
    layer(system, material, 'DarkCloudBase', 18, 1., .55, .95, .32, (.08, .095, .125), .90, lifecycle)
    layer(system, material, 'GreyCloudBody', 14, .85, .45, .75, .18, (.14, .16, .19), .85, lifecycle)
    layer(system, material, 'LightCloudCrown', 9, .60, .35, .55, 0., (.26, .285, .32), .80, lifecycle)
    layer(system, material, 'DriftingCloudFringe', 0, 1., .45, .60, .24, (.10, .115, .14), .32, lifecycle)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1150, -1150, -120), max=u.Vector(1150, 1150, 1300)))
    save(system)
    return system


def landing_audio():
    def create(name, kind, factory):
        return u.load_asset(DEST + '/' + name) if EAL.does_asset_exist(DEST + '/' + name) else TOOLS.create_asset(name, DEST, kind, factory)
    attenuation = create('ATT_BlizzardIceLanding', u.SoundAttenuation, u.SoundAttenuationFactory())
    settings = attenuation.get_editor_property('attenuation')
    for name, value in {'attenuate': True, 'spatialize': True,
                        'attenuation_shape_extents': u.Vector(120, 0, 0), 'falloff_distance': 2000.}.items():
        settings.set_editor_property(name, value)
    attenuation.set_editor_property('attenuation', settings)
    save(attenuation)
    concurrency = create('CON_BlizzardIceLanding', u.SoundConcurrency, u.SoundConcurrencyFactory())
    settings = concurrency.get_editor_property('concurrency')
    settings.set_editor_property('max_count', 6)
    settings.set_editor_property('limit_to_owner', False)
    settings.set_editor_property('resolution_rule', u.MaxConcurrentResolutionRule.PREVENT_NEW)
    concurrency.set_editor_property('concurrency', settings)
    save(concurrency)
    sound = own(ICE_SOUND, 'S_BlizzardIceLanding')
    sound.set_editor_property('looping', False)
    sound.set_editor_property('attenuation_settings', attenuation)
    sound.set_editor_property('override_concurrency', False)
    sound.set_editor_property('concurrency_set', {concurrency})
    save(sound)
    return sound


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved Blizzard StormV2 assets')
    EAL.make_directory(DEST)
    material = cloud_material()
    system = cloud_system(material)
    sound = landing_audio()
    receipt = {'saved_assets': list(CREATED), 'cloud_source': CLOUD_PARENT, 'cloud_instance_source': CLOUD_INSTANCE,
               'cloud_mask': '/Game/UnrealNormandy/Textures/T_Particle_Cloud_00A_Masks',
               'cloud_system': system.get_path_name(), 'core_layers': [18, 14, 9], 'core_max': 41,
               'fringe_max_approx': 19, 'systems_per_zone': 3, 'audio_source': ICE_SOUND,
               'landing_audio': sound.get_path_name(), 'max_landing_voices': 6,
               'gameplay_tested': False, 'rendered': False, 'audio_played': False}
    folder = ROOT / 'Saved/BlizzardCloud20261001'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('BLIZZARD_STORM_V2_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
