"""Author/save M27's native jelly material; optionally connect after native build.

Commandlet or shared editor bridge. No game, map, preview or acceptance run.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/CloakV1')
DEST = '/Game/Monsters/MantisM27/CloakV1/Materials'
PATH = DEST + '/M_M27_JellyCloak'
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
REPORT = {'revision': 'CloakV1', 'material_saved': False, 'blueprint_connected': False,
          'tested': False, 'visual_tested': False, 'runtime_tested': False}

def receipt():
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'ue_cloak_receipt.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')

def node(m, cls):
    return L.create_material_expression(m, cls)

def wire(source, target, pin):
    n, output = source if isinstance(source, tuple) else (source, '')
    if not L.connect_material_expressions(n, output, target, pin):
        raise RuntimeError('Cannot connect ' + pin)

def output(m, n, name):
    if not L.connect_material_property(n, '', getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Cannot connect material output ' + name)

def custom(m, code, inputs, width=1):
    n = node(m, u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('description', 'M27 CloakV1')
    n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
    n.set_editor_property('inputs', pins)
    for name, value in inputs.items():
        wire(value, n, name)
    return n

def scalar(m, name, value):
    n = node(m, u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', value)
    return n

def texture(m, name, sampler):
    n = node(m, u.MaterialExpressionTextureSample)
    tex = u.load_asset('/Game/Monsters/MantisM27/ProductionV1/Textures/T_M27_' + name)
    if not tex:
        raise RuntimeError('Missing original M27 texture ' + name)
    n.set_editor_property('texture', tex)
    n.set_editor_property('sampler_type', sampler)
    return n

def material():
    E.make_directory(DEST)
    m = u.load_asset(PATH) or u.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_M27_JellyCloak', DEST, u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('disable_depth_test', False)
    m.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    m.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    m.set_editor_property('refraction_method', u.RefractionMode.RM_INDEX_OF_REFRACTION)
    L.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    amount = scalar(m, 'CloakAmount', 1.)
    center = scalar(m, 'CenterOpacity', .025)
    rim_opacity = scalar(m, 'RimOpacity', .16)
    ior = scalar(m, 'JellyIOR', 1.025)
    shimmer = scalar(m, 'ShimmerNormalStrength', .028)
    p = node(m, u.MaterialExpressionLocalPosition)
    p.set_editor_property('included_offsets', u.PositionIncludedOffsets.EXCLUDE_OFFSETS)
    time = node(m, u.MaterialExpressionTime)
    original = texture(m, 'BaseColor', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal_map = texture(m, 'Normal', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm = texture(m, 'MetallicRoughness', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal = custom(m, '''float2 ripple=float2(sin(P.z*.075+P.x*.045+T*1.7),cos(P.y*.055-P.z*.04-T*1.3));
return normalize(float3(N.xy*lerp(1.,.22,A)+ripple*S*A,lerp(N.z,1.,A)));''',
                    {'P': p, 'T': time, 'N': (normal_map, 'RGB'), 'A': amount, 'S': shimmer}, 3)
    fresnel = node(m, u.MaterialExpressionFresnel)
    fresnel.set_editor_property('exponent', 3.)
    fresnel.set_editor_property('base_reflect_fraction', .015)
    inputs = {
        'BASE_COLOR': ('BaseColor', custom(m, 'return lerp(C,float3(.11,.19,.21),A);', {'C': (original, 'RGB'), 'A': amount}, 3)),
        'METALLIC': ('Metallic', custom(m, 'return M*(1-A);', {'M': (orm, 'B'), 'A': amount})),
        'ROUGHNESS': ('Roughness', custom(m, 'return lerp(R,.12,A);', {'R': (orm, 'G'), 'A': amount})),
        'SPECULAR': ('Specular', scalar(m, 'JellySpecular', .5)),
        'NORMAL': ('Normal', normal),
        'OPACITY': ('Opacity', custom(m, 'return lerp(1.,saturate(C+F*R),A);', {'A': amount, 'C': center, 'R': rim_opacity, 'F': fresnel})),
    }
    slab = node(m, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for name, (pin, value) in inputs.items():
        output(m, value, name)
        wire(value, slab, pin)
    output(m, slab, 'FRONT_MATERIAL')
    output(m, custom(m, 'return lerp(1.,IOR,A);', {'IOR': ior, 'A': amount}), 'REFRACTION')
    E.set_metadata_tag(m, 'M27.Source', 'Original native UE graph; GitHub examples reviewed as conceptual references only; no third-party code/assets copied.')
    E.set_metadata_tag(m, 'M27.Shadow', 'Runtime hidden opaque skeletal follower; translucent visible mesh does not own the shadow.')
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError(str(errors))
    if not u.PoisonMaggotMonster.compile_material_assets([m]):
        raise RuntimeError('Material compilation failed')
    if not E.save_loaded_asset(m, False):
        raise RuntimeError('Material save failed')
    REPORT.update(material_saved=True, material=m.get_path_name())
    receipt()
    return m

def connect(m):
    bp = u.load_asset(BP)
    defaults = u.get_default_object(bp.generated_class())
    defaults.set_editor_property('cloak_material', m)
    for name, value in {'cloak_heal_fraction_per_second': .05, 'cloak_injury_threshold': .5,
                        'cloak_recovery_threshold': .8, 'cloak_minimum_seconds': 3.,
                        'cloak_fade_seconds': .45, 'cloak_orbit_radius': 700., 'cloak_move_speed': 190.}.items():
        defaults.set_editor_property(name, value)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not E.save_loaded_asset(bp, False):
        raise RuntimeError('M27 blueprint save failed')
    REPORT.update(blueprint_connected=True, blueprint=BP)
    receipt()

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Preserve active PIE; author after play stops')
        dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if dirty.intersection({PATH, BP}):
            raise RuntimeError('Preserve unsaved M27 target packages')
    connect_only = '-m27connectcloak' in u.SystemLibrary.get_command_line().lower()
    if connect_only:
        REPORT.update(json.loads((ROOT / 'ue_cloak_receipt.json').read_text(encoding='utf-8')))
        saved_material = u.load_asset(PATH)
        if not saved_material:
            raise RuntimeError('Cloak material has not been saved')
        if not u.PoisonMaggotMonster.compile_material_assets([saved_material]):
            raise RuntimeError('Cloak material compilation failed')
        if not E.save_loaded_asset(saved_material, False):
            raise RuntimeError('Cannot save compiled cloak material')
        connect(saved_material)
    else:
        material()
    u.log('M27_CLOAK_SAVED ' + json.dumps(REPORT))
except Exception as exc:
    REPORT['error'] = str(exc)
    receipt()
    raise
