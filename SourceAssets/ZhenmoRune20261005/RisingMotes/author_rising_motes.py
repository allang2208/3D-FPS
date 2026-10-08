"""Author and save the Bagua field's rising gold motes; no playback or preview."""
from pathlib import Path
import json
import sys
import unreal as u

OUT = Path(__file__).resolve().parent
PROJECT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(PROJECT / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, POSITION, COLOR
from build_fireball_flight import user_parameter

DEST = '/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles'
TEMPLATE = '/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SAVED = []
HL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
ENUM = '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum'


def own(name, cls, factory):
    path = DEST + '/' + name
    asset = u.load_asset(path) if E.does_asset_exist(path) else TOOLS.create_asset(name, DEST, cls, factory)
    if not asset:
        raise RuntimeError('Cannot create ' + path)
    return asset


def save(asset):
    if isinstance(asset, u.Material):
        errors = L.recompile_material(asset)
        if errors:
            raise RuntimeError('Mote material compilation: ' + str(errors))
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Mote Niagara compilation failed')
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    u.log('ZHENMO_MOTES_SAVED ' + asset.get_path_name())


def material():
    m = own('M_ZhenmoGoldMote', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    L.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)

    def node(cls, **props):
        n = L.create_material_expression(m, cls)
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    def link(src, output, dst, pin):
        if not L.connect_material_expressions(src, output, dst, pin):
            raise RuntimeError('Mote material connection failed: ' + pin)

    uv = node(u.MaterialExpressionTextureCoordinate)
    color = node(u.MaterialExpressionParticleColor)
    depth = node(u.MaterialExpressionPixelDepth)
    pins = []
    for name in ('UV', 'Alpha', 'Depth'):
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
    mask = node(u.MaterialExpressionCustom,
                output_type=u.CustomMaterialOutputType.CMOT_FLOAT1, inputs=pins,
                code='''float2 p=(UV-.5)*2;
float r2=dot(p,p);
float glow=.72*exp(-r2*15)+.28*exp(-r2*4);
float edge=1-smoothstep(.55,1,sqrt(r2));
return glow*edge*Alpha*smoothstep(40,100,Depth);''')
    link(uv, '', mask, 'UV')
    link(color, 'A', mask, 'Alpha')
    link(depth, '', mask, 'Depth')
    fade = node(u.MaterialExpressionDepthFade, fade_distance_default=10.)
    link(mask, '', fade, 'Opacity')
    intensity = node(u.MaterialExpressionConstant, r=4.5)
    emissive = node(u.MaterialExpressionMultiply)
    link(color, 'RGB', emissive, 'A')
    link(intensity, '', emissive, 'B')
    exposed = node(u.MaterialExpressionEyeAdaptationInverse)
    link(emissive, '', exposed, str(L.get_material_expression_input_names(exposed)[0]))
    L.connect_material_property(exposed, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    surface = node(u.MaterialExpressionSubstrateShadingModels,
                   shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
    link(exposed, '', surface, 'Emissive Color')
    link(fade, '', surface, 'Opacity')
    if not L.connect_material_property(surface, '', u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Mote Substrate output not connected')
    E.set_metadata_tag(m, 'Source', 'Original analytic soft gold mote; no bitmap or external artwork')
    save(m)
    return m


def particles(m):
    s = own('NS_ZhenmoRisingGold', u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    en = 'BaguaRisingGold'
    for old in emitters(s):
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            E.remove_metadata_tag(s, 'Fireball.Assignments.' + old + '.' + stage)
        API.call_method('RemoveEmitter', (ref(s, old),))
    emitter = u.load_asset(TEMPLATE)
    if not emitter:
        raise RuntimeError('Missing project Epic Niagara template: ' + TEMPLATE)
    API.call_method('AddEmitter', (s, emitter, en))
    trim(s, en, {'EmitterUpdateScript': ['EmitterState'],
                 'ParticleSpawnScript': ['InitializeParticle'],
                 'ParticleUpdateScript': ['ParticleState']})
    API.call_method('AddModule', (ref(s, en, 'EmitterUpdateScript'),
                                 u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    variables = str(API.call_method('GetUserVariables', (s,)).export_text())
    for key in ('Radius', 'FieldOpacity', 'SlopeX', 'SlopeY'):
        if 'User.' + key not in variables:
            user_parameter(s, key, FLOAT)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(s, en),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    mode = str(u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode'))
    loop = str(u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior'))
    mode = mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"')
    loop = loop.replace('NewEnumerator1', 'NewEnumerator0').replace('"Once"', '"Infinite"')
    put(s, en, 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode', mode, ENUM)
    put(s, en, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior', loop, ENUM)
    put(s, en, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        '(HlslExpression="80.0*saturate(User.FieldOpacity)")', HL)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(s, en, renderer=0), {
        'Material': m.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'PivotInUVSpace': {'X': .5, 'Y': .5}, 'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera',
        'bCastShadows': False, 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0, 'MaxCameraDistance': 6500})

    # Independent low-discrepancy sequences avoid concentric lanes and radial clumps.
    seed = 'frac(float(Particles.UniqueID)*.61803398875+.137)'
    angle_seed = 'frac(float(Particles.UniqueID)*.41421356237+.273)'
    other = 'frac(float(Particles.UniqueID)*.75487766623+.413)'
    a, n = 'Particles.Age', 'Particles.NormalizedAge'
    angle = f'({angle_seed}*6.2831853+.012*sin({a}*1.2+{other}*6.2831853))'
    inner_radius = f'(min(460,max(0,User.Radius)*.31)*sqrt(saturate({seed}/.7)))'
    outer_radius = f'(max(0,User.Radius)*(.34+.64*sqrt(saturate(({seed}-.7)/.3))))'
    radius = f'lerp({inner_radius},{outer_radius},step(.7,{seed}))'
    speed = f'(32+20*{other})'
    width = f'(5+4*{other})'
    tall = f'(1+.9*step(.82,{seed}))'
    # Niagara's CPU VM has no smoothstep intrinsic; use the equivalent polynomial.
    edge_t = f'saturate(({radius}/max(1,User.Radius)-.86)/.135)'
    edge = f'(1-({edge_t})*({edge_t})*(3-2*({edge_t})))'
    alpha = f'(.78*saturate({n}*7)*saturate((1-{n})*3)*saturate(User.FieldOpacity)*{edge})'
    shimmer = f'(.84+.16*sin({a}*3+{seed}*6.2831853))'
    common = {
        'Particles.Position': (POSITION, f'float3(cos({angle})*{radius},sin({angle})*{radius},24+{a}*{speed}+User.SlopeX*cos({angle})*{radius}+User.SlopeY*sin({angle})*{radius})'),
        'Particles.SpriteSize': (VEC2, f'{width}*float2(1,{tall})'),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.Color': (COLOR, f'float4(1,.56+.1*{other},.09, {alpha}*{shimmer})')}
    assignments(s, en, 'ParticleSpawnScript',
                {'Particles.Lifetime': (FLOAT, f'2.6+1.2*{other}'), **common})
    assignments(s, en, 'ParticleUpdateScript', common)
    s.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1520, -1520, -1900),
                                               max=u.Vector(1520, 1520, 2100)))
    E.set_metadata_tag(s, 'Zhenmo.Source', TEMPLATE + '; module skeleton only; original motion and material')
    E.set_metadata_tag(s, 'Zhenmo.Lifecycle', 'Owner field controls activation; crit refresh does not restart; fade final .5 seconds')
    E.set_metadata_tag(s, 'Zhenmo.Budget', '1 CPU sprite emitter, 80/s, lifetime <=3.8s, about 304 live motes; no lights, collision or actor per particle')
    E.set_metadata_tag(s, 'Zhenmo.Visibility', 'GroundVisibility20261007; 70% within 4.6m, 30% outer field; cached ground slope')
    save(s)


def build():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Exit PIE before authoring Zhenmo motes')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if str(package.get_name()).startswith(DEST + '/'):
            raise RuntimeError('Preserve unsaved target: ' + package.get_name())
    particles(material())
    (OUT / 'asset_receipt.json').write_text(json.dumps({
        'complete': True, 'saved_assets': SAVED, 'radius_cm': 1500,
        'rise_cm_per_s': [32, 52], 'lifetime_s': [2.6, 3.8], 'spawn_per_s': 80,
        'inner_distribution_fraction': .7, 'inner_radius_cm': 460,
        'local_space_follows_field': True, 'critical_refresh_restarts_particles': False,
        'runtime_tested': False, 'editor_launched': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ZHENMO_RISING_MOTES_ASSETS_SAVED ' + json.dumps(SAVED), flush=True)


if __name__ == '__main__':
    build()
