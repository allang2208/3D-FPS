"""Thunder Lance ray FX — M09 gaze recipe recolored to electric blue.

Imports the crossed-ribbon and iris meshes under the skill folder, authors
beam/filament/iris materials from SourceAssets HLSL, and clones the M09 eye
gather Niagara stack retuned for a staff-tip charge. Safe to re-run: owned
assets are rebuilt in place with snapshot deletion; unowned assets are
preserved.
"""
import json, sys
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/ThunderLanceRay20261005'
RECORDS = ROOT / 'Records'
RECORDS.mkdir(parents=True, exist_ok=True)
DEST = '/Game/Skills/ElectricMagic/LanceRay'
GATHER_SOURCE = '/Game/Monsters/HangingBellM09/V10/NS_M09_EyeGather_V10'

sys.path.insert(0, str(PROJECT / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, setdata, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import expression

L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
T = u.AssetToolsHelpers.get_asset_tools()

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End related PIE before saving lance ray assets')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
saved = []

def own(name, source=None):
    path = DEST + '/' + name
    if path in dirty:
        raise RuntimeError('Preserve unsaved lance ray target ' + path)
    if E.does_asset_exist(path):
        a = u.load_asset(path)
        if E.get_metadata_tag(a, 'LanceRayProduction') != 'ThunderLanceRayV1':
            raise RuntimeError('Preserve unowned target ' + path)
    else:
        folder, _, leaf = name.rpartition('/')
        a = E.duplicate_asset(source, path) if source else T.create_asset(leaf, DEST + '/' + folder, u.Material, u.MaterialFactoryNew())
    if not a:
        raise RuntimeError('Asset authoring failed ' + path)
    E.set_metadata_tag(a, 'LanceRayProduction', 'ThunderLanceRayV1')
    return a

def save(a):
    if isinstance(a, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(a):
        raise RuntimeError('Niagara compile failed ' + a.get_path_name())
    if not E.save_loaded_asset(a, False):
        raise RuntimeError('Save failed ' + a.get_path_name())
    saved.append(a.get_path_name())
    print('LANCE_RAY_SAVED ' + a.get_path_name(), flush=True)
    (RECORDS / 'import_saved.json').write_text(json.dumps({'complete': False, 'saved': saved, 'tested': False}, indent=2), encoding='utf8')

def imp(file, name, options=None, factory=None):
    path = DEST + '/FX/' + name
    if E.does_asset_exist(path):
        a = u.load_asset(path)
        if E.get_metadata_tag(a, 'LanceRayProduction') != 'ThunderLanceRayV1':
            raise RuntimeError('Preserve unowned target ' + path)
        return a
    task = u.AssetImportTask()
    task.filename = str(file); task.destination_path = DEST + '/FX'; task.destination_name = name
    task.automated = True; task.save = False; task.replace_existing = False
    if options: task.options = options
    if factory: task.factory = factory
    T.import_asset_tasks([task])
    result = u.load_asset(path)
    if not result:
        raise RuntimeError('Import failed ' + path)
    E.set_metadata_tag(result, 'LanceRayProduction', 'ThunderLanceRayV1')
    return result

def beam_material(name, hlsl, instanced, depth):
    mat = own('Materials/' + name)
    # Snapshot deletion: bulk delete_all_material_expressions leaves stranded
    # Custom nodes behind (UE 5.8 iteration bug).
    for old in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat, old)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    if instanced:
        L.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    def node(cls, **props):
        n = L.create_material_expression(mat, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n
    def wire(a, b, pin):
        if isinstance(pin, int):
            pin = str(L.get_material_expression_input_names(b)[pin])
        if not L.connect_material_expressions(a, '', b, pin):
            raise RuntimeError('Material connection failed ' + str(pin))
    inputs = {
        'UV': node(u.MaterialExpressionTextureCoordinate),
        'Strength': node(u.MaterialExpressionScalarParameter, parameter_name='Strength', default_value=0.),
        'Clock': node(u.MaterialExpressionScalarParameter, parameter_name='Clock', default_value=0.),
        'FirePower': node(u.MaterialExpressionScalarParameter, parameter_name='FirePower', default_value=0.),
        'Exposure': node(u.MaterialExpressionEyeAdaptation),
    }
    if instanced:
        data = node(u.MaterialExpressionPerInstanceCustomData, data_index=0, const_default_value=1.)
        interp = node(u.MaterialExpressionVertexInterpolator)
        wire(data, interp, 0)
        inputs['InstanceAlpha'] = interp
    custom = node(u.MaterialExpressionCustom, description='ThunderLanceRay ' + name,
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
                  code=(ROOT / 'Authoring' / (hlsl + '.hlsl')).read_text(encoding='utf8'))
    pins = []
    for key in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', key); pins.append(p)
    custom.set_editor_property('inputs', pins)
    for key, source in inputs.items():
        wire(source, custom, key)
    rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(custom, rgb, 0); wire(custom, alpha, 0)
    fade = node(u.MaterialExpressionDepthFade, fade_distance_default=depth)
    wire(alpha, fade, 0)
    L.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed ' + str(errors))
    save(mat)
    return mat

def particle_material(name, streak):
    m = own('Materials/' + name)
    for old in list(L.get_material_expressions(m)):
        L.delete_material_expression(m, old)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    L.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    def node(cls, **props):
        n = L.create_material_expression(m, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n
    def wire(a, b, pin, out=''):
        if isinstance(pin, int):
            pin = str(L.get_material_expression_input_names(b)[pin])
        if not L.connect_material_expressions(a, out, b, pin):
            raise RuntimeError('Material connection failed ' + str(pin))
    uv = node(u.MaterialExpressionTextureCoordinate)
    code = ('float2 p=UV*2-1;return exp(-p.x*p.x*10)*pow(saturate(1-abs(p.y)),1.5)*smoothstep(1.,.7,abs(p.x));' if streak
            else 'float r=length(UV*2-1);return exp(-r*r*5.5)*(1-smoothstep(.55,1.,r));')
    mask = node(u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    pin = u.CustomInput(); pin.set_editor_property('input_name', 'UV')
    mask.set_editor_property('inputs', [pin])
    wire(uv, mask, 'UV')
    color = node(u.MaterialExpressionParticleColor)
    gain = node(u.MaterialExpressionConstant, r=8.4 if streak else 10.5)
    light = node(u.MaterialExpressionMultiply); wire(color, light, 'A', 'RGB'); wire(gain, light, 'B')
    exposure = node(u.MaterialExpressionEyeAdaptationInverse); wire(light, exposure, 0)
    L.connect_material_property(exposure, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    alpha = node(u.MaterialExpressionMultiply); wire(mask, alpha, 'A'); wire(color, alpha, 'B', 'A')
    fade = node(u.MaterialExpressionDepthFade, fade_distance_default=1.5); wire(alpha, fade, 'Opacity')
    L.connect_material_property(fade, '', u.MaterialProperty.MP_OPACITY)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compilation failed ' + str(errors))
    save(m)
    return m

# ── Meshes (same authored geometry as the M09 gaze, provenance kept) ──
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal = False; opt.import_mesh = True; opt.import_animations = False
opt.import_materials = False; opt.import_textures = False
geo = opt.static_mesh_import_data
geo.convert_scene = True; geo.convert_scene_unit = True; geo.import_uniform_scale = 1.
geo.set_editor_property('auto_generate_collision', False)
geo.set_editor_property('combine_meshes', True)
geo.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS

beam = beam_material('M_ThunderLanceBeam', 'LanceBeam', False, 15.)
# M_ThunderLanceFilament retired 2026-10-06: beam coils use real arc actors;
# source/asset archived under trash/thunder-lance-flux-retired-20261006.
iris = beam_material('M_ThunderLanceIris', 'LanceIris', True, .35)
speck = particle_material('M_ThunderLanceGatherSpeck', False)
streak = particle_material('M_ThunderLanceGatherStreak', True)

ribbon = imp(ROOT / 'SM_ThunderLanceRibbon.fbx', 'SM_ThunderLanceRibbon', opt, u.FbxFactory())
ribbon.set_material(0, beam); save(ribbon)
veil = imp(ROOT / 'SM_ThunderLanceIris.fbx', 'SM_ThunderLanceIris', opt, u.FbxFactory())
veil.set_material(0, iris); save(veil)

# ── Gather Niagara: M09's inward-collapse stack retuned to lightning blue ──
system = own('NS_ThunderLanceGather', GATHER_SOURCE)
keep = ('GatheringSparks', 'ChargingFilaments', 'GatheringRings')
for name in emitters(system):
    if name not in keep:
        API.call_method('RemoveEmitter', (ref(system, name),))
# rate, lifetime, start radius, streak length, streak width, material — the
# gather envelope is larger than M09's eyes; the component scale stays near 1.
recipes = [('GatheringSparks', 88, .42, 62, 4.0, 3.5, speck),
           ('ChargingFilaments', 25, .28, 48, 17., 2.4, streak),
           ('GatheringRings', 38, .34, 38, 2.4, 2.4, speck)]
for name, rate, life, start_radius, length, width, mat in recipes:
    trim(system, name, {'EmitterUpdateScript': ['EmitterState', 'SpawnRate'],
                        'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        E.remove_metadata_tag(system, 'Fireball.Assignments.' + name + '.' + stage)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'Alignment': 'VelocityAligned' if name == 'ChargingFilaments' else 'Unaligned',
        'FacingMode': 'FaceCamera', 'SortMode': 'ViewDepth', 'bCastShadows': False, 'MotionVectorSetting': 'Disable',
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'SubImageSize': {'X': 1, 'Y': 1}})
    expression(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
               f'{rate}*(.32+.68*saturate(User.Charge))')
    seed = 'frac(float(Particles.UniqueID)*.618033989)'
    age = 'saturate(Particles.NormalizedAge)'
    charge = 'saturate(User.Charge)'
    theta = f'({seed}*6.2831853+Particles.Age*(5+{charge}*5))'
    collapse = f'(1-.96*pow(saturate(({charge}-.82)/.18),2))'
    radius = f'(.4+({start_radius}-.4)*(1-pow({age},1.65))*{collapse})'
    position = f'float3(1+10*(1-{age})*{collapse},cos({theta})*{radius},sin({theta})*{radius})'
    velocity = f'float3(-.2,-cos({theta})-.55*sin({theta}),-sin({theta})+.55*cos({theta}))*100'
    size = f'float2({width},{length})*(.7+.35*{charge})*(1-.35*{age})'
    alpha = f'(.40+.56*{charge})*saturate({age}*10)*saturate((1-{age})*7)'
    color = f'float4(.30+.16*{seed},.58+.20*{seed},1.,{alpha})'
    values = {'Particles.Lifetime': (FLOAT, str(life)), 'Particles.Position': (POSITION, position),
              'Particles.Velocity': (VEC3, velocity), 'Particles.SpriteSize': (VEC2, size),
              'Particles.Color': (COLOR, color), 'Particles.SpriteRotation': (FLOAT, '0'),
              'Particles.SubImageIndex': (FLOAT, '0')}
    assignments(system, name, 'ParticleSpawnScript', values)
    assignments(system, name, 'ParticleUpdateScript', {k: v for k, v in values.items() if k != 'Particles.Lifetime'})
system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-14, -80, -80), max=u.Vector(26, 80, 80)))
E.set_metadata_tag(system, 'LanceRaySourceSystem', GATHER_SOURCE)
E.set_metadata_tag(system, 'LanceRayMotion', 'Inward specks, curved streaks and dust; collapse into the cast point before release')
save(system)

receipt = {'complete': True, 'saved': saved, 'source_system': GATHER_SOURCE,
           'source_meshes': 'M09 GazeV08 FBX geometry reused (crossed ribbons + iris veil)',
           'emitters': [{'name': x[0], 'max_spawn_rate': x[1], 'lifetime': x[2], 'start_radius_cm': x[3]} for x in recipes],
           'provenance': 'M09 Gaze beam/filament/iris HLSL recolored electric blue; gather stack retuned',
           'tested': False, 'preview_rendered': False}
(RECORDS / 'import_saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
print('LANCE_RAY_COMPLETE assets=' + str(len(saved)))
