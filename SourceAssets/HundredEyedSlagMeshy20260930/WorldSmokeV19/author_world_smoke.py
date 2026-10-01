"""Save world-space wake smoke and an in-smoke blur overlay; no game or preview."""
from pathlib import Path
import json
import sys
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
if Path(u.Paths.project_dir()).resolve().name not in ('FPSGAME', 'FPSGAME_MP'):
    raise RuntimeError('This asset batch belongs to FPSGAME')
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from author_river_pilot import node, prop, scalar, custom

DEST = '/Game/Monsters/HundredEyedSlag/WorldSmokeV19'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
VEC4 = '/Script/CoreUObject.Vector4f'
SAVED = []


def own(name, cls, factory):
    path = DEST + '/' + name
    obj = u.load_asset(path) if E.does_asset_exist(path) else TOOLS.create_asset(name, DEST, cls, factory)
    if not obj:
        raise RuntimeError('Cannot create ' + path)
    return obj


def save(obj):
    if isinstance(obj, u.Material):
        errors = L.recompile_material(obj)
        if errors:
            raise RuntimeError('Material compile: ' + str(errors))
    if isinstance(obj, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(obj):
        raise RuntimeError('Niagara compile failed: ' + obj.get_path_name())
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Cannot save ' + obj.get_path_name())
    SAVED.append(obj.get_path_name())
    u.log('SLAG_WORLD_SMOKE_SAVED ' + obj.get_path_name())


def blind_material():
    m = own('M_SlagMistBlindView', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain', u.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property('blendable_location', u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    m.set_editor_property('blendable_priority', 40)
    scene = node(m, u.MaterialExpressionSceneTexture)
    scene.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    scene.set_editor_property('filtered', True)
    noise = node(m, u.MaterialExpressionTextureObjectParameter)
    noise.set_editor_property('parameter_name', 'NoiseTex')
    texture = u.load_asset('/Game/Monsters/HundredEyedSlag/BlackMistV17/T_SlagDensityNoise')
    if not texture:
        raise RuntimeError('Missing the saved original smoke density texture')
    noise.set_editor_property('texture', texture)
    noise.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    result = custom(m, (OUT / 'blind_view.hlsl').read_text('utf-8'),
                    {'SceneColor': (scene, 'Color'), 'NoiseTex': noise,
                     'Time': node(m, u.MaterialExpressionTime),
                     'BlindStrength': scalar(m, 'BlindStrength', 0)}, 3,
                    'Slag in-smoke defocus, distortion and soot film')
    prop(m, result, 'EMISSIVE_COLOR')
    save(m)


def smoke():
    system = own('NS_SlagSmokeTrail', u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    emitter = 'WorldSootWake'
    for old in emitters(system):
        for script in ['EmitterSpawnScript', 'EmitterUpdateScript', 'ParticleSpawnScript', 'ParticleUpdateScript']:
            E.remove_metadata_tag(system, 'Fireball.Assignments.' + old + '.' + script)
        API.call_method('RemoveEmitter', (ref(system, old),))
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), emitter))
    trim(system, emitter, {'EmitterUpdateScript': ['EmitterState'],
                          'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    API.call_method('AddModule', (ref(system, emitter, 'EmitterUpdateScript'),
                                  u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    variables = str(API.call_method('GetUserVariables', (system,)).export_text())
    for name, typ in [('Radius', FLOAT), ('SmokeLifetime', FLOAT), ('EmissionRate', FLOAT),
                      ('EmitOrigin', POSITION), ('EmitDrift', VEC3)]:
        if 'User.' + name not in variables:
            user_parameter(system, name, typ)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    mode = str(u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,User.EmissionRate)")', HL)
    material = u.load_asset('/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke')
    if not material:
        raise RuntimeError('Missing approved rolling smoke surface')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, emitter, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 3000})
    # Capture in a separate spawn module before any expression reads these attributes.
    assignments(system, emitter, 'ParticleSpawnScript', {
        'Particles.MistBirthPosition': (POSITION, 'User.EmitOrigin'),
        'Particles.MistBirthDrift': (VEC3, 'User.EmitDrift')})
    tag = 'Fireball.Assignments.' + emitter + '.ParticleSpawnScript'
    E.set_metadata_tag(system, 'Slag.WakeCaptureModule', E.get_metadata_tag(system, tag))
    E.remove_metadata_tag(system, tag)
    seed = 'frac(float(Particles.UniqueID)*.61803398875+.137)'
    var = 'frac(float(Particles.UniqueID)*.41421356237+.273)'
    other = 'frac(float(Particles.UniqueID)*.75487766623+.413)'
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    z = f'({var}*2-1)'
    angle = f'({other}*6.2831853+{a}*.26)'
    direction = f'float3(sqrt(max(0,1-{z}*{z}))*cos({angle}),sqrt(max(0,1-{z}*{z}))*sin({angle}),{z})'
    spread = f'{direction}*User.Radius*.14*sqrt({seed})*(1+.7*sqrt({n}))'
    roll = f'float3(sin({a}*.8+{other}*6.283),cos({a}*.7+{seed}*6.283),sin({a}*.6+{var}*6.283))*User.Radius*.04'
    common = {
        'Particles.Position': (POSITION, f'Particles.MistBirthPosition+Particles.MistBirthDrift*{a}+{spread}+{roll}'),
        'Particles.SpriteSize': (VEC2, f'User.Radius*(.52+.50*sqrt({n}))*(.9+.14*{other})*float2(1,1.05)'),
        'Particles.Color': (COLOR, f'float4(.030,.026,.028,.60*saturate({n}*12)*saturate((1-{n})*4))'),
        'Particles.SpriteRotation': (FLOAT, f'{other}*6.2831853+{a}*({var}-.5)*.35'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)')}
    assignments(system, emitter, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, 'User.SmokeLifetime'), **common})
    assignments(system, emitter, 'ParticleUpdateScript', common)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1600,-1600,-800), max=u.Vector(1600,1600,800)))
    E.set_metadata_tag(system, 'Slag.WorldSmokeRevision', '19')
    save(system)


def build():
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if str(package.get_name()).startswith(DEST + '/'):
            raise RuntimeError('Preserve unsaved target: ' + package.get_name())
    blind_material()
    smoke()
    receipt = dict(revision='WorldSmokeV19', saved_assets=SAVED,
                   world_space_particles=True, birth_position_and_drift_frozen=True,
                   smoke_lifetime_s=3.6, rate_per_s=12, maximum_particles=44,
                   gameplay_history_interval_s=.3, maximum_gameplay_puffs=16,
                   post_process_only_inside_smoke=True, clear_on_exit=True,
                   blind_seconds_refreshed_inside=2, blur_scene_samples=9,
                   copied_valve_assets_or_code=False,
                   presentation_reference='https://cdn.steamstatic.com/apps/valve/2009/GDC2009_ReplayableCooperativeGameDesign_Left4Dead.pdf',
                   runtime_tested=False, interactive_editor_started=False)
    (OUT / 'asset_installation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf-8')
    u.log('SLAG_WORLD_SMOKE_ASSETS_SAVED')


if __name__ == '__main__':
    build()
