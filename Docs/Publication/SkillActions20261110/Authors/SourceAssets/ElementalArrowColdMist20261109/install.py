"""Author cold-arrow condensation and outward white motes. No playback/rendering."""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
DEST = '/Game/Skills/ElementalArrow20261109/ColdMistV2'
SOURCE = '/Game/Skills/IceSpike/FrostV2/NS_ColdMist'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, TOOLS, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_ice_spike_assets import custom

SAVED = []


def owned(name, source=None):
    path = DEST + '/' + name
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:
        raise RuntimeError('Preserve unsaved target: ' + path)
    disk = ROOT / ('Content/' + path.removeprefix('/Game/') + '.uasset')
    backup = OUT / 'Before' / disk.name
    if disk.exists() and not backup.exists():
        shutil.copy2(disk, backup)
    if u.EditorAssetLibrary.does_asset_exist(path):
        return u.load_asset(path)
    asset = u.EditorAssetLibrary.duplicate_asset(source, path) if source else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    if asset is None:
        raise RuntimeError('Cannot create ' + path)
    return asset


def save(asset):
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset, True):
        raise RuntimeError('Niagara compilation failed: ' + asset.get_path_name())
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())


def materials():
    mist = owned('MI_ArrowColdMist', '/Game/Skills/IceSpike/FrostV2/MI_ColdMist')
    for key, value in [('Opacity Gain', .85), ('Emissive Gain', .10),
                       ('Near Fade Distance', 8), ('Depth Fade Distance', 3)]:
        LIB.set_material_instance_scalar_parameter_value(mist, key, value)
    LIB.update_material_instance(mist)
    save(mist)

    motes = owned('M_ArrowWhiteMotes')
    LIB.delete_all_material_expressions(motes)
    for key, value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT,
                           shading_model=u.MaterialShadingModel.MSM_UNLIT,
                           two_sided=True, disable_depth_test=False,
                           enable_responsive_aa=True, output_translucent_velocity=False,
                           translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF).items():
        motes.set_editor_property(key, value)
    uv = LIB.create_material_expression(motes, u.MaterialExpressionTextureCoordinate)
    color = LIB.create_material_expression(motes, u.MaterialExpressionParticleColor)
    depth = LIB.create_material_expression(motes, u.MaterialExpressionPixelDepth)
    mask = custom(motes, 'float2 p=(UV-.5)*2; return pow(saturate(1-dot(p,p)),2)*A*saturate((D-8)/12);',
                  {'UV': (uv, ''), 'A': (color, 'A'), 'D': (depth, '')})
    fade = LIB.create_material_expression(motes, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 2)
    LIB.connect_material_expressions(mask, '', fade, 'InOpacity')
    LIB.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    # White soft dots, no crystal silhouettes, star flare or bright bloom core.
    gain = custom(motes, 'return C*.65;', {'C': (color, 'RGB')}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    eye = LIB.create_material_expression(motes, u.MaterialExpressionEyeAdaptationInverse)
    LIB.connect_material_expressions(gain, '', eye, str(LIB.get_material_expression_input_names(eye)[0]))
    LIB.connect_material_property(eye, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.set_material_usage(motes, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    errors = LIB.recompile_material(motes)
    if errors:
        raise RuntimeError(str(errors))
    save(motes)
    return mist, motes


def layer(system, name, mat, mist, burst, lifecycle):
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                       'ParticleSpawnScript': ['InitializeParticle'],
                       'ParticleUpdateScript': ['ParticleState']})
    for script in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        u.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    top = API.call_method('GetEmitterTopology', (ref(system, name),))
    for renderer in sorted(top.get_editor_property('renderers'), key=lambda r: -r.get_editor_property('renderer_index')):
        index = renderer.get_editor_property('renderer_index')
        if index > 0:
            API.call_method('RemoveRenderer', (ref(system, name, renderer=index),))
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8 if mist else 1, 'Y': 8 if mist else 1}, 'bSubImageBlend': mist,
        'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera', 'bCastShadows': False,
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'MotionVectorSetting': 'Disable',
    })
    for key, value in lifecycle.items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=1.6)')
    module = 'SpawnBurst_Instantaneous' if burst else 'SpawnRate'
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/' + module)))
    count = ('12' if mist else '28') if burst else ('18' if mist else '26')
    expression(system, name, 'EmitterUpdateScript', module, 'Spawn Count' if burst else 'SpawnRate',
               ('floor(' if burst else '(') + count + '*saturate(User.Detail)' + ('+.5)' if burst else ')'))
    if burst:
        put(system, name, 'EmitterUpdateScript', module, 'Spawn Time', '(Value=0)')
    seed = '(float(Particles.UniqueID)+User.VariationSeed+1.)'
    a = f'frac(abs(sin({seed}*12.9898)*43758.5453))'
    b = f'frac(abs(sin({seed}*39.3467)*24634.6345))'
    c = f'frac(abs(sin({seed}*73.1561)*56445.2341))'
    d = f'frac(abs(sin({seed}*19.1963)*12414.1241))'
    age, norm = 'Particles.Age', 'saturate(Particles.NormalizedAge)'
    angle = f'({b}*6.2831853)'
    if burst:
        # Normal points out of the contact surface, so the mist stays above it.
        direction = f'float3(cos({angle}),sin({angle}),.10+.45*{c})'
        travel = f'User.BurstRadius*(.10+(.65+.35*{a})*(1-exp(-{age}*2.8)))'
        position = f'{direction}*({travel})+float3(0,0,{age}*3)'
        size = f'float2(18,14)*(1+{c}*.7)*(1+{norm})' if mist else f'float2(1,1)*(.55+.9*{c})*(1-.35*{norm})'
        life = f'.65+.45*{a}' if mist else f'.8+.6*{a}'
    else:
        axis = 'normalize(User.ArrowEnd)'
        radial = f'(User.Side*cos({angle})+User.Up*sin({angle}))'
        direction = f'({radial}*(.75+.25*{c})+{axis}*({d}-.5)*.55)'
        travel = f'(1.2+{age}*(3+5*{a}))' if mist else f'(1.8+{age}*(7+12*{a}))'
        # Independent outward drift and a small bounded flutter, never an orbit.
        flutter = f'(User.Side*sin({age}*4.1+{d}*6.28)+User.Up*sin({age}*3.3+{c}*6.28))*{age}*.8'
        position = (f'User.ArrowEnd*{a}+{direction}*{travel}+{flutter}'
                    f'+User.Lift*{age}*' + ('-2.5' if mist else '1.2')
                    + f'+User.Wind*{age}*.35-{axis}*User.Flight*{age}*16')
        size = f'float2(8,11)*(.8+.45*{c})*(1+{norm}*.65)' if mist else f'float2(1,1)*(.32+.62*{c})*(1-.30*{norm})'
        life = f'.55+.40*{b}' if mist else f'.7+.65*{b}'
    opacity = '.25' if mist else '.78'
    tint = '.91,.96,1' if mist else '1,1,1'
    fade = f'saturate({age}/.07)*pow(1-{norm},1.35)'
    common = {
        'Particles.Position': (POSITION, position),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, size), 'Particles.SpriteRotation': (FLOAT, f'{d}*360'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, f'float4({tint},{opacity}*{fade})'),
        'Particles.SubImageIndex': (FLOAT, f'min(62.95,{norm}*56)' if mist else '0'),
    }
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, life), **common})
    assignments(system, name, 'ParticleUpdateScript', common)


def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving cold arrow effects')
    u.EditorAssetLibrary.make_directory(DEST)
    mist, motes = materials()
    source = u.load_asset(SOURCE)
    lifecycle = {key: u.RainAssetEditor.read_input(source, 'RocketTrail', 'EmitterUpdateScript', 'EmitterState', key)
                 for key in ('Life Cycle Mode', 'Loop Behavior')}
    lifecycle['Life Cycle Mode'] = lifecycle['Life Cycle Mode'].replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    for name, burst in [('NS_ArrowColdMist', False), ('NS_ArrowColdBurst', True)]:
        system = owned(name, SOURCE)
        for emitter in emitters(system):
            API.call_method('RemoveEmitter', (ref(system, emitter),))
        for key, typ in [('ArrowEnd', VEC3), ('Side', VEC3), ('Up', VEC3), ('Lift', VEC3), ('Wind', VEC3),
                         ('Flight', FLOAT), ('Detail', FLOAT), ('VariationSeed', FLOAT), ('BurstRadius', FLOAT)]:
            user_parameter(system, key, typ)
        mode = dict(lifecycle)
        if burst:
            mode['Loop Behavior'] = mode['Loop Behavior'].replace('NewEnumerator0', 'NewEnumerator1').replace('"Infinite"', '"Once"')
        layer(system, 'ColdVeil', mist, True, burst, mode)
        layer(system, 'FloatingWhiteMotes', motes, False, burst, mode)
        system.set_editor_property('require_current_frame_data', True)
        system.set_editor_property('fixed_tick_delta', False)
        system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-180, -180, -180), max=u.Vector(180, 180, 180)))
        u.EditorAssetLibrary.set_metadata_tag(system, 'ElementalArrow.ColdMistRevision', '20261109-v2')
        save(system)
    receipt = dict(saved_assets=SAVED, layers=['ColdVeil', 'FloatingWhiteMotes'],
                   arrow_rates=[18, 26], burst_counts=[12, 28], mesh_renderers=False,
                   runtime_tested=False, editor_started=False)
    (OUT / 'saved-assets.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ELEMENTAL_ARROW_COLD_MIST_SAVED ' + json.dumps(receipt))


main()
