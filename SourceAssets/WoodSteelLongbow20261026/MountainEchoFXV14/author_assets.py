"""Author/save gold echo-arrow VFX. No preview, gameplay or acceptance run."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoFXV14'
DEST = '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoFXV14'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_torch_burn import setup_emitter
from build_fireball_impact_realistic import custom
from build_fireball_outer_flame import enable_sprite_usage
from build_fireball_fluid_burn import moving_translucency, compensate_emission

SAVED = []
SEED = 'frac(float(Particles.UniqueID)*.61803398875)'
VARIANT = 'frac(float(Particles.UniqueID)*.41421356237)'
ANGLE = f'(6.2831853*{VARIANT})'
AGE = 'Particles.Age'
N = 'Particles.NormalizedAge'


def save(asset):
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset, True):
        raise RuntimeError('Niagara compilation failed: ' + asset.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    (SOURCE / 'asset-receipt.json').write_text(json.dumps({'complete': False, 'saved': SAVED}, indent=2), encoding='utf-8')
    u.log('MOUNTAIN_ECHO_FX_SAVED ' + asset.get_path_name())


def material(name, shape):
    path = DEST + '/' + name
    mat = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    moving_translucency(mat)
    if shape == 'arrow':
        glow = custom(mat, 'return float3(3.8,1.65,.22);', {}, u.CustomMaterialOutputType.CMOT_FLOAT3)
        opacity = custom(mat, 'return .85;', {})
    else:
        enable_sprite_usage(mat)
        uv = LIB.create_material_expression(mat, u.MaterialExpressionTextureCoordinate)
        color = LIB.create_material_expression(mat, u.MaterialExpressionParticleColor)
        masks = {
            'core': 'float2 p=(UV-.5)*2;float r=dot(p,p);return exp(-r*5)*saturate(1-r)*Alpha;',
            'spark': 'float2 p=(UV-.5)*2;return pow(saturate(1-abs(p.x)),3)*pow(saturate(1-abs(p.y)),.8)*Alpha;',
            'ring': 'float r=length((UV-.5)*2);return exp(-pow((r-.78)*25,2))*saturate(1-r)*5*Alpha;'
        }
        opacity = custom(mat, masks[shape], {'UV': (uv, ''), 'Alpha': (color, 'A')})
        glow = custom(mat, 'return Color.rgb*float3(4.2,2.3,.42);', {'Color': (color, 'RGB')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_property(compensate_emission(mat, glow), '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(opacity, '', u.MaterialProperty.MP_OPACITY)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat


def system(name, donor, extent):
    path = DEST + '/' + name
    s = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(donor, path)
    if not s:
        raise RuntimeError('Cannot create ' + path)
    for emitter in emitters(s):
        API.call_method('RemoveEmitter', (ref(s, emitter),))
    s.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-extent, -extent, -extent), max=u.Vector(extent, extent, extent)))
    setdata('SetSystemData', u.NiagaraExt_SystemData, s, {'bFixedBounds': True})
    return s


def layer(s, name, mat, rate, position, size, life, alpha, direction='float3(1,0,0)', burst=None, ring=False):
    setup_emitter(s, name, mat, rate, True)
    if burst is not None:
        API.call_method('RemoveModule', (ref(s, name, 'EmitterUpdateScript', 'SpawnRate'),))
        donor = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
        for key in ['Life Cycle Mode', 'Loop Behavior']:
            value = u.RainAssetEditor.read_input(donor, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
            value = value.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"').replace('"Infinite"', '"Once"')
            put(s, name, 'EmitterUpdateScript', 'EmitterState', key, value, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        put(s, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=.85)')
        API.call_method('AddModule', (ref(s, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        put(s, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count', f'(Value={burst})', '/Script/Niagara.NiagaraInt32')
        put(s, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    if ring:
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(s, name, renderer=0), {'Alignment': 'Unaligned'})
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteAlignment': (VEC3, direction),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SubImageIndex': (FLOAT, '0'),
        'Particles.Color': (COLOR, f'float4(1,1,1,{alpha})'),
        'Particles.DynamicMaterialParameter': ('/Script/CoreUObject.Vector4f', 'float4(0,0,0,0)')
    }
    assignments(s, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, life), **common})
    assignments(s, name, 'ParticleUpdateScript', common)


def main():
    # Do not overwrite packages with editor-local unsaved work.
    dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    owned_dirty = [p.get_path_name() for p in dirty if p.get_path_name().startswith(DEST + '/')]
    if owned_dirty:
        raise RuntimeError('Unsaved destination packages: ' + str(owned_dirty))
    u.EditorAssetLibrary.make_directory(DEST)
    sys.path.insert(0, str(ROOT / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoFlightV19'))
    from author_flight import main as author_current_flight
    SAVED.extend(author_current_flight()['saved'])
    # Rebuilding the original bundle must keep the current impact treatment.
    sys.path.insert(0, str(ROOT / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoImpactV18'))
    from mountain_echo_impact_v18 import main as author_current_impact
    SAVED.extend(author_current_impact()['saved'])
    (SOURCE / 'asset-receipt.json').write_text(json.dumps({'complete': True, 'saved': SAVED, 'game_run': False}, indent=2), encoding='utf-8')


main()
