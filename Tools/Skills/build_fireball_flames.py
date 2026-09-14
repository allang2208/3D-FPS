"""Add the owned Epic flame layer to the existing runtime fireball system.

UE Python commandlet authoring only. No playback, screenshots or game tests.
The original environment system/materials are never saved or edited.
"""
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments, save, duplicate

DEST = '/Game/Skills/Fireball'
ROOT = Path(unreal.Paths.project_dir())
FLOAT = '/Script/Niagara.NiagaraFloat'
VEC2 = '/Script/CoreUObject.Vector2f'
VEC3 = '/Script/CoreUObject.Vector3f'
POSITION = '/Script/Niagara.NiagaraPosition'
COLOR = '/Script/CoreUObject.LinearColor'


def trim(system, emitter, keep):
    topology = API.call_method('GetEmitterTopology', (ref(system, emitter),))
    for field in ['emitter_spawn_script', 'emitter_update_script', 'particle_spawn_script', 'particle_update_script']:
        stack = topology.get_editor_property(field)
        script = str(stack.get_editor_property('script_name'))
        for module in stack.get_editor_property('modules'):
            name = str(module.get_editor_property('module_name'))
            if name not in keep.get(script, []):
                API.call_method('RemoveModule', (ref(system, emitter, script, name),))


def flame_material():
    mat = duplicate('/Game/NiagaraExamples/Materials/MI_Flames', 'MI_FireballSurfaceFlames')
    for key, value in [('FadeDistance', 4), ('Color Boost Gain', 5),
                       ('Opacity Exponent', 1.35), ('Distortion Scale', .22)]:
        LIB.set_material_instance_scalar_parameter_value(mat, key, value)
    LIB.update_material_instance(mat)
    save(mat)
    return mat


def build():
    core = duplicate(DEST + '/NS_FireballCore', 'NS_FireballBurningCore')
    source = unreal.load_asset('/Game/NiagaraExamples/FX_Misc/NS_Fire')
    if not core or not source:
        raise RuntimeError('Build the initial fireball assets and restore Niagara Examples first')
    flame_template = unreal.load_object(None, source.get_path_name() + ':FlamesOnly_0')
    if not flame_template:
        raise RuntimeError('Missing owned NS_Fire FlamesOnly authoring emitter')

    mat = flame_material()
    for name in ['FireballSurfaceFlames', 'FireballSurfaceEmbers']:
        if name in emitters(core):
            API.call_method('RemoveEmitter', (ref(core, name),))
        # Own assignment tags are tied to the replaced emitter's module nodes.
        for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
            unreal.EditorAssetLibrary.remove_metadata_tag(core, 'Fireball.Assignments.' + name + '.' + script)
        API.call_method('AddEmitter', (core, flame_template, name))

        # Retain the source's material animation and normalised particle age,
        # replacing only its environment-mesh spawning and world-force motion.
        trim(core, name, {
            'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
            'ParticleSpawnScript': ['InitializeParticle'],
            'ParticleUpdateScript': ['ParticleState', 'DynamicMaterialParameters'],
        })
        setdata('SetEmitterData', unreal.NiagaraExt_EmitterData, ref(core, name),
                {'bLocalSpace': True, 'SimTarget': 'CPUSim'})
        setdata('SetRendererData', unreal.NiagaraExt_RendererData, ref(core, name, renderer=0),
                {'Material': mat.get_path_name(),
                 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
                 'bCastShadows': False, 'Alignment': 'VelocityAligned'})
        # Self lifecycle takes the already-authored core's infinite loop.
        for input_name in ['Life Cycle Mode', 'Loop Behavior']:
            value = unreal.RainAssetEditor.read_input(core, 'FireballCore', 'EmitterUpdateScript', 'EmitterState', input_name)
            put(core, name, 'EmitterUpdateScript', 'EmitterState', input_name, value,
                '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        rate = 32 if name == 'FireballSurfaceFlames' else 7
        put(core, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(Value=' + str(rate) + ')')

        # UniqueID is stable during a particle's life. Irrational increments
        # distribute a continuous stream over the sphere, without emitter-wide
        # turns or random direction changes between frames.
        seed = 'frac(float(Particles.UniqueID)*.61803398875)'
        z = '(frac(float(Particles.UniqueID)*.754877666)*1.8-.9)'
        theta = '(float(Particles.UniqueID)*2.39996323+Particles.Age*2.4)'
        direction = f'float3(sqrt(1-{z}*{z})*cos({theta}),sqrt(1-{z}*{z})*sin({theta}),{z})'
        ember = name == 'FireballSurfaceEmbers'
        life = f'({".38" if ember else ".32"}+{seed}*{ ".18" if ember else ".16"})'
        radius = '(12+Particles.Age*19)' if ember else '(11.5+Particles.Age*8)'
        lift = '38' if ember else '22'
        position = f'{direction}*{radius}+float3(0,0,Particles.Age*{lift})'
        velocity = f'{direction}*{ "19" if ember else "8"}+float3(0,0,{lift})'
        size = f'float2(.7,1.8)*(1-.65*Particles.NormalizedAge)' if ember else f'float2(7+{seed}*3,12+Particles.NormalizedAge*9)*(1-.35*Particles.NormalizedAge)'
        alpha = 'saturate(Particles.NormalizedAge*9)*saturate((1-Particles.NormalizedAge)*3)'
        tint = f'float4(1,.32,.045,{alpha}*.65)' if ember else f'float4(1,.46,.10,{alpha}*.58)'
        assignments(core, name, 'ParticleSpawnScript', {
            'Particles.Lifetime': (FLOAT, life),
            'Particles.Position': (POSITION, position),
            'Particles.Velocity': (VEC3, velocity),
            'Particles.SpriteSize': (VEC2, 'float2(1,2)' if ember else 'float2(8,12)'),
            'Particles.Color': (COLOR, 'float4(1,.46,.1,0)'),
            'Particles.Temperature': (FLOAT, '3400'),
        })
        assignments(core, name, 'ParticleUpdateScript', {
            'Particles.Position': (POSITION, position),
            'Particles.Velocity': (VEC3, velocity),
            'Particles.SpriteSize': (VEC2, size),
            'Particles.Color': (COLOR, tint),
            'Particles.Temperature': (FLOAT, '3400-1800*Particles.NormalizedAge'),
        })

    # Existing Core component supplies gather scale, near-camera visibility,
    # world occlusion and impact shutdown to every new layer automatically.
    core.set_editor_property('fixed_bounds', unreal.Box(min=unreal.Vector(-65,-65,-65), max=unreal.Vector(65,65,65)))
    save(core)
    out = ROOT / 'SourceAssets/FireballBurn20260914'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'authoring.json').write_text(json.dumps({
        'source_package': 'Epic Niagara Examples Pack (existing locally acquired assets)',
        'source_system': source.get_path_name(),
        'source_emitter': flame_template.get_path_name(),
        'source_material': '/Game/NiagaraExamples/Materials/MI_Flames',
        'runtime_system': core.get_path_name(),
        'runtime_material': mat.get_path_name(),
        'surface_flames_per_second': 32,
        'surface_embers_per_second': 7,
        'flame_lifetime_seconds': [.32,.48],
        'ember_lifetime_seconds': [.38,.56],
        'local_space': True,
        'existing_trail_and_impact': 'unchanged',
        'status': 'authored and compiled; no game test or rendered acceptance',
        'license': 'Keep original Epic package license and content dependencies; no redistribution grant.'
    }, indent=2), encoding='utf-8')
    unreal.log('FIREBALL_SURFACE_FLAMES_AUTHORED')


if __name__ == '__main__':
    build()
