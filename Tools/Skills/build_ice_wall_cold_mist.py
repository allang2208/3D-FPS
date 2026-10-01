"""Make the wall's bounded condensation layer from the existing ice-spike mist.

Owns only /Game/Skills/IceWall/ColdMistV1/NS_IceWallColdMist. Reuses the
FrostV2 material/atlas without saving them. Asset compilation and saving only.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, setdata, assignments, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression

SOURCE = '/Game/Skills/IceSpike/FrostV2/NS_ColdMist'
DEST = '/Game/Skills/IceWall/ColdMistV1'
TARGET = DEST + '/NS_IceWallColdMist'


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if TARGET in dirty:
        raise RuntimeError('Preserve unsaved ice-wall mist asset: ' + TARGET)
    u.EditorAssetLibrary.make_directory(DEST)
    system = (u.load_asset(TARGET) if u.EditorAssetLibrary.does_asset_exist(TARGET)
              else u.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET))
    if not system:
        raise RuntimeError('Missing ice-spike condensation source: ' + SOURCE)
    en = 'RocketTrail'
    trim(system, en, {
        'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
        'ParticleSpawnScript': ['InitializeParticle'],
        'ParticleUpdateScript': ['ParticleState'],
    })
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        u.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + en + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, en), {
        'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False,
    })
    for name, typ in [('WallPhase', FLOAT), ('WallSize', VEC3)]:
        user_parameter(system, name, typ)
    expression(system, en, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
               'saturate(User.Strength)*lerp(18+User.Flight*65,clamp(User.WallSize.y*.065,20,72),User.WallPhase)*(1-saturate(User.DetailReduction))')

    a = 'frac(float(Particles.UniqueID)*.61803398875)'
    b = 'frac(float(Particles.UniqueID)*.754877666)'
    c = 'frac(float(Particles.UniqueID)*.569840296)'
    face = '(frac(float(Particles.UniqueID)*.5)<.5?-1:1)'
    radial = f'(User.Side*cos({b}*6.2831853)+User.Up*sin({b}*6.2831853))'
    seed_position = f'User.FlightDirection*(-9+{a}*18)+{radial}*(3+{b}*3)'
    wall_position = (f'User.Side*({b}*2-1)*max(0,User.WallSize.y*.5-6)'
                     f'+User.FlightDirection*{face}*(User.WallSize.x*.5+4)'
                     f'+User.Up*(18+{c}*max(0,User.WallSize.z-18))')
    seed_velocity = f'{radial}*(6+{a}*8)+float3(0,0,-15)-User.FlightDirection*User.Flight*38'
    wall_velocity = (f'User.FlightDirection*{face}*(5+{a}*5)'
                     f'+User.Side*({b}*2-1)*5+float3(0,0,-8)')
    size = f'lerp(float2(11,15),float2(28,34),User.WallPhase)*(1+{b}*.4)'
    opacity = 'lerp(.42,.26,User.WallPhase)'
    assignments(system, en, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'lerp(lerp(.40+.26*{a},.10+.06*{a},User.Flight),1.05+.50*{a},User.WallPhase)'),
        'Particles.Position': (POSITION, f'lerp(lerp(User.PreviousPosition,User.CurrentPosition,{a}),User.CurrentPosition,User.WallPhase)+lerp({seed_position},{wall_position},User.WallPhase)'),
        'Particles.Velocity': (VEC3, f'lerp({seed_velocity},{wall_velocity},User.WallPhase)+User.Wind'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'{a}*360'),
        'Particles.Color': (COLOR, f'float4(.60,.73,.79,{opacity})'),
        'Particles.SubImageIndex': (FLOAT, '0'),
    })
    assignments(system, en, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize': (VEC2, size + '*(1+Particles.NormalizedAge*.6)'),
        'Particles.Color': (COLOR, f'float4(.60,.73,.79,{opacity}*saturate(Particles.NormalizedAge*7)*pow(1-Particles.NormalizedAge,1.5))'),
        'Particles.SubImageIndex': (FLOAT, 'clamp(Particles.NormalizedAge*56,0,63)'),
    })
    # Runtime narrows these world-oriented bounds for each cast's actual width.
    system.set_editor_property('fixed_bounds', u.Box(
        min=u.Vector(-2600, -2600, -160), max=u.Vector(2600, 2600, 420)))
    save(system)
    receipt = {
        'source': SOURCE, 'saved_assets': [system.get_path_name()],
        'material_reused': '/Game/Skills/IceSpike/FrostV2/MI_ColdMist',
        'niagara_compiled': True, 'components_per_wall': 1,
        'wall_spawn_rate_per_second': [20, 72], 'wall_particle_lifetime_seconds': [1.05, 1.55],
        'low_wall_emission_height_fraction': .5, 'high_wall_emission_height_fraction': .8,
        'world_space': True, 'gameplay_tested': False,
    }
    out = ROOT / 'Saved/IceWallColdMist'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ICE_WALL_COLD_MIST_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
