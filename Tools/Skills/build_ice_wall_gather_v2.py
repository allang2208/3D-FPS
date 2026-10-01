"""Save inward white condensation and cube-face frost, without opening a preview.

Owns only /Game/Skills/IceWall/GatherV2. FrostV2, ColdMistV1 and the Fab ice
surface stay read-only. Both CPU emitters share the runtime detail allocation.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, setdata, assignments, put, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression

SOURCE = '/Game/Skills/IceWall/ColdMistV1/NS_IceWallColdMist'
DEST = '/Game/Skills/IceWall/GatherV2'
TARGET = DEST + '/NS_IceWallColdMist'
MATERIAL = DEST + '/MI_WhiteCondensation'


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for target in [TARGET, MATERIAL]:
        if target in dirty:
            raise RuntimeError('Preserve unsaved target: ' + target)
    u.EditorAssetLibrary.make_directory(DEST)
    mat = (u.load_asset(MATERIAL) if u.EditorAssetLibrary.does_asset_exist(MATERIAL)
           else u.EditorAssetLibrary.duplicate_asset('/Game/Skills/IceSpike/FrostV2/MI_ColdMist', MATERIAL))
    if not mat:
        raise RuntimeError('Missing owned frost material')
    # Close wisps remain visible at the staff, with depth testing and soft contact.
    for name, value in [('Near Fade Distance', 12), ('Depth Fade Distance', 6), ('Emissive Gain', .06)]:
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mat, name, value)
    u.MaterialEditingLibrary.update_material_instance(mat)
    save(mat)
    system = (u.load_asset(TARGET) if u.EditorAssetLibrary.does_asset_exist(TARGET)
              else u.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET))
    if not system:
        raise RuntimeError('Missing owned wall-mist source: ' + SOURCE)
    for name in ['GatherPhase', 'GatherProgress']:
        user_parameter(system, name, FLOAT)
    en = 'RocketTrail'
    trim(system, en, {'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
                     'ParticleSpawnScript': ['InitializeParticle'],
                     'ParticleUpdateScript': ['ParticleState']})
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        u.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + en + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, en),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, en, renderer=0),
            {'Material': mat.get_path_name(), 'bCastShadows': False, 'MotionVectorSetting': 'Disable'})
    # Charge is energetic; a completed, held cube has a quieter condensation rate.
    gather_rate = '(User.GatherProgress>=.98?14:76)'
    expression(system, en, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
               'saturate(User.Strength)*(User.GatherPhase*' + gather_rate
               + '+(1-User.GatherPhase)*lerp(User.Flight*83,clamp(User.WallSize.y*.065,20,72),User.WallPhase))*(1-saturate(User.DetailReduction))')
    a = 'frac(float(Particles.UniqueID)*.61803398875)'
    b = 'frac(float(Particles.UniqueID)*.754877666)'
    c = 'frac(float(Particles.UniqueID)*.569840296)'
    z = f'({a}*2-1)'
    xy = f'sqrt(max(0,1-{z}*{z}))'
    direction = f'float3({xy}*cos({b}*6.2831853),{xy}*sin({b}*6.2831853),{z})'
    basis_dir = f'(User.FlightDirection*({direction}).x+User.Side*({direction}).y+User.Up*({direction}).z)'
    axis_max = f'max(.001,max(abs(({direction}).x),max(abs(({direction}).y),abs(({direction}).z))))'
    core_t = 'saturate((User.GatherProgress-.20)/.65)'
    core = f'({core_t}*{core_t}*(3-2*{core_t}))'
    cube_radius = f'(12*lerp(.2,1,{core})/{axis_max})'
    convergence = 'pow(saturate(Particles.NormalizedAge),.72)'
    radius = f'lerp(42+{c}*26,{cube_radius},{convergence})'
    # Analytic advection follows the moving staff; it never leaves a trail across the room.
    gather_position = f'User.CurrentPosition+{basis_dir}*({radius})'
    radial = f'(User.Side*cos({b}*6.2831853)+User.Up*sin({b}*6.2831853))'
    flight_position = f'lerp(User.PreviousPosition,User.CurrentPosition,{a})+User.FlightDirection*(-9+{a}*18)+{radial}*(3+{b}*3)'
    face = '(frac(float(Particles.UniqueID)*.5)<.5?-1:1)'
    wall_position = (f'User.CurrentPosition+User.Side*({b}*2-1)*max(0,User.WallSize.y*.5-6)'
                     f'+User.FlightDirection*{face}*(User.WallSize.x*.5+4)'
                     f'+User.Up*(18+{c}*max(0,User.WallSize.z-18))')
    velocity = (f'lerp({radial}*(6+{a}*8)+float3(0,0,-15)-User.FlightDirection*User.Flight*38,'
                f'User.FlightDirection*{face}*(5+{a}*5)+User.Side*({b}*2-1)*5+float3(0,0,-8),User.WallPhase)+User.Wind')
    old_size = f'lerp(float2(11,15),float2(28,34),User.WallPhase)*(1+{b}*.4)*(1+Particles.NormalizedAge*.6)'
    size = f'lerp({old_size},float2(18,23)*(1+{c}*.25)*lerp(1,.32,{convergence}),User.GatherPhase)'
    opacity = (f'lerp(lerp(.42,.26,User.WallPhase),.56,User.GatherPhase)'
               '*saturate(Particles.NormalizedAge*9)*pow(max(0,1-Particles.NormalizedAge),.65)'
               '*(User.GatherPhase+User.WallPhase+User.Flight*saturate(User.Strength))')
    color = f'float4(lerp(float3(.60,.73,.79),float3(.94,.97,1),User.GatherPhase),{opacity})'
    assignments(system, en, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'lerp(lerp(lerp(.40+.26*{a},.10+.06*{a},User.Flight),1.05+.50*{a},User.WallPhase),.30+.18*{c},User.GatherPhase)'),
        'Particles.Position': (POSITION, f'lerp(lerp({flight_position},{wall_position},User.WallPhase),{gather_position},User.GatherPhase)'),
        'Particles.Velocity': (VEC3, velocity),
        'Particles.SpriteSize': (VEC2, size), 'Particles.SpriteRotation': (FLOAT, f'{a}*360'),
        'Particles.Color': (COLOR, color), 'Particles.SubImageIndex': (FLOAT, '0'),
    })
    assignments(system, en, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, f'lerp(Particles.Position+Particles.Velocity*Engine.DeltaTime,{gather_position},User.GatherPhase)'),
        'Particles.SpriteSize': (VEC2, size), 'Particles.Color': (COLOR, color),
        'Particles.SubImageIndex': (FLOAT, 'clamp(Particles.NormalizedAge*56,0,63)'),
    })

    # Fine frost settles on the six faces, making the final silhouette cubic.
    face_name = 'CubeCondensation'
    from build_fireball_assets import emitters
    if face_name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, face_name),))
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), face_name))
    trim(system, face_name, {'EmitterUpdateScript': ['EmitterState'],
                            'ParticleSpawnScript': ['InitializeParticle'],
                            'ParticleUpdateScript': ['ParticleState']})
    for key in ['Life Cycle Mode', 'Loop Behavior']:
        value = u.RainAssetEditor.read_input(system, en, 'EmitterUpdateScript', 'EmitterState', key)
        put(system, face_name, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    API.call_method('AddModule', (ref(system, face_name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, face_name),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, face_name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8, 'Y': 8}, 'bSubImageBlend': True,
        'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera', 'bCastShadows': False,
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable',
    })
    expression(system, face_name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
               '22*saturate(User.GatherProgress)*User.GatherPhase*(1-saturate(User.DetailReduction))')
    common = {
        'Particles.Position': (POSITION, f'User.CurrentPosition+{basis_dir}*({cube_radius}+.5)'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, f'float2(5,7)*(1+{b}*.4)'),
        'Particles.SpriteRotation': (FLOAT, f'{b}*360'),
        'Particles.Color': (COLOR, 'float4(.96,.98,1,.26*User.GatherPhase*saturate(Particles.NormalizedAge*8)*saturate((1-Particles.NormalizedAge)*6))'),
        'Particles.SubImageIndex': (FLOAT, 'clamp(Particles.NormalizedAge*56,0,63)'),
    }
    assignments(system, face_name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, f'.22+.12*{a}'), **common})
    assignments(system, face_name, 'ParticleUpdateScript', common)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-2600, -2600, -160), max=u.Vector(2600, 2600, 420)))
    save(system)
    receipt = {'saved_assets': [mat.get_path_name(), system.get_path_name()],
               'source': SOURCE, 'white_inward_gather': True, 'gather_outer_radius_cm': [42, 68],
               'cube_edge_cm': 24, 'inward_spawn_rate': 76, 'held_inward_spawn_rate': 14,
               'face_spawn_rate_max': 22, 'inward_lifetime_seconds': [.30, .48],
               'cpu_emitters': 2, 'shared_detail_budget': True, 'gameplay_tested': False}
    out = ROOT / 'Saved/IceWallCondensation20261001'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'gather-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ICE_WALL_GATHER_V2_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
