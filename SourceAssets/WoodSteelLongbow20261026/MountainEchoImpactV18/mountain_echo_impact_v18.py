"""Author/save readable gold impact fragments after V17 visibility feedback."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoImpactV18'
DEST = '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoImpactV18'
SYSTEM_PATH = '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoFXV14/NS_MountainEcho_GoldenImpact'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_torch_burn import setup_emitter
from build_fireball_impact_realistic import custom
from build_fireball_outer_flame import enable_sprite_usage
from build_fireball_fluid_burn import moving_translucency, compensate_emission

SAVED = []
A = 'Particles.Age'
N = 'Particles.NormalizedAge'
PHASE = 'frac(sin(float(Engine.System.RandomSeed)*.0131)*43758.5453)'
S = f'frac(sin(float(Particles.UniqueID)*12.9898+{PHASE}*97.17)*43758.5453)'
V = f'frac(sin(float(Particles.UniqueID)*39.3467+{PHASE}*61.43)*24634.6345)'
W = f'frac(sin(float(Particles.UniqueID)*73.1561+{PHASE}*17.37)*56445.2341)'
THETA = f'({V}*6.2831853)'
# Preserve a readable streak width at bow distances, capped for distant hits.
WIDTH_SCALE = 'clamp(Engine.Owner.LODDistance/1600,1,3)'


def save(asset):
    if isinstance(asset, u.Material):
        errors = LIB.recompile_material(asset)
        if errors:
            raise RuntimeError(asset.get_path_name() + ': ' + str(errors))
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset, True):
        raise RuntimeError('Niagara compilation failed: ' + asset.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    (OUT / 'asset-receipt.json').write_text(json.dumps({'complete': False, 'saved': SAVED}, indent=2), encoding='utf-8')
    u.log('MOUNTAIN_IMPACT_V18_SAVED ' + asset.get_path_name())


def light_material(name, shape):
    path = DEST + '/' + name
    mat = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('two_sided', True)
    moving_translucency(mat)
    enable_sprite_usage(mat)
    uv = LIB.create_material_expression(mat, u.MaterialExpressionTextureCoordinate)
    color = LIB.create_material_expression(mat, u.MaterialExpressionParticleColor)
    shapes = {
        'flash': 'float2 p=(UV-.5)*2;float r=dot(p,p);float angle=atan2(p.y,p.x);float edge=1+.11*sin(angle*5+.4)+.06*sin(angle*9);return exp(-r*6)*saturate(edge-r)*Alpha;',
        'needle': 'float2 p=(UV-.5)*2;float taper=saturate(1-abs(p.y));float width=.24+.60*taper;float edge=1-smoothstep(.8,1,abs(p.x));return exp(-pow(p.x/width,2)*2.8)*pow(taper,.45)*edge*Alpha;',
        'chip': 'float2 p=(UV-.5)*2;float edge=min(min(.76-abs(p.x+.26*p.y),.85-abs(p.y)),.92-abs(p.x-p.y*.38));return smoothstep(0,.13,edge)*(.45+.55*saturate(p.x*.6-p.y*.5+.45))*Alpha;'
    }
    mask = custom(mat, shapes[shape], {'UV': (uv, ''), 'Alpha': (color, 'A')})
    gain = 'float3(6.5,4.3,1.35)' if shape == 'flash' else 'float3(9,5.4,1.1)'
    emission = custom(mat, f'return Color.rgb*{gain};', {'Color': (color, 'RGB')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    fade = LIB.create_material_expression(mat, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 1.5)
    LIB.connect_material_expressions(mask, '', fade, str(LIB.get_material_expression_input_names(fade)[0]))
    LIB.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    LIB.connect_material_property(compensate_emission(mat, emission), '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    save(mat)
    return mat


def dust_material():
    path = DEST + '/M_MountainEcho_ContactDust'
    mat = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(
        '/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke', path)
    if not mat:
        raise RuntimeError('Missing authored Mantaflow impact-smoke material')
    # Independent material; retain its 8x8 density atlas and soft frame borders.
    save(mat)
    return mat


def layer(system, name, mat, count, life, position, velocity, size, alpha, tint,
          delay=0., aligned=True, dust=False):
    setup_emitter(system, name, mat, 0, True)
    API.call_method('RemoveModule', (ref(system, name, 'EmitterUpdateScript', 'SpawnRate'),))
    donor = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    for key in ['Life Cycle Mode', 'Loop Behavior']:
        value = u.RainAssetEditor.read_input(donor, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
        value = value.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"').replace('"Infinite"', '"Once"')
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=1.1)')
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count', f'(Value={count})', '/Script/Niagara.NiagaraInt32')
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', f'(Value={delay})')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Alignment': 'CustomAlignment' if aligned else 'Unaligned',
        'FacingMode': 'FaceCamera', 'SortOrderHint': -1 if dust else 1
    })
    # Analytic drag/gravity and one contact plane, without particle world traces.
    p = f'float3(({position}).xy,max(1.5,({position}).z))'
    values = {
        'Particles.Position': (POSITION, p),
        'Particles.Velocity': (VEC3, velocity),
        'Particles.SpriteAlignment': (VEC3, f'normalize(({velocity})+float3(.001,0,0))'),
        'Particles.SpriteRotation': (FLOAT, '0' if aligned else f'({S}*6.2831853+{A}*({W}-.5)*2)'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SubImageIndex': (FLOAT, '0'),
        'Particles.Color': (COLOR, f'float4({tint},{alpha})'),
        'Particles.DynamicMaterialParameter': ('/Script/CoreUObject.Vector4f', f'float4({S},0,0,0)')
    }
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, life), **values})
    assignments(system, name, 'ParticleUpdateScript', values)


def main():
    SAVED.clear()
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = [p for p in dirty if p == SYSTEM_PATH or p.startswith(DEST + '/')]
    if conflicts:
        raise RuntimeError('Preserve unsaved impact packages: ' + str(conflicts))
    u.EditorAssetLibrary.make_directory(DEST)
    flash = light_material('M_MountainEcho_ContactFlash', 'flash')
    needle = light_material('M_MountainEcho_HotNeedle', 'needle')
    chip = light_material('M_MountainEcho_HotChip', 'chip')
    dust = dust_material()
    system = u.load_asset(SYSTEM_PATH) if u.EditorAssetLibrary.does_asset_exist(SYSTEM_PATH) else u.EditorAssetLibrary.duplicate_asset(
        '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small', SYSTEM_PATH)
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    user_parameter(system, 'LocalUp', VEC3)
    layer(system, 'CompressedContact', flash, 1, '.11', 'float3(0,0,3)', 'float3(0,0,1)',
          f'float2(42,60)*(.65+.35*saturate({A}/.015))', f'pow(1-{N},1.5)', 'float3(1,1,1)', aligned=False)
    layer(system, 'ShortContactBloom', flash, 1, '.17', 'float3(0,0,4)', 'float3(0,0,1)',
          f'float2(75,75)*(.7+.3*{N})', f'.18*pow(1-{N},1.6)', 'float3(1,.85,.6)', aligned=False)
    # Favour visible lateral spread over a narrow spray toward the shooter.
    direction = f'normalize(float3(cos({THETA}),sin({THETA}),.25+{S}*.8))'
    speed = f'(1100+{S}*800)'
    velocity = f'{direction}*{speed}*exp(-{A}*9)'
    position = f'float3(0,0,3)+{direction}*{speed}*(1-exp(-{A}*9))/9'
    layer(system, 'ImpulseFilaments', needle, 12, f'.16+{W}*.10', position, velocity,
          f'float2((3.6+{S}*2.2)*{WIDTH_SCALE},(32+{V}*40)*exp(-{A}*5)+7)',
          f'.95*pow(saturate((1-{N})/.65),.8)', 'float3(1,1,.9)')
    speed = f'(850+{S}*850)'
    velocity = f'{direction}*{speed}*exp(-{A}*6)-User.LocalUp*{A}*760'
    position = f'float3(0,0,3)+{direction}*{speed}*(1-exp(-{A}*6))/6-User.LocalUp*{A}*{A}*380'
    layer(system, 'BallisticGoldSparks', needle, 36, f'.42+{W}*.28', position, velocity,
          f'float2((3.4+{V}*2.4)*{WIDTH_SCALE},(24+{S}*32)*exp(-{A}*3.3)+6)',
          f'.95*pow(saturate((1-{N})/.45),.85)',
          f'lerp(float3(1,1,.95),float3(.6,.4,.15),saturate(({N}-.3)/.7))')
    speed = f'(330+{V}*400)'
    velocity = f'{direction}*{speed}*exp(-{A}*3.4)-User.LocalUp*{A}*980'
    position = f'float3(0,0,3)+{direction}*{speed}*(1-exp(-{A}*3.4))/3.4-User.LocalUp*{A}*{A}*490'
    layer(system, 'CoolingGoldChips', chip, 16, f'.52+{W}*.32', position, velocity,
          f'float2(3.2+{S}*2.6,5+{V}*4)*sqrt({WIDTH_SCALE})*(1-.2*{N})',
          f'.85*pow(saturate((1-{N})/.6),.9)',
          f'lerp(float3(1,1,.85),float3(.45,.24,.06),saturate(({N}-.2)/.8))', delay=.018, aligned=False)
    position = f'float3(0,0,4)+{direction}*(4+22*(1-exp(-{A}*7)))+User.LocalUp*{A}*6'
    layer(system, 'ContactDensityWisps', dust, 3, f'.4+{S}*.18', position, 'float3(0,0,1)',
          f'float2(22+{V}*13,28+{S}*16)*(.45+.65*{N})',
          f'.24*saturate({N}*12)*pow(1-{N},1.6)*saturate((14000-Engine.Owner.LODDistance)/6000)',
          'float3(.17,.14,.095)', delay=.025, aligned=False, dust=True)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-460,-460,-460), max=u.Vector(460,460,460)))
    setdata('SetSystemData', u.NiagaraExt_SystemData, system, {'bFixedBounds': True})
    save(system)
    result = {'complete': True, 'saved': list(SAVED), 'runtime_path': SYSTEM_PATH,
              'particles_per_impact': 69, 'maximum_particle_lifetime_seconds': .84,
              'game_run': False, 'runtime_tested': False}
    (OUT / 'asset-receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    main()
