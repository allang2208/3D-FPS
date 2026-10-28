"""Author a bright arrow, local glow and a short world-space golden path."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoFlightV19'
DEST = '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoFlightV19'
ACTIVE = '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoFXV14'
SYSTEM_PATH = ACTIVE + '/NS_MountainEcho_GoldenFlight'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_torch_burn import setup_emitter
from build_fireball_impact_realistic import custom
from build_fireball_outer_flame import enable_sprite_usage
from build_fireball_fluid_burn import moving_translucency, compensate_emission

SAVED = []
N = 'Particles.NormalizedAge'
S = 'frac(float(Particles.UniqueID)*.61803398875)'
V = 'frac(float(Particles.UniqueID)*.41421356237)'
THETA = f'({V}*6.2831853)'
WIDTH = 'clamp(Engine.Owner.LODDistance/1600,1,3)'
SPEED = 'length(Engine.Owner.Velocity)'
DIRECTION = f'({SPEED}>1 ? normalize(Engine.Owner.Velocity) : Engine.Owner.SystemXAxis)'
SWEPT = f'(Engine.Owner.Position-Engine.Owner.Velocity*Engine.DeltaTime*(1-{S}))'


def save(asset):
    if isinstance(asset, u.Material):
        errors = LIB.recompile_material(asset)
        if errors:
            raise RuntimeError(str(errors))
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset, True):
        raise RuntimeError('Flight Niagara compilation failed')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    (OUT / 'asset-receipt.json').write_text(json.dumps({'complete': False, 'saved': SAVED}, indent=2), encoding='utf-8')
    u.log('MOUNTAIN_FLIGHT_V19_SAVED ' + asset.get_path_name())


def material(name, kind):
    folder = ACTIVE if kind == 'arrow' else DEST
    path = folder + '/' + name
    mat = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('two_sided', True)
    moving_translucency(mat)
    if kind == 'arrow':
        glow = custom(mat, 'return float3(8,4.6,.8);', {}, u.CustomMaterialOutputType.CMOT_FLOAT3)
        alpha = custom(mat, 'return .95;', {})
    else:
        enable_sprite_usage(mat)
        uv = LIB.create_material_expression(mat, u.MaterialExpressionTextureCoordinate)
        color = LIB.create_material_expression(mat, u.MaterialExpressionParticleColor)
        shape = {
            'core': 'float2 p=(UV-.5)*2;float end=1-smoothstep(.55,1,abs(p.y));float width=.42+.25*(1-abs(p.y));return exp(-pow(p.x/width,2)*2)*end*(1-smoothstep(.85,1,abs(p.x)))*Alpha;',
            'halo': 'float2 p=(UV-.5)*2;return exp(-p.x*p.x*4)*pow(saturate(1-abs(p.y)),.55)*(1-smoothstep(.8,1,abs(p.x)))*Alpha;',
            'head': 'float2 p=(UV-.5)*2;float r=dot(p,p);return exp(-r*3.5)*saturate(1-r)*Alpha;'
        }[kind]
        alpha = custom(mat, shape, {'UV': (uv, ''), 'Alpha': (color, 'A')})
        gain = {'core': 'float3(8,4.8,1)', 'halo': 'float3(4.5,2.5,.38)', 'head': 'float3(10,6.7,1.9)'}[kind]
        glow = custom(mat, f'return Color.rgb*{gain};', {'Color': (color, 'RGB')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_property(compensate_emission(mat, glow), '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY)
    save(mat)
    return mat


def configure(system, name, mat, rate, local, aligned=True):
    setup_emitter(system, name, mat, 0, local)
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="({rate})*saturate(User.Flying)")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Alignment': 'CustomAlignment' if aligned else 'Unaligned', 'FacingMode': 'FaceCamera', 'SortOrderHint': 0})


def defaults(position, size, alpha, direction='float3(1,0,0)', velocity='float3(0,0,0)'):
    return {
        'Particles.Position': (POSITION, position), 'Particles.Velocity': (VEC3, velocity),
        'Particles.SpriteAlignment': (VEC3, direction), 'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'), 'Particles.SpriteSize': (VEC2, size),
        'Particles.SubImageIndex': (FLOAT, '0'), 'Particles.Color': (COLOR, f'float4(1,1,1,{alpha})'),
        'Particles.DynamicMaterialParameter': ('/Script/CoreUObject.Vector4f', 'float4(0,0,0,0)')}


def local_layer(system, name, mat, position, size, alpha, aligned):
    configure(system, name, mat, '60', True, aligned)
    common = defaults(position, size, f'({alpha})*saturate(User.Flying)')
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, '.065'), **common})
    assignments(system, name, 'ParticleUpdateScript', common)


def path_layer(system, name, mat, halo=False):
    spacing, cap, length, width, life, opacity = ('42', '220', '110', '18', '.26', '.10') if halo else ('22', '420', '86', '6.5', '.21', '.68')
    configure(system, name, mat, f'clamp({SPEED}/{spacing},0,{cap})', False)
    # Niagara derives Owner.Velocity from component displacement. Distribute each
    # frame's births on that actual swept segment, including replicated movement.
    # Centre each stroke behind its birth point so it cannot extend past the arrow.
    position = f'{SWEPT}-{DIRECTION}*(max(10,User.Length)*.35+{length}*.5)'
    size = f'float2({width}*{WIDTH},{length})'
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, life), **defaults(position, size, opacity, DIRECTION)})
    # Position and alignment remain at birth values in world space.
    assignments(system, name, 'ParticleUpdateScript', {
        'Particles.SpriteSize': (VEC2, f'float2({width}*{WIDTH}*(1-.25*{N}),{length})'),
        'Particles.Color': (COLOR, f'float4(1,1,lerp(1,.4,{N}),{opacity}*pow(1-{N},.85))')})


def main():
    SAVED.clear()
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = [p for p in dirty if p in [SYSTEM_PATH, ACTIVE + '/M_MountainEcho_GoldenArrow'] or p.startswith(DEST + '/')]
    if conflicts:
        raise RuntimeError('Preserve unsaved flight assets: ' + str(conflicts))
    u.EditorAssetLibrary.make_directory(DEST)
    material('M_MountainEcho_GoldenArrow', 'arrow')
    core = material('M_MountainEcho_PathCore', 'core')
    halo = material('M_MountainEcho_PathHalo', 'halo')
    head = material('M_MountainEcho_HeadGlow', 'head')
    system = u.load_asset(SYSTEM_PATH)
    if not system:
        raise RuntimeError('Missing current golden flight system')
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))
    user_parameter(system, 'Length', FLOAT)
    user_parameter(system, 'Flying', FLOAT)
    local_layer(system, 'GoldenArrowAura', halo, 'float3(-max(10,User.Length)*.5,0,0)',
                f'float2(11*{WIDTH},max(10,User.Length)+24)', f'.14*(1-{N})', True)
    local_layer(system, 'GoldenArrowhead', head, 'float3(-3,0,0)',
                f'float2(17,17)*sqrt({WIDTH})', f'.7*(1-{N})', False)
    path_layer(system, 'GoldenPathCore', core)
    path_layer(system, 'GoldenPathHalo', halo, True)
    configure(system, 'GoldenPathMotes', core, f'min(60,{SPEED}/80)', False)
    offset = f'(Engine.Owner.SystemYAxis*cos({THETA})+Engine.Owner.SystemZAxis*sin({THETA}))'
    values = defaults(f'{SWEPT}-Engine.Owner.SystemXAxis*max(10,User.Length)*.7+{offset}*2',
                      f'float2(3.6*sqrt({WIDTH}),10+{S}*12)', '.6', DIRECTION, f'{offset}*(8+{S}*8)')
    assignments(system, 'GoldenPathMotes', 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, f'.12+{S}*.1'), **values})
    assignments(system, 'GoldenPathMotes', 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.Color': (COLOR, f'float4(1,.95,.7,.6*pow(1-{N},1.1))')})
    # CPU particle bounds follow the finite world-space tail at any arrow speed.
    setdata('SetSystemData', u.NiagaraExt_SystemData, system, {'bFixedBounds': False, 'bInitialOwnerVelocityFromActor': False})
    save(system)
    result = {'complete': True, 'saved': list(SAVED), 'runtime_path': SYSTEM_PATH,
              'maximum_tail_seconds': .26, 'world_particle_rate_cap': 700,
              'core_spacing_cm': 22, 'core_stroke_cm': 86, 'game_run': False, 'runtime_tested': False}
    (OUT / 'asset-receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    main()
