"""Author StormDomainV3: compact, dense, non-hollow overhead storm cloud for lightning domain.

Derived directly from the user-approved Blizzard ChargedV3 Normandy cloud recipe
(/Game/Skills/Blizzard/ChargedV3/M_BlizzardStormCloud & MI_BlizzardStormCloud):
  1. Continuous scrolling Normandy storm-cloud texture (T_Particle_Cloud_00A_Masks) at
     dense ChargedV3 opacity (Opacity=1.65, Fade=12, DistanceFade=8/18 cm).
  2. ChargedV3's Unaligned + FaceCamera billboards with zero roll and Dynamic emitter
     bounds (eliminates RollingV1's broken CustomAlignment/ShapeVector binding and
     overhead edge-on hollowing).
  3. Compact overhead envelope tuned for personal storm-domain cloud (~4.6m diameter at
     Lv1 to ~6.4m at Lv20 when paired with FPSElectricMagicComponent's decoupled visual
     radius), while maintaining 26 overlapping zenith lobes (r=0) and zero hollow gaps.
  4. SystemState Loop Duration matched to max(0.6, User.StormDuration + 0.6).
  5. Removes the legacy flat 2D M_ElectricFilament CloudDischarges emitter (replaced by
     high-frequency, branching runtime NS_LightningChain arcs attached to the cloud in
     FPSElectricMagicComponent / AFPSLightningArc), while harmonizing FallingElectricSparks
     with NS_LightningChain's violet-blue lightning palette.

Writes only /Game/Skills/ElectricMagic/StormDomainV3. Source Blizzard/Normandy/Electric
assets remain untouched. Run via UnrealEditor-Cmd -run=pythonscript -unattended -NullRHI
or the serialized editor MCP bridge.
"""
import hashlib
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments, save, CREATED
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_electric_magic_assets import lifecycle, sprite, ENUM, TEMPLATE, SEED, SEED2, SEED3

DEST = '/Game/Skills/ElectricMagic/StormDomainV3'
SOURCE_PARENT = '/Game/Skills/Blizzard/ChargedV3/M_BlizzardStormCloud'
SOURCE_INSTANCE = '/Game/Skills/Blizzard/ChargedV3/MI_BlizzardStormCloud'
BATCH_ROOT = Path(r'F:\FPSGAMEData\ArtProduction\StormDomainCloud\StormDomainV3-20261126')
AUTHOR_DIR = ROOT / 'SourceAssets/StormDomainCloudV3_20261126'
EAL = u.EditorAssetLibrary
REVISION = 'StormDomainV3_TightCloud_20261126'

# 49 persistent core sprites (exact ChargedV3 budget), tightened so the full visual outer
# boundary stays cleanly inside ~1.0x User.RadiusX/Y with 26 zenith-overlapping lobes:
#   (name, count, spread, rad_exp, size_min, size_max, level, rgb, alpha, swirl_dir)
CORE_LAYERS = [
    ('CloudShadowBase', 14, 0.44, 0.85, 0.74, 1.08, 0.92, (0.048, 0.056, 0.082), 1.00, -1.0),
    ('CloudBody',       15, 0.56, 0.72, 0.72, 1.06, 0.52, (0.105, 0.122, 0.162), 0.98,  1.0),
    ('CloudCrown',      12, 0.50, 0.70, 0.68, 1.00, 0.10, (0.190, 0.215, 0.265), 0.94,  1.0),
    ('CloudLowerRoll',   8, 0.60, 0.65, 0.66, 0.98, 0.74, (0.115, 0.135, 0.220), 0.90, -1.0),
]


def own(source, name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Missing StormDomainV3 authoring source: ' + source)
    return asset


def cloud_material():
    material = own(SOURCE_PARENT, 'M_StormDomainCloud')
    material.set_editor_property('two_sided', True)
    material.set_editor_property('disable_depth_test', False)
    material.set_editor_property('output_translucent_velocity', False)
    LIB.set_material_usage(material, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('StormDomainV3 cloud material compilation failed: ' + str(errors))
    save(material)

    instance = own(SOURCE_INSTANCE, 'MI_StormDomainCloud')
    LIB.set_material_instance_parent(instance, material)
    for name, value in {
        'Opacity': 1.65,
        'Fade': 12.0,
        'DistanceFade_Distance': 8.0,
        'DistanceFade_FallOff': 18.0,
        'Cloud_Speed': 0.065,
        'AdditionalNoise_SpeedX': 0.035,
        'AdditionalNoise_SpeedY': 0.070,
        'CloudBig_Tiling': 0.5,
        'AdditionalNoise_Tiling': 2.0,
        'AdditionalNoiseMultiplier': 1.0,
        'AdditionalNoisePower': 1.0,
        'CloudBig_Brightness': 1.0,
        'CloudBig_Power': 2.0,
        'CloudMid_Brightness': 1.0,
        'CloudMid_Power': 1.0,
        'Cloud_Contribution': 1.0,
        'Emissive_Multiplier': 0.015,
    }.items():
        LIB.set_material_instance_scalar_parameter_value(instance, name, value)
    LIB.set_material_instance_vector_parameter_value(instance, 'BaseColor', u.LinearColor(1.0, 1.0, 1.0, 1.0))
    LIB.update_material_instance(instance)
    save(instance)
    return material, instance


def add_core_layer(system, mat, spec, lc):
    name, count, spread, rad_exp, size_min, size_max, level, rgb, alpha, swirl_dir = spec
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {
        'EmitterUpdateScript': ['EmitterState'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
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
    for key, value in lc.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value, ENUM)
    expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    expression(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
               f'floor({count}*(1-saturate(User.DetailReduction)*.25)+.5)')
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')

    seed = f'(float(Particles.UniqueID)+{level}*29.7)'
    a, b, c = [f'frac({seed}*{v})' for v in ('.618033989', '.754877666', '.569840296')]
    width = f'min(User.RadiusX,User.RadiusY)*({size_min}+{c}*{round(size_max - size_min, 4)})'
    height = f'min(({width})*.66,max(6,User.CloudThickness)*.70)'
    swirl = f'Particles.Age*(.042+{b}*.028)*({swirl_dir})+.065*sin(Particles.Age*.55+{c}*6.2831853)'
    theta = f'({a}*6.2831853+{round(level * 2.1, 4)}+{swirl})'
    radial = f'pow(max(.0001,{b}),{rad_exp})*{spread}'
    # Keep entire vertical sprite span inside [CloudHeight - CloudThickness, CloudHeight].
    z = f'User.CloudHeight-({height})*.5-max(0,User.CloudThickness-({height}))*{level}'
    pos = (f'User.CurrentPosition+(User.Side*cos({theta})*User.RadiusX+'
           f'User.Up*sin({theta})*User.RadiusY)*({radial})+User.SurfaceNormal*({z})')
    size = f'float2(({width})*(1+.030*sin(Particles.Age*.65+{c}*6.2831853)),{height})'
    fade_in = 'saturate(Particles.Age*5)'
    color = f'float4({rgb[0]},{rgb[1]},{rgb[2]},{alpha}*saturate(User.Strength)*({fade_in}))'

    common = {
        'Particles.Position': (POSITION, pos),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.Color': (COLOR, color),
        'Particles.SubImageIndex': (FLOAT, '0'),
    }
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, 'max(.6,User.StormDuration+.6)'),
        **common,
    })
    assignments(system, name, 'ParticleUpdateScript', common)


def build_cloud(filament=None, spark=None):
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved StormDomainV3 assets')
    EAL.make_directory(DEST)
    mat_parent, mat_inst = cloud_material()

    system = own(TEMPLATE, 'NS_StormDomainCloud')
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            EAL.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)

    for name, typ in [
        ('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3),
        ('SurfaceNormal', VEC3), ('Wind', VEC3),
        ('RadiusX', FLOAT), ('RadiusY', FLOAT),
        ('CloudHeight', FLOAT), ('CloudThickness', FLOAT),
        ('StormDuration', FLOAT), ('CloudEmission', FLOAT),
        ('Strength', FLOAT), ('DetailReduction', FLOAT),
    ]:
        user_parameter(system, name, typ)

    expression(system, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration',
               'max(.6,User.StormDuration+.6)')

    lc = lifecycle()
    for spec in CORE_LAYERS:
        add_core_layer(system, mat_inst, spec, lc)

    # Cloud-attached bolts now reuse the approved NS_LightningChain spline ribbon system
    # directly at runtime (AFPSLightningArc::InitializeCloudArc), so the flat 2D
    # CloudDischarges filament emitter is removed. Keep subtle violet-blue sparks
    # shedding out of the storm belly to match NS_LightningChain's electric palette.
    spark = spark or u.load_asset('/Game/Skills/ElectricMagic/M_ElectricSpark')
    if not spark:
        raise RuntimeError('Missing shared electric spark material in /Game/Skills/ElectricMagic')

    emission = 'saturate(User.CloudEmission)*saturate(User.Strength)*(1-saturate(User.DetailReduction))'
    theta = f'{SEED}*6.2831853'
    radial = f'sqrt(max(.0001,{SEED2}))*.52'
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
    EAL.set_metadata_tag(
        system, REVISION,
        'Compact ChargedV3 Normandy storm cloud (4.6-6.4m diam); 49 zenith-dense lobes; Unaligned FaceCamera; runtime NS_LightningChain cloud arcs + violet-blue sparks',
    )
    save(system)

    # Local-space copy of the approved lightning-magic ribbon system (/Game/Skills/Lightning/NS_LightningChain)
    # so cloud-attached bolts move seamlessly with the caster's overhead storm cloud without lagging behind.
    arc_source = '/Game/Skills/Lightning/NS_LightningChain'
    arc = own(arc_source, 'NS_StormCloudArc')
    arc_emitters = emitters(arc)
    for ename in ('Currency', 'MainPower', 'Detail'):
        if ename not in arc_emitters:
            continue
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(arc, ename), {
            'bLocalSpace': True,
            'SimTarget': 'CPUSim',
        })
        if ename != 'Detail':
            put(arc, ename, 'ParticleSpawnScript', 'InitializeParticle', 'Lifetime', '(Value=0.45)')
    arc.set_editor_property('require_current_frame_data', True)
    EAL.set_metadata_tag(arc, 'StormCloudArc.Source', arc_source)
    EAL.set_metadata_tag(arc, REVISION, 'Local-space copy of NS_LightningChain with User.BladeSpline binding for overhead storm cloud')
    if not u.RainAssetEditor.bind_spline_user_object(arc, 'User.BladeSpline'):
        raise RuntimeError('StormCloudArc spline compilation/binding failed')
    if not EAL.save_loaded_asset(arc, False):
        raise RuntimeError('Save failed ' + arc.get_path_name())
    CREATED.append(arc.get_path_name())

    def digest(pkg_path):
        rel = pkg_path.split('.')[0].replace('/Game/', '') + '.uasset'
        disk = ROOT / 'Content' / rel
        return hashlib.sha256(disk.read_bytes()).hexdigest() if disk.is_file() else None

    saved = [p for p in CREATED if p.startswith(DEST)]
    receipt = {
        'revision': REVISION,
        'dest': DEST,
        'source_material': SOURCE_PARENT,
        'source_instance': SOURCE_INSTANCE,
        'saved_assets': saved,
        'sha256': {Path(p.split('.')[0]).name + '.uasset': digest(p) for p in saved},
        'core_layers': [{'name': s[0], 'count': s[1], 'spread': s[2], 'rad_exp': s[3], 'size': [s[4], s[5]], 'level': s[6]} for s in CORE_LAYERS],
        'core_particles': sum(s[1] for s in CORE_LAYERS),
        'cloud_lightning_source': arc_source,
        'cloud_lightning_system': arc.get_path_name(),
        'spark_emitters': ['FallingElectricSparks'],
        'alignment': 'Unaligned',
        'facing_mode': 'FaceCamera',
        'system_loop_duration': 'max(.6,User.StormDuration+.6)',
        'gameplay_tested': False,
        'rendered': False,
    }
    for out_dir in (BATCH_ROOT, AUTHOR_DIR):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'published.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('STORM_DOMAIN_V3_SAVED ' + json.dumps(receipt))
    return system


if __name__ == '__main__':
    build_cloud()
