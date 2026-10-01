"""Author corrected persistent body soot; compile and save, without game/preview."""
from pathlib import Path
import json
import math
import sys
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
if Path(u.Paths.project_dir()).resolve().name not in ('FPSGAME', 'FPSGAME_MP'):
    raise RuntimeError('This asset batch belongs to FPSGAME')
sys.path[:0] = [str(ROOT / 'Tools/Skills')]
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter

DEST = '/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21'
E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
VEC4 = '/Script/CoreUObject.Vector4f'
HOLD_SECONDS, FADE_SECONDS, RATE = 8, 1.5, 8
L = u.MaterialEditingLibrary
MATERIAL_PATH = DEST + '/M_SlagPersistentBodySmoke'

def persistent_material():
    source = '/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke'
    material = (u.load_asset(MATERIAL_PATH) if E.does_asset_exist(MATERIAL_PATH)
                else E.duplicate_asset(source, MATERIAL_PATH))
    if not material:
        raise RuntimeError('Cannot author persistent slag smoke material')
    density = [node for node in L.get_material_expressions(material)
               if isinstance(node, u.MaterialExpressionCustom)
               and str(node.get_editor_property('description')) == 'ImpactSmokeCorrosion20260924 Density']
    if len(density) != 1:
        raise RuntimeError('Cannot find copied Mantaflow density expression')
    density[0].set_editor_property('code', (OUT / 'PersistentBodySmoke.hlsl').read_text('utf-8'))
    L.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    L.recompile_material(material)
    if not u.PoisonMaggotMonster.compile_material_assets([material]):
        raise RuntimeError('Persistent smoke material compilation failed')
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save persistent smoke material')
    return material



def build():
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if str(package.get_name()).startswith(DEST + '/'):
            raise RuntimeError('Preserve unsaved target: ' + package.get_name())
    name = 'NS_SlagBodySmoke'
    path = DEST + '/' + name
    system = (u.load_asset(path) if E.does_asset_exist(path)
              else TOOLS.create_asset(name, DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew()))
    if not system:
        raise RuntimeError('Cannot create ' + path)
    emitter = 'BodyRisingSoot'
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
    for name, typ in [('Radius', FLOAT), ('SmokeLifetime', FLOAT), ('SmokeHoldTime', FLOAT),
                      ('EmissionRate', FLOAT), ('EmitOrigin0', POSITION), ('EmitOrigin1', POSITION),
                      ('EmitOrigin2', POSITION), ('EmitDrift', VEC3)]:
        if 'User.' + name not in variables:
            user_parameter(system, name, typ)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'InterpolatedSpawnMode': 'RunUpdateScript',
             'CalculateBoundsMode': 'Dynamic'})
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    mode = str(u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="max(0,User.EmissionRate)")', HL)
    material = persistent_material()
    if not material:
        raise RuntimeError('Missing the existing rolling smoke surface')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, emitter, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 3000})

    seed = 'frac(float(Particles.UniqueID)*.61803398875+.137)'
    var = 'frac(float(Particles.UniqueID)*.41421356237+.273)'
    other = 'frac(float(Particles.UniqueID)*.75487766623+.413)'
    # Capture a body site in a separate spawn module. Reading animated origins
    # in the update script would drag already emitted smoke with the monster.
    site = f'({seed}<.3333333?User.EmitOrigin0:({seed}<.6666667?User.EmitOrigin1:User.EmitOrigin2))'
    assignments(system, emitter, 'ParticleSpawnScript', {
        'Particles.MistBirthPosition': (POSITION, site),
        'Particles.MistBirthDrift': (VEC3, 'User.EmitDrift')})
    tag = 'Fireball.Assignments.' + emitter + '.ParticleSpawnScript'
    E.set_metadata_tag(system, 'Slag.BodyCaptureModule', E.get_metadata_tag(system, tag))
    E.remove_metadata_tag(system, tag)

    a, n = 'max(0,Particles.Age)', 'saturate(Particles.NormalizedAge)'
    angle = f'({other}*6.2831853)'
    spread = (f'float3(cos({angle}),sin({angle}),({var}-.5)*.35)'
              f'*User.Radius*(.022+.060*sqrt({n}))*(.6+.4*{var})')
    roll = (f'float3(sin({a}*.48+{other}*6.283),cos({a}*.43+{seed}*6.283),'
            f'sin({a}*.35+{var}*6.283)*.4)*User.Radius*.025*saturate({a}*.6)')
    fade = f'saturate((User.SmokeLifetime-{a})/max(.01,User.SmokeLifetime-User.SmokeHoldTime))'
    smooth_fade = f'({fade}*{fade}*(3-2*{fade}))'
    common = {
        'Particles.Position': (POSITION, f'Particles.MistBirthPosition+Particles.MistBirthDrift*{a}'
                               f'+float3(0,0,.45*{a}*{a})+{spread}+{roll}'),
        'Particles.SpriteSize': (VEC2, f'User.Radius*(.38+.43*sqrt({n}))*(.94+.12*{other})*float2(1,1.12)'),
        'Particles.Color': (COLOR, f'float4(.030,.026,.028,.65*saturate({a}/.45)*{smooth_fade})'),
        'Particles.SpriteRotation': (FLOAT, f'{other}*6.2831853+{a}*({var}-.5)*.22'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)')}
    assignments(system, emitter, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, 'User.SmokeLifetime'), **common})
    assignments(system, emitter, 'ParticleUpdateScript', common)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-4000,-4000,-800), max=u.Vector(4000,4000,800)))
    E.set_metadata_tag(system, 'Slag.WorldSmokeRevision', '21')
    E.set_metadata_tag(system, 'Slag.CoverageScale', '1.5')
    E.set_metadata_tag(system, 'Slag.PersistentDensity', material.get_path_name())
    E.set_metadata_tag(system, 'Slag.BodySmokeSites', 'carapace,shell_L,shell_R')
    E.set_metadata_tag(system, 'Slag.DenseHoldSeconds', str(HOLD_SECONDS))
    if not u.RainAssetEditor.compile_rain(system):
        raise RuntimeError('Niagara compile failed: ' + system.get_path_name())
    if not E.save_loaded_asset(system, False):
        raise RuntimeError('Cannot save ' + system.get_path_name())
    receipt = dict(revision='SmokeVisibilityFixV21', saved_assets=[material.get_path_name(), system.get_path_name()],
                   interpolated_spawn_mode='RunUpdateScript', emitter_bounds_mode='Dynamic',
                   normalized_age_clamped=True, particle_alpha=.65,
                   density_atlas_phase=[.035, .485], material_age_erosion=False,
                   coverage_scale=1.5, effective_radius_cm=390,
                   world_space_particles=True, birth_position_and_drift_frozen=True,
                   body_sites=['carapace', 'shell_L', 'shell_R'],
                   smoke_hold_s=HOLD_SECONDS, smoke_fade_s=FADE_SECONDS,
                   smoke_lifetime_s=HOLD_SECONDS+FADE_SECONDS, rate_per_s=RATE,
                   maximum_particles=math.ceil((HOLD_SECONDS+FADE_SECONDS)*RATE),
                   rise_velocity_cm_s=18, rise_quadratic_cm_s2=.45,
                   sideways_drift_cm_s=[4, -3], gameplay_history_interval_s=.3,
                   maximum_gameplay_groups=32, origins_per_group=3,
                   preserved_blind_material='/Game/Monsters/HundredEyedSlag/WorldSmokeV19/M_SlagMistBlindView.M_SlagMistBlindView',
                   post_process_only_inside_smoke=True, clear_on_exit=True,
                   runtime_tested=False, interactive_editor_started=False)
    (OUT / 'asset_installation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf-8')
    u.log('SLAG_SMOKE_VISIBILITY_V21_ASSETS_SAVED ' + system.get_path_name())


if __name__ == '__main__':
    build()
