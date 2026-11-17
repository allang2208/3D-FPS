"""Two bounded, room-aware cold mist layers for the existing Blizzard system."""
import json
import unreal as u
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import expression
from build_blizzard_indoor_v5 import select_cell
from build_blizzard_charged_v3 import cloud_lifecycle

E = u.EditorAssetLibrary
DEST = '/Game/Skills/Blizzard/IndoorV5/'
SYSTEM = DEST + 'NS_BlizzardBoundaryMist'
MATERIAL = DEST + 'MI_BlizzardColdMist'
LAYERS = ('BlizzardGroundCold', 'BlizzardRisingCold')


def author_material():
    material = (u.load_asset(MATERIAL) if E.does_asset_exist(MATERIAL) else
                E.duplicate_asset('/Game/Skills/IceSpike/FrostV2/MI_ColdMist', MATERIAL))
    if not material:
        raise RuntimeError('Missing IceSpike cold mist source')
    for key, value in [('Opacity Gain', .9), ('Emissive Gain', .025),
                       ('Depth Fade Distance', 20), ('Near Fade Distance', 45)]:
        LIB.set_material_instance_scalar_parameter_value(material, key, value)
    LIB.update_material_instance(material)
    E.set_metadata_tag(material, 'Blizzard.ColdMist.Revision', '2')
    return material


def layer(system, name, material, rising):
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                       'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'InterpolatedSpawnMode': 'NoInterpolation'})
    renderer = ref(system, name, renderer=0)
    values = json.loads(API.call_method('GetRendererData', (renderer,)).get_editor_property('property_values'))
    bindings = {}
    for key, attribute in [('SpriteAlignmentBinding', 'SpriteAlignment'), ('UVScaleBinding', 'SpriteUVScale')]:
        binding = values[key]
        binding.update(rootName=attribute, dataSetName=attribute,
                       cachedDisplayName='Particles.'+attribute, bindingSourceMode='ImplicitFromSource')
        binding['paramMapVariable']['name'] = 'Particles.'+attribute
        bindings[key] = binding
    setdata('SetRendererData', u.NiagaraExt_RendererData, renderer, {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8, 'Y': 8}, 'bSubImageBlend': True,
        'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth',
        'bCastShadows': False, 'MotionVectorSetting': 'Disable',
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, **bindings})
    for key, value in cloud_lifecycle().items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
               f'{6 if rising else 20}*saturate(User.Strength)*(1-.75*saturate(User.DetailReduction))')

    # Scatter over the ellipse first, then sample room clearance at that point.
    # Room probes control clipping only; their centres must not become a visible
    # 5x5 arrangement of regularly spaced cold puffs.
    salt = '31.73' if rising else '7.19'
    seed = f'(float(Particles.UniqueID)+{salt})'
    a = f'frac(sin({seed}*12.9898)*43758.5453)'
    b = f'frac(sin({seed}*39.3468+11.13)*24634.6345)'
    c = f'frac(sin({seed}*7.123+53.71)*19341.167)'
    cell, age = 'Particles.RoomCell', 'Particles.NormalizedAge'
    wind_x, wind_y = 'clamp(dot(User.Wind,User.Side)/60,-1,1)', 'clamp(dot(User.Wind,User.Up)/60,-1,1)'
    px = f'cos({a}*6.2831853)*sqrt({b})*.87+.025*sin(Particles.Age*1.4+{c}*6.28)+.035*({wind_x})*sin(Particles.Age*.9)'
    py = f'sin({a}*6.2831853)*sqrt({b})*.87+.025*cos(Particles.Age*1.1+{c}*6.28)+.035*({wind_y})*sin(Particles.Age*.9)'
    x, y = 'Particles.MistUV.x', 'Particles.MistUV.y'
    gx, gy = f'clamp(floor(({x}+1)*2.5),0,4)', f'clamp(floor(({y}+1)*2.5),0,4)'
    index = f'(({gy})*5+({gx}))'
    local = f'max(abs({x}-(({gx})-2)*.4),abs({y}-(({gy})-2)*.4))/.2'
    room_mask = f'({cell}.z>=.999?1:saturate(({cell}.z-({local}))*12))'
    valid = f'saturate({cell}.z*12)*({room_mask})*saturate((.98-({x})*({x})-({y})*({y}))*8)'
    if rising:
        width = f'min(90,min(min(User.RadiusX,User.RadiusY)*.22*{cell}.z,{cell}.y*.42))'
        size = f'float2(.85,1)*({width})*(.72+.28*{c})*(.68+.32*{age})'
        z = f'{cell}.x+({width})*(.52+.30*{age})'
        life, alpha = f'.75+{b}*.40', '.17'
        rotation = f'(2*{a}-1)*9+sin(Particles.Age*1.7+{b}*6.28)*5'
    else:
        width = f'min(180,min(min(User.RadiusX,User.RadiusY)*.30*{cell}.z,{cell}.y*1.1))'
        size = f'float2(1,.40)*({width})*(.72+.28*{c})*(.80+.20*{age})'
        z = f'{cell}.x+({width})*(.20+.025*sin(Particles.Age*2+{a}*6.28))'
        life, alpha = f'1.25+{b}*.60', '.30'
        rotation = f'(2*{a}-1)*4+sin(Particles.Age*1.2+{b}*6.28)*2'
    fade = f'saturate({age}*6)*saturate((1-{age})*3.5)'
    position = f'User.CurrentPosition+User.Side*User.RadiusX*({x})+User.Up*User.RadiusY*({y})+User.SurfaceNormal*({z})'
    fields = {
        'Particles.Position': (POSITION, position), 'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, rotation), 'Particles.SpriteAlignment': (VEC3, 'User.SurfaceNormal'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SubImageIndex': (FLOAT, f'clamp({age}*62.9,0,62.9)'),
        'Particles.Color': (COLOR, f'float4(.64,.78,.84,{alpha}*saturate(User.Strength)*({valid})*({fade}))')}
    for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        tag = 'Fireball.Assignments.'+name+'.'+stage
        E.remove_metadata_tag(system, tag)
        assignments(system, name, stage, {'Particles.MistUV': (VEC2, f'float2({px},{py})')})
        E.remove_metadata_tag(system, tag)
        assignments(system, name, stage, {'Particles.RoomCell': (VEC3, select_cell(index, 'User.RoomCell'))})
        E.remove_metadata_tag(system, tag)
        assignments(system, name, stage,
                    {**fields, **({'Particles.Lifetime': (FLOAT, life)} if stage == 'ParticleSpawnScript' else {})})


def apply(system, material):
    current = set(emitters(system))
    # Only replace this system's old boundary mist and our own two layers.
    for name in ('IndoorMist',) + LAYERS:
        if name in current:
            API.call_method('RemoveEmitter', (ref(system, name),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            E.remove_metadata_tag(system, 'Fireball.Assignments.'+name+'.'+stage)
    for name, rising in zip(LAYERS, (False, True)):
        layer(system, name, material, rising)
    E.set_metadata_tag(system, 'Blizzard.ColdMist.Revision', '2')
    return {'revision': 2, 'layers': list(LAYERS), 'ground_rate': 20, 'rising_rate': 6,
            'ground_lifetime_seconds': [1.25, 1.85], 'rising_lifetime_seconds': [.75, 1.15],
            'ground_width_cap_cm': 180, 'rising_width_cap_cm': 90,
            'room_cells_per_layer': 25, 'distribution': 'continuous ellipse; room lookup after scattered position',
            'added_textures': 0, 'added_lights': 0,
            'source_ice_spike_modified': False}
