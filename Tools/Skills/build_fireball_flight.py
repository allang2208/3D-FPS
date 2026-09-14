"""Author velocity-aligned fireball flames and a world-space path trail.

Uses the existing owned flame assets. Asset creation/compilation only, no play.
"""
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, ref, emitters, setdata, put, assignments, duplicate, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR

DEST = '/Game/Skills/Fireball'


def user_parameter(system, name, typ):
    variable = unreal.NiagaraExt_UserVariable()
    variable.import_text('(Name="User.' + name + '",Type=(ClassStructOrEnum="' + typ + '",UnderlyingType=2))')
    API.call_method('AddUserVariables', (system, [variable]))


def expression(system, emitter, script, module, name, value):
    put(system, emitter, script, module, name,
        '(HlslExpression="' + value + '")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')


def aerodynamic_core():
    core = duplicate(DEST + '/NS_FireballBurningCore', 'NS_FireballAerodynamicCore')
    user_parameter(core, 'Flight', FLOAT)
    for name in ['FireballSurfaceFlames', 'FireballSurfaceEmbers']:
        # Keep the existing gathering/hovering shape. At launch only the flame
        # movement changes: no upward or outward drift remains in flight.
        seed = 'frac(float(Particles.UniqueID)*.61803398875)'
        z = '(frac(float(Particles.UniqueID)*.754877666)*1.8-.9)'
        theta = '(float(Particles.UniqueID)*2.39996323+Particles.Age*2.4)'
        direction = f'float3(sqrt(1-{z}*{z})*cos({theta}),sqrt(1-{z}*{z})*sin({theta}),{z})'
        ember = name == 'FireballSurfaceEmbers'
        lift, spread = ('38', '19') if ember else ('22', '8')
        radius = '(12+Particles.Age*19)' if ember else '(11.5+Particles.Age*8)'
        hover_position = f'{direction}*{radius}+float3(0,0,Particles.Age*{lift})'
        hover_velocity = f'{direction}*{spread}+float3(0,0,{lift})'
        # The actor's +X follows flight velocity. Cross-section contracts with
        # age and all longitudinal displacement is behind the rear hemisphere.
        rear_speed = '110' if ember else '80'
        rear_position = (f'float3(-5-abs({direction}.x)*7-Particles.Age*{rear_speed},'
                         f'{direction}.y*10*(1-Particles.NormalizedAge),'
                         f'{direction}.z*10*(1-Particles.NormalizedAge))')
        for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
            # Asset duplication preserves the graph but not package metadata.
            # Locate the copied motion assignment by its particle inputs.
            stack = API.call_method('GetScriptStackTopology', (ref(core, name, script),))
            candidates = [m for m in stack.get_editor_property('modules')
                          if {'Particles.Position', 'Particles.Velocity'}.issubset(
                              {str(i.get_editor_property('name')) for i in m.get_editor_property('inputs')})]
            if not candidates:
                raise RuntimeError('Missing burning-core motion assignment: ' + name + '/' + script)
            module = str(candidates[-1].get_editor_property('module_name'))
            expression(core, name, script, module, 'Particles.Position',
                       f'lerp({hover_position},{rear_position},saturate(User.Flight))')
            expression(core, name, script, module, 'Particles.Velocity',
                       f'lerp({hover_velocity},float3(-{rear_speed},0,0),saturate(User.Flight))')
    core.set_editor_property('fixed_bounds', unreal.Box(min=unreal.Vector(-90,-65,-65), max=unreal.Vector(65,65,65)))
    save(core)
    return core


def trajectory_trail(core):
    trail = duplicate(DEST + '/NS_FireballTrail', 'NS_FireballVelocityTrail')
    name = 'RocketTrail'
    if name not in emitters(trail):
        raise RuntimeError('Missing source RocketTrail emitter')
    # Remove the imported rocket's lift, turbulence, gravity, velocity solver,
    # spawn shape and per-unit source motion. C++ supplies each swept segment.
    trim(trail, name, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState', 'SubUVAnimation', 'DynamicMaterialParameters'],
    })
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        unreal.EditorAssetLibrary.remove_metadata_tag(trail, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', unreal.NiagaraExt_EmitterData, ref(trail, name),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', unreal.NiagaraExt_RendererData, ref(trail, name, renderer=0),
            {'Alignment': 'VelocityAligned', 'bCastShadows': False})
    for param, typ in [('FlightDirection', VEC3), ('FlightSpeed', FLOAT),
                       ('PreviousPosition', POSITION), ('CurrentPosition', POSITION)]:
        user_parameter(trail, param, typ)

    stack = API.call_method('GetEmitterTopology', (ref(trail, name),)).get_editor_property('emitter_update_script')
    if not any(str(m.get_editor_property('module_name')) == 'SpawnRate' for m in stack.get_editor_property('modules')):
        API.call_method('AddModule', (ref(trail, name, 'EmitterUpdateScript'), unreal.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    for input_name in ['Life Cycle Mode', 'Loop Behavior']:
        value = unreal.RainAssetEditor.read_input(core, 'FireballCore', 'EmitterUpdateScript', 'EmitterState', input_name)
        put(trail, name, 'EmitterUpdateScript', 'EmitterState', input_name, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    expression(trail, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', 'clamp(User.FlightSpeed/10,0,480)')
    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    assignments(trail, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'.10+.04*{seed}'),
        # Low-frame-rate movement is distributed along the actual traversed
        # segment; no particle is authored above it or ahead of the projectile.
        'Particles.Position': (POSITION, f'lerp(User.PreviousPosition,User.CurrentPosition,{seed})'),
        'Particles.Velocity': (VEC3, '-User.FlightDirection*65'),
        'Particles.SpriteSize': (VEC2, 'float2(17,26)'),
        'Particles.Color': (COLOR, 'float4(1,.48,.09,.48)'),
    })
    assignments(trail, name, 'ParticleUpdateScript', {
        # Integrate the birth velocity in world space. No live user direction,
        # forces, buoyancy or component transform can redirect existing flames.
        'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize': (VEC2, 'float2(17,26)*(1-.8*Particles.NormalizedAge)'),
        'Particles.Color': (COLOR, 'float4(1,lerp(.48,.10,Particles.NormalizedAge),.04,.48*(1-Particles.NormalizedAge)*(1-Particles.NormalizedAge))'),
    })
    trail.set_editor_property('fixed_bounds', unreal.Box(min=unreal.Vector(-600,-600,-600), max=unreal.Vector(600,600,600)))
    save(trail)
    return trail


def build():
    core = aerodynamic_core()
    trail = trajectory_trail(core)
    out = Path(unreal.Paths.project_dir()) / 'SourceAssets/FireballFlight20260914'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'authoring.json').write_text(json.dumps({
        'runtime_core': core.get_path_name(), 'runtime_trail': trail.get_path_name(),
        'source': 'Existing project FireballBurningCore and FireballTrail, derived from owned Epic Niagara Examples',
        'hover': 'Original buoyant flames',
        'flight_surface': 'Local -X aligned with opposite projectile velocity; no upward lift',
        'trail': 'World-space swept path, velocity sampled at birth, no gravity/wind/upward lift',
        'trail_lifetime_seconds': [.10,.14], 'trail_spawn_spacing_cm': 10,
        'status': 'authored and compiled; not game-tested or rendered',
    }, indent=2), encoding='utf-8')
    unreal.log('FIREBALL_VELOCITY_TRAIL_AUTHORED')


if __name__ == '__main__':
    build()
