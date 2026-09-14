"""Author a soft, slowly roiling fireball from the owned Epic flipbooks.

Commandlet asset creation/compilation only. No game, preview or acceptance run.
"""
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments, duplicate, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter

DEST = '/Game/Skills/Fireball'


def smooth(low, high, value):
    # Niagara's CPU VectorVM does not implement the HLSL smoothstep intrinsic.
    t = f'saturate(({value}-{low})/({high}-{low}))'
    return f'({t}*{t}*(3-2*{t}))'


def soft_parent():
    mat = duplicate('/Game/NiagaraExamples/Materials/MasterMaterials/M_SmokeAndFire_Sprites',
                    'M_FireballSoftSprites')
    nodes = {n.get_name(): n for n in LIB.get_material_expressions(mat)}
    # This is the owned source graph's low-alpha clip, not a global material edit.
    nodes['MaterialExpressionCustom_1'].set_editor_property('code', 'return saturate(Opacity);')
    # The source reconstructs 0..1 sprite UVs independently of the atlas frame.
    # Apply softness before the parent's depth fade / premultiplied-alpha output.
    tag = 'Fireball.SoftEdgeNode'
    custom = nodes.get(unreal.EditorAssetLibrary.get_metadata_tag(mat, tag))
    if not custom:
        custom = LIB.create_material_expression(mat, unreal.MaterialExpressionCustom, 0, 1200)
        unreal.EditorAssetLibrary.set_metadata_tag(mat, tag, custom.get_name())
        pins = []
        for name in ['Opacity', 'UV', 'Time']:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        custom.set_editor_property('inputs', pins)
    custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    custom.set_editor_property('code', '''
float2 q = (UV - .5) * 2;
float phase = Time * 1.3;
float warp = .075 * sin(q.x * 4.1 + phase) * sin(q.y * 3.3 - phase * .7);
float edge = 1 - smoothstep(.42, 1.06, length(q) + warp);
return saturate(Opacity) * edge;
''')
    for source, output, target, input_name in [
        (nodes['MaterialExpressionMultiply_1'], '', custom, 'Opacity'),
        (nodes['MaterialExpressionNamedRerouteUsage_0'], '', custom, 'UV'),
        (nodes['MaterialExpressionTime_0'], '', custom, 'Time'),
        (custom, '', nodes['MaterialExpressionSetMaterialAttributes_6'],
         str(LIB.get_material_expression_input_names(nodes['MaterialExpressionSetMaterialAttributes_6'])[1])),
    ]:
        if not LIB.connect_material_expressions(source, output, target, input_name):
            raise RuntimeError('Cannot author soft opacity connection: ' + target.get_name() + '/' + input_name)
    LIB.recompile_material(mat)
    save(mat)
    return mat


def material(parent, source_name, name, emissive, opacity, temperature):
    mat = duplicate('/Game/NiagaraExamples/Materials/' + source_name, name)
    LIB.set_material_instance_parent(mat, parent)
    for key, value in [('Emissive Gain', emissive), ('Opacity Gain', opacity),
                       ('Opacity Exponent', .85), ('Near Fade Distance', 10),
                       ('Depth Fade Distance', 8), ('Temperature Max', temperature),
                       ('Temperature Min', 900), ('Opacity Clip Value', 0),
                       ('SubUV Speed', .4)]:
        LIB.set_material_instance_scalar_parameter_value(mat, key, value)
    # Each particle drives its own interpolated frame; the shared world clock
    # must not synchronize all layers or ignore the slower Niagara animation.
    for key, value in [('Use Material SubUV', False), ('Use Particle Alpha As Threshold', False),
                       ('Use Emissive Color', True), ('Use Blackbody', True)]:
        LIB.set_material_instance_static_switch_parameter_value(mat, key, value)
    LIB.update_material_instance(mat)
    save(mat)
    return mat


def layer(system, name, mat, inner, lifecycle):
    if name not in emitters(system):
        API.call_method('AddEmitter', (system,
            unreal.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        unreal.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', unreal.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', unreal.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8, 'Y': 8}, 'bSubImageBlend': True,
        'Alignment': 'Unaligned', 'FacingMode': 'FaceCameraPosition', 'bCastShadows': False,
    })
    for input_name, value in lifecycle.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', input_name, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    stack = API.call_method('GetScriptStackTopology', (ref(system, name, 'EmitterUpdateScript'),))
    if not any(str(m.get_editor_property('module_name')) == 'SpawnRate'
               for m in stack.get_editor_property('modules')):
        API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'),
            unreal.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(Value=3)' if inner else '(Value=10)')

    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    variant = 'frac(float(Particles.UniqueID)*.41421356237)'
    z = '(frac(float(Particles.UniqueID)*.754877666)*1.8-.9)'
    theta = '(float(Particles.UniqueID)*2.39996323)'
    direction = f'float3(sqrt(1-{z}*{z})*cos({theta}),sqrt(1-{z}*{z})*sin({theta}),{z})'
    phase = f'(6.2831853*{variant})'
    age = 'Particles.Age'
    normalized = 'Particles.NormalizedAge'
    # Fixed birth direction, volume-filled origins and bounded local sway.
    # No shared axial rotation, expanding shell or velocity-stretched cards.
    radius = f'(1+3*{seed})' if inner else f'(2+6*{seed})'
    sway = (f'float3(sin({age}*1.5+{phase})-sin({phase}),'
            f'sin({age}*1.1+{phase}*1.7)-sin({phase}*1.7),0)')
    hover_position = f'{direction}*{radius}+{sway}*' + ('.6' if inner else '1.5')
    if not inner:
        hover_position += f'+float3(0,0,{age}*3)'
    # The long hover lifetime cannot be used to compute flight displacement:
    # otherwise old particles would jump a metre backwards at launch. Saturate
    # a short tail envelope and crossfade the positions over the first 60 ms.
    flight_shape = f'float3(-4-{normalized}*18,{direction}.y*5*(1-{normalized}),{direction}.z*5*(1-{normalized}))'
    flight_blend = smooth('0', '.06', 'User.FlightAge') + '*saturate(User.Flight)'
    position = hover_position if inner else f'lerp({hover_position},{flight_shape},{flight_blend})'
    life = f'1.5+.5*{seed}' if inner else f'1.2+.6*{seed}'
    size = f'float2(22+{seed}*5,23+{variant}*5)' if inner else f'float2(17+{seed}*6,20+{variant}*7)'
    size += f'*(1+.045*sin({age}*1.7+{phase}))*(1-.14*{normalized})'
    envelope = smooth('0', '.15', normalized) + '*(1-' + smooth('.60', '1', normalized) + ')'
    alpha = '.62' if inner else '.34'
    tint = f'float4(1,.57,.16,{alpha}*{envelope})' if inner else f'float4(1,lerp(.44,.20,{normalized}),.045,{alpha}*{envelope})'
    # 64-frame loop, 10-13 frames/s, independent initial phase; frame blending
    # stays on so slowing the flipbook does not turn it into discrete steps.
    frame = f'fmod({variant}*64+{age}*(10+3*{seed}),64)'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'-20+40*{variant}'),
        'Particles.SubImageIndex': (FLOAT, frame),
        'Particles.Color': (COLOR, tint),
        # Source material: opacity exponent / emission gain / temperature
        # exponent / temperature scale. Explicit neutral values avoid retaining
        # NE_Core's short explosive temperature curve.
        'Particles.DynamicMaterialParameter': ('/Script/CoreUObject.Vector4f', 'float4(1,1,1,1)'),
    }
    spawn = {'Particles.Lifetime': (FLOAT, life), **common}
    assignments(system, name, 'ParticleSpawnScript', spawn)
    assignments(system, name, 'ParticleUpdateScript', common)


def build():
    parent = soft_parent()
    inner = material(parent, 'MI_FireBall_8x8', 'MI_FireballSoftInner', 1.05, .68, 4400)
    roil = material(parent, 'MI_FireRoil_8x8', 'MI_FireballSlowRoil', .9, .62, 3900)
    system = duplicate(DEST + '/NS_FireballAerodynamicCore', 'NS_FireballSlowBurnCore')
    lifecycle = {key: unreal.RainAssetEditor.read_input(system, 'FireballCore', 'EmitterUpdateScript', 'EmitterState', key)
                 for key in ['Life Cycle Mode', 'Loop Behavior']}
    for name in emitters(system):
        if name not in ['FireballCore', 'FireballSlowRoil']:
            API.call_method('RemoveEmitter', (ref(system, name),))
    user_parameter(system, 'FlightAge', FLOAT)
    layer(system, 'FireballCore', inner, True, lifecycle)
    layer(system, 'FireballSlowRoil', roil, False, lifecycle)
    system.set_editor_property('fixed_bounds', unreal.Box(min=unreal.Vector(-65,-45,-45), max=unreal.Vector(45,45,55)))
    save(system)
    out = Path(unreal.Paths.project_dir()) / 'SourceAssets/FireballSlowBurn20260914'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'authoring.json').write_text(json.dumps({
        'runtime_core': system.get_path_name(),
        'source': 'Owned local Epic Niagara Examples FireBall and FireRoil 8x8 looping atlases',
        'materials': [parent.get_path_name(), inner.get_path_name(), roil.get_path_name()],
        'inner': {'rate': 3, 'life_seconds': [1.5,2], 'origin_radius_cm': [1,4]},
        'roil': {'rate': 10, 'life_seconds': [1.2,1.8], 'origin_radius_cm': [2,8], 'hover_lift_cm_per_second': 3},
        'animation': {'atlas_frames': 64, 'frames_per_second': [10,13], 'random_start_frame': True, 'blend_frames': True},
        'edge': 'Soft warped falloff before premultiplication; no alpha clip or velocity stretch',
        'flight': '60 ms transition into a bounded 22 cm rear envelope; hover lift removed at transition end',
        'embers_and_smoke': 'disabled in this first calm-fire version',
        'trail': 'Existing NS_FireballVelocityTrail unchanged',
        'license': 'Derived from existing local Epic assets; original dependencies and license retained',
        'status': 'authored and compiled; no game test or visual acceptance',
    }, indent=2), encoding='utf-8')
    unreal.log('FIREBALL_SLOW_BURN_AUTHORED')


if __name__ == '__main__':
    build()
