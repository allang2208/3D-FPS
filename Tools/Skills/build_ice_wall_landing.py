"""Save one ice-wall landing system from existing project dust and frost materials.

Background/serialized editor authoring only. Owns /Game/Skills/IceWall/SlamV2/NS_IceWallLanding;
source explosion, rolling-smoke material and ice-spike mist are read-only.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
from build_fireball_assets import API, ref, emitters, setdata, put, assignments, save
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from fluid_contact_nodes import contact_nodes, clear_contact_tags

DEST = '/Game/Skills/IceWall/SlamV2'
TARGET = DEST + '/NS_IceWallLanding'
SOURCE = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'
DUST = '/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke'
MIST = '/Game/Skills/IceSpike/FrostV2/MI_ColdMist'


def layer(system, name, material, mist, lifecycle):
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                       'ParticleSpawnScript': ['InitializeParticle'],
                       'ParticleUpdateScript': ['ParticleState']})
    clear_contact_tags(system, name)
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        u.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8 if mist else 1, 'Y': 8 if mist else 1}, 'bSubImageBlend': mist,
        'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera', 'bCastShadows': False,
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable',
    })
    for key, value in lifecycle.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=1.8)')
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'),
                                u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    count = 'floor(User.' + ('MistCount' if mist else 'DustCount') + '*(1-saturate(User.DetailReduction))+.5)'
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(HlslExpression="' + count + '")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    a = 'frac(float(Particles.UniqueID)*.618033989)'
    b = 'frac(float(Particles.UniqueID)*.414213562)'
    age = 'Particles.Age'
    norm = 'Particles.NormalizedAge'
    side = '(frac(float(Particles.UniqueID)*.5)<.5?-1:1)'
    # Count includes both faces. Reduced detail still spans the entire wall.
    along = f'((floor(float(Particles.UniqueID)*.5)+.5)/max(1,ceil(({count})*.5))-.5)*User.WallSize.y'
    travel = f'{age}*30' if mist else f'(110+30*{a})*(1-exp(-{age}*12))'
    position = (f'float3({side}*(User.WallSize.x*.5+8+{travel}),{along},'
                f'12+{age}*' + ('7)' if mist else f'(12+8*{b}))'))
    position += f'+User.Wind*({age}-.25*(1-exp(-{age}/.25)))'
    size = f'float2(76,40)*(1+{b}*.25)*(.8+{norm}*.8)' if mist else f'float2(96,64)*(1+{b}*.25)*(.9+{norm}*.85)'
    tint = '.60,.73,.79' if mist else '.28,.27,.25'
    opacity = '.34' if mist else '.56'
    life = f'1.10+.35*{a}' if mist else f'.85+.30*{a}'
    common = {
        'Particles.Position': (POSITION, position), 'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size), 'Particles.SpriteRotation': (FLOAT, f'{b}*360'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, f'float4({tint},{opacity}*saturate({age}/.025)*pow(1-{norm},1.4))'),
        'Particles.SubImageIndex': (FLOAT, f'min(62.95,{norm}*56)' if mist else '0'),
        'Particles.DynamicMaterialParameter': ('/Script/CoreUObject.Vector4f', f'float4({a},0,0,0)'),
    }
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, life), **common})
    assignments(system, name, 'ParticleUpdateScript', common)
    contact_nodes(system, name)


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if TARGET in dirty:
        raise RuntimeError('Preserve unsaved target: ' + TARGET)
    dust, mist, source = u.load_asset(DUST), u.load_asset(MIST), u.load_asset(SOURCE)
    if not dust or not mist or not source:
        raise RuntimeError('Restore existing rolling smoke, cold mist and explosion template first')
    u.EditorAssetLibrary.make_directory(DEST)
    system = u.load_asset(TARGET) if u.EditorAssetLibrary.does_asset_exist(TARGET) else u.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    for name, typ in [('WallSize', VEC3), ('DustCount', FLOAT), ('MistCount', FLOAT),
                      ('DetailReduction', FLOAT), ('Wind', VEC3)]:
        user_parameter(system, name, typ)
    lifecycle = {key: u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
                 for key in ['Life Cycle Mode', 'Loop Behavior']}
    lifecycle['Life Cycle Mode'] = lifecycle['Life Cycle Mode'].replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    lifecycle['Loop Behavior'] = lifecycle['Loop Behavior'].replace('NewEnumerator0', 'NewEnumerator1').replace('"Infinite"', '"Once"')
    layer(system, 'GroundDust', dust, False, lifecycle)
    layer(system, 'GroundColdMist', mist, True, lifecycle)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-340, -1200, -100), max=u.Vector(340, 1200, 210)))
    save(system)
    receipt = {'saved_assets': [system.get_path_name()], 'materials_reused': [DUST, MIST],
               'max_dust_particles': 48, 'max_mist_particles': 28, 'systems_per_landing': 1,
               'dust_opacity': .56, 'dust_base_size_cm': [96, 64],
               'dust_lifetime_seconds': [.85, 1.15], 'mist_lifetime_seconds': [1.1, 1.45],
               'one_shot': True, 'gameplay_tested': False}
    out = ROOT / 'Saved/IceWallSlamBoost20260930'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ICE_WALL_LANDING_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
