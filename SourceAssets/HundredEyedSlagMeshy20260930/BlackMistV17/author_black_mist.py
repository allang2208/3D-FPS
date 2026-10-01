"""Produce and save monster-owned smoke assets through the existing UE bridge."""
from pathlib import Path
import json
import sys
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
project = Path(u.Paths.project_dir()).resolve()
if project.name not in ('FPSGAME', 'FPSGAME_MP'):
    raise RuntimeError('This asset batch belongs to FPSGAME only: ' + str(project))
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, POSITION, COLOR
from build_fireball_flight import user_parameter
from author_river_pilot import node, prop, scalar, vector, custom

DEST = '/Game/Monsters/HundredEyedSlag/BlackMistV17'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SAVED = []
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
VEC4 = '/Script/CoreUObject.Vector4f'


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
        raise RuntimeError('Niagara compile failed ' + obj.get_path_name())
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Cannot save ' + obj.get_path_name())
    SAVED.append(obj.get_path_name())
    u.log('SLAG_BLACK_MIST_SAVED ' + obj.get_path_name())


def density():
    task = u.AssetImportTask()
    for key, value in dict(filename=str(OUT / 'slag_density_noise.png'), destination_path=DEST,
                           destination_name='T_SlagDensityNoise', automated=True,
                           replace_existing=True, save=False).items():
        task.set_editor_property(key, value)
    TOOLS.import_asset_tasks([task])
    texture = u.load_asset(DEST + '/T_SlagDensityNoise')
    if not texture:
        raise RuntimeError('Density texture import failed')
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_GRAYSCALE)
    for axis in ['address_x', 'address_y']:
        texture.set_editor_property(axis, u.TextureAddress.TA_WRAP)
    save(texture)
    return texture


def view_material(texture):
    mat = own('M_SlagMistView', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain', u.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location', u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    mat.set_editor_property('blendable_priority', 40)
    scene = node(mat, u.MaterialExpressionSceneTexture)
    scene.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    noise = node(mat, u.MaterialExpressionTextureObjectParameter)
    noise.set_editor_property('parameter_name', 'NoiseTex')
    noise.set_editor_property('texture', texture)
    noise.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    inputs = dict(SceneColor=(scene, 'Color'), PixelPos=node(mat, u.MaterialExpressionWorldPosition),
                  CameraOrigin=node(mat, u.MaterialExpressionCameraPositionWS),
                  Time=node(mat, u.MaterialExpressionTime),
                  NoiseTex=noise, BlindStrength=scalar(mat, 'BlindStrength', 0))
    for i in range(4):
        inputs['MistSphere' + str(i)] = (vector(mat, 'MistSphere' + str(i), (0, 0, 0, 0)), 'RGBA')
    output = custom(mat, (OUT / 'mist_view.hlsl').read_text('utf-8'), inputs, 3, 'Slag bounded soot and blindness')
    prop(mat, output, 'EMISSIVE_COLOR')
    E.set_metadata_tag(mat, 'Slag.BlackMistRevision', '17')
    save(mat)


def smoke_system():
    system = own('NS_SlagBlackMist', u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    emitter = 'SlagRollingSoot'
    for old in emitters(system):
        for script in ['EmitterSpawnScript', 'EmitterUpdateScript', 'ParticleSpawnScript', 'ParticleUpdateScript']:
            E.remove_metadata_tag(system, 'Fireball.Assignments.' + old + '.' + script)
        API.call_method('RemoveEmitter', (ref(system, old),))
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), emitter))
    trim(system, emitter, {'EmitterUpdateScript': ['EmitterState'],
                          'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    API.call_method('AddModule', (ref(system, emitter, 'EmitterUpdateScript'),
                                  u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    if 'User.Radius' not in str(API.call_method('GetUserVariables', (system,)).export_text()):
        user_parameter(system, 'Radius', FLOAT)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    lifecycle = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    mode = str(u.RainAssetEditor.read_input(lifecycle, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(lifecycle, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)
    put(system, emitter, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(HlslExpression="12.0")', HL)
    material = u.load_asset('/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke')
    if not material:
        raise RuntimeError('Missing existing rolling smoke surface')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, emitter, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 3000})
    seed = 'frac(float(Particles.UniqueID)*.61803398875+.137)'
    var = 'frac(float(Particles.UniqueID)*.41421356237+.273)'
    other = 'frac(float(Particles.UniqueID)*.75487766623+.413)'
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    z = f'({var}*2-1)'
    angle = f'({other}*6.2831853+{a}*.17)'
    direction = f'float3(sqrt(max(0,1-{z}*{z}))*cos({angle}),sqrt(max(0,1-{z}*{z}))*sin({angle}),{z})'
    curl = f'float3(sin({a}*.8+{other}*6.283),cos({a}*.7+{seed}*6.283),sin({a}*.6+{var}*6.283))*User.Radius*.06'
    common = {
        'Particles.Position': (POSITION, f'{direction}*User.Radius*(.12+.55*sqrt({seed}))+{curl}'),
        'Particles.SpriteSize': (VEC2, f'User.Radius*(.42+.2*{other})*(.8+.3*sqrt({n}))*float2(1,1.05)'),
        'Particles.Color': (COLOR, f'float4(.017,.014,.019,.42*saturate({n}*8)*saturate((1-{n})*5))'),
        'Particles.SpriteRotation': (FLOAT, f'{other}*6.2831853+{a}*({var}-.5)*.28'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)')}
    assignments(system, emitter, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, f'2.1+.7*{seed}'), **common})
    assignments(system, emitter, 'ParticleUpdateScript', common)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-520, -520, -520), max=u.Vector(520, 520, 520)))
    E.set_metadata_tag(system, 'Slag.BlackMistRevision', '17')
    save(system)


def build():
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if str(package.get_name()).startswith(DEST + '/'):
            raise RuntimeError('Preserve existing unsaved mist asset: ' + package.get_name())
    view_material(density())
    smoke_system()
    receipt = dict(revision='BlackMistV17', saved_assets=SAVED, radius_cm=260,
                   offset_from_monster_feet_cm=[-245, 0, 120], blind_seconds=2,
                   near_clear_cm=80, far_dark_cm=250, maximum_view_clouds=4,
                   density_samples_per_cloud=3, spawn_rate=12, maximum_sprites_per_cloud=34,
                   reference='https://github.com/geb0598/IVSmoke',
                   third_party_code_or_assets_copied=False,
                   runtime_tested=False, editor_started=False)
    (OUT / 'asset_installation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), 'utf-8')
    u.log('SLAG_BLACK_MIST_ASSETS_SAVED')


if __name__ == '__main__':
    build()
