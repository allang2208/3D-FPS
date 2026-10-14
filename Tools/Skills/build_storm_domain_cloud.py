"""Author StormDomainV2 only: dense clouds bounded by runtime room clearance.

Run with the background Python commandlet or serialized existing editor bridge.
Normandy/Blizzard materials and the previous electric cloud stay read-only.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments, save, CREATED
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_blizzard_assets import custom
from build_electric_magic_assets import lifecycle, sprite, ENUM, TEMPLATE, SEED, SEED2, SEED3

DEST = '/Game/Skills/ElectricMagic/StormDomainV2'
EAL = u.EditorAssetLibrary


def own(source, name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Missing cloud source: ' + source)
    return asset


def dense_material():
    material = own('/Game/Skills/Blizzard/StormV2/M_BlizzardStormCloud', 'M_StormDomainCloud')
    if not EAL.get_metadata_tag(material, 'StormDomainV2.DenseOpacity'):
        node = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_OPACITY)
        output = LIB.get_material_property_input_node_output_name(material, u.MaterialProperty.MP_OPACITY)
        # Optical density, rather than extra stacked emitters. Keep the inherited
        # soft boundary and subtractive noise; zero-alpha texels remain transparent.
        density = custom(material, 'return 1-pow(1-saturate(A),1.85);', {'A': (node, output)})
        LIB.connect_material_property(density, '', u.MaterialProperty.MP_OPACITY)
        EAL.set_metadata_tag(material, 'StormDomainV2.DenseOpacity', '1.85')
    material.set_editor_property('disable_depth_test', False)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Storm cloud material compilation: ' + str(errors))
    save(material)
    instance = own('/Game/Skills/Blizzard/StormV2/MI_BlizzardStormCloud', 'MI_StormDomainCloud')
    LIB.set_material_instance_parent(instance, material)
    for name, value in {'Opacity': .98, 'Fade': 8., 'DistanceFade_Distance': 12.,
                        'DistanceFade_FallOff': 24., 'Cloud_Speed': .045,
                        'AdditionalNoise_SpeedX': .026, 'AdditionalNoise_SpeedY': .052,
                        'Emissive_Multiplier': .025}.items():
        LIB.set_material_instance_scalar_parameter_value(instance, name, value)
    LIB.update_material_instance(instance)
    save(instance)
    return instance


def cloud_layer(system, material, name, count, spread, size_min, size_max, level, rgb, alpha):
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                        'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        # World-up facing and zero roll keep even very wide billboards below the
        # ceiling. Random sprite rotation used to rotate their full width upward.
        'Alignment': 'Unaligned', 'FacingMode': 'FaceCameraPosition', 'SortMode': 'ViewDepth',
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'bCastShadows': False,
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable',
    })
    for key, value in lifecycle().items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value, ENUM)
    expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    fringe = count == 0
    spawn = 'SpawnRate' if fringe else 'SpawnBurst_Instantaneous'
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/' + spawn)))
    expression(system, name, 'EmitterUpdateScript', spawn, 'SpawnRate' if fringe else 'Spawn Count',
               '4*saturate(User.CloudEmission)*saturate(User.Strength)*(1-saturate(User.DetailReduction))' if fringe else
               f'floor({count}*(1-saturate(User.DetailReduction)*.35)+.5)')
    if not fringe:
        put(system, name, 'EmitterUpdateScript', spawn, 'Spawn Time', '(Value=0)')
    width = f'min(User.RadiusX,User.RadiusY)*({size_min}+{SEED3}*({size_max}-{size_min}))'
    height = f'min(({width})*.62,max(4,User.CloudThickness)*.72)'
    theta = f'({SEED}*6.2831853+{level}+.065*sin(Particles.Age*.48+{SEED3}*6.2831853))'
    radial = f'sqrt({SEED2})*{spread}'
    # Entire vertical billboard extent remains inside [CloudHeight-Thickness, CloudHeight].
    position = (f'User.CurrentPosition+(User.Side*cos({theta})*User.RadiusX+'
                f'User.Up*sin({theta})*User.RadiusY)*({radial})+'
                f'User.SurfaceNormal*(User.CloudHeight-({height})*.5-(User.CloudThickness-({height}))*{level})')
    size = f'float2({width},{height})'
    fade = 'saturate(Particles.NormalizedAge*6)*saturate((1-Particles.NormalizedAge)*4)' if fringe else '1'
    color = f'float4({rgb[0]},{rgb[1]},{rgb[2]},{alpha}*saturate(User.Strength)*({fade}))'
    common = {'Particles.Position': (POSITION, position), 'Particles.SpriteSize': (VEC2, size),
              'Particles.SpriteRotation': (FLOAT, '0'), 'Particles.Color': (COLOR, color),
              'Particles.SubImageIndex': (FLOAT, '0')}
    assignments(system, name, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, f'1.3+{SEED3}*.7' if fringe else 'max(.6,User.StormDuration+.6)'), **common})
    assignments(system, name, 'ParticleUpdateScript', common)


def build_cloud(filament=None, spark=None):
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved StormDomainV2 assets')
    EAL.make_directory(DEST)
    material = dense_material()
    system = own(TEMPLATE, 'NS_StormDomainCloud')
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)
    for name, typ in [('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3),
                      ('SurfaceNormal', VEC3), ('RadiusX', FLOAT), ('RadiusY', FLOAT),
                      ('CloudHeight', FLOAT), ('CloudThickness', FLOAT), ('StormDuration', FLOAT),
                      ('CloudEmission', FLOAT), ('Strength', FLOAT), ('DetailReduction', FLOAT)]:
        user_parameter(system, name, typ)
    # Keep 48 persistent core sprites; fill the centre with overlapping charcoal
    # lobes and use slate edges rather than washing the entire cloud blue.
    cloud_layer(system, material, 'DenseDarkBase', 18, .45, .92, 1.08, .90, (.065, .080, .105), .98)
    cloud_layer(system, material, 'RollingCloudBody', 14, .48, .78, 1.04, .56, (.12, .15, .20), .94)
    cloud_layer(system, material, 'SlateCloudCrown', 10, .40, .68, .94, .14, (.23, .28, .35), .88)
    cloud_layer(system, material, 'ElectricCloudRim', 6, .42, .52, .82, .35, (.30, .40, .53), .76)
    cloud_layer(system, material, 'SoftCloudFringe', 0, .64, .36, .66, .65, (.09, .12, .17), .38)
    filament = filament or u.load_asset('/Game/Skills/ElectricMagic/M_ElectricFilament')
    spark = spark or u.load_asset('/Game/Skills/ElectricMagic/M_ElectricSpark')
    if not filament or not spark:
        raise RuntimeError('Restore the shared electric filament/spark materials first')
    emission = 'saturate(User.CloudEmission)*saturate(User.Strength)*(1-saturate(User.DetailReduction))'
    theta = f'{SEED}*6.2831853'
    position = (f'User.CurrentPosition+User.Side*cos({theta})*User.RadiusX*.4+'
                f'User.Up*sin({theta})*User.RadiusY*.4+'
                f'User.SurfaceNormal*(User.CloudHeight-User.CloudThickness*(.45+{SEED2}*.35))')
    sprite(system, 'CloudDischarges', filament, rate=f'16*{emission}', life=.16, position=position,
           size=f'float2(min(User.RadiusX,User.RadiusY)*(.16+{SEED3}*.18),min(7,User.CloudThickness*.12))',
           color='float4(.50,.69,1,User.Strength)', rotation='0', loop_seconds='max(.6,User.StormDuration+.6)')
    sprite(system, 'FallingElectricSparks', spark, rate=f'10*{emission}', life=.4,
           position=position+'-User.SurfaceNormal*Particles.Age*55',
           size='float2(2,min(9,User.CloudThickness*.15))', color='float4(.35,.57,1,User.Strength)',
           rotation='0', loop_seconds='max(.6,User.StormDuration+.6)')
    for name in ('CloudDischarges', 'FallingElectricSparks'):
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name), {'bLocalSpace': False})
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0),
                {'FacingMode': 'FaceCameraPosition', 'Alignment': 'Unaligned'})
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1600, -1600, -120), max=u.Vector(1600, 1600, 450)))
    EAL.set_metadata_tag(system, 'Electric.Source', 'StormDomainV2: 48 dense cloud lobes; room-adaptive thickness; bounded fringe and discharges')
    save(system)
    receipt = {'saved_assets': [p for p in CREATED if p.startswith(DEST)], 'core_particles': 48,
               'fringe_max_approx': 8, 'discharge_max_approx': 3, 'spark_max_approx': 4,
               'opacity_density': 1.85, 'gameplay_tested': False, 'rendered': False}
    folder = ROOT / 'Saved/StormDomainUpgrade20261012'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('STORM_DOMAIN_SAVED ' + json.dumps(receipt))
    return system


if __name__ == '__main__':
    build_cloud()
