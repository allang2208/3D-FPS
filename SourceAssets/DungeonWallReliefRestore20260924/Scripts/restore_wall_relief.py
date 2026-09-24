"""Save a new relief master and reparent only the two live mortar instances.

Also imported by the Fab material producer so later authoring retains relief.
No level loading, geometry changes, gameplay launch, or rendering.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
BASE = '/Game/Dungeons/WallDamage20260923/Materials'
MASTER = BASE + '/M_WallMortarProjectedRelief20260924'
OLD = '/Game/Dungeons/AtmosphereV2/WallRelief/Textures/T_WallMortar_'
SCAN = '/Game/Dungeons/WallDamage20260923/Textures/T_FabExposedConcrete_'
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
CODE = (ROOT / 'Scripts/mortar_projected.ush').read_text(encoding='utf-8')
SIGNATURE = 'Wall mortar projected relief 20260924 ' + hashlib.sha256(CODE.encode()).hexdigest()
RELIEF_INSTANCES = {'MI_FabExposedBed': (.65, 1.0), 'MI_FabBondingMortar': (.065, .10)}
PARAMETERS = {'SurfaceTileCm': 128., 'WallReliefDepthCm': .65,
              'WallNormalStrength': 1., 'WallReliefSteps': 12.,
              'WallReliefRefineSteps': 4., 'WallReliefFadeStartCm': 250.,
              'WallReliefFadeEndCm': 650.}


def require_context():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    ue = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ue and ue.get_game_world():
        raise RuntimeError('PIE active; preserve the running scene')
    owned = {MASTER, *(BASE + '/' + name for name in RELIEF_INSTANCES)}
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if owned & dirty:
        raise RuntimeError('Preserve unsaved wall material edits: ' + str(owned & dirty))
    (ROOT / 'Receipts').mkdir(parents=True, exist_ok=True)


def backup(asset):
    rel = asset.get_path_name().split('.')[0].removeprefix('/Game/') + '.uasset'
    src = PROJECT / 'Content' / rel
    dst = ROOT / 'BeforeV2/Content' / rel
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Failed to save ' + asset.get_path_name())


def ensure_master():
    require_context()
    mat = u.load_asset(MASTER)
    if mat:
        if E.get_metadata_tag(mat, 'WallReliefSource') != SIGNATURE:
            raise RuntimeError('Existing relief graph differs; preserve it and use a new asset revision')
        return mat
    textures = {}
    for pin, path, compression, sampler in [
        ('HeightTex', OLD+'Height', u.TextureCompressionSettings.TC_HALF_FLOAT, u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
        ('ReliefNormal', OLD+'Normal', u.TextureCompressionSettings.TC_NORMALMAP, u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        ('ReliefSurface', OLD+'Surface', u.TextureCompressionSettings.TC_MASKS, u.MaterialSamplerType.SAMPLERTYPE_MASKS),
        ('ReliefColor', OLD+'BaseColor', u.TextureCompressionSettings.TC_DEFAULT, u.MaterialSamplerType.SAMPLERTYPE_COLOR),
    ]:
        tex = u.load_asset(path)
        if not tex or tex.get_editor_property('compression_settings') != compression:
            raise RuntimeError('Missing or changed source texture compression: ' + path)
        if bool(tex.get_editor_property('srgb')) != (pin == 'ReliefColor'):
            raise RuntimeError('Source texture colour space differs: ' + path)
        textures[pin] = (tex, sampler)
    mat = A.create_asset(MASTER.rsplit('/', 1)[-1], BASE, u.Material, u.MaterialFactoryNew())
    mat.set_editor_property('tangent_space_normal', False)
    mat.set_editor_property('used_with_instanced_static_meshes', True)
    mat.set_editor_property('used_with_nanite', True)

    def node(kind, **props):
        n = L.create_material_expression(mat, getattr(u, 'MaterialExpression'+kind))
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    def wire(src, dst, pin='', output=''):
        if not L.connect_material_expressions(src, output, dst, pin):
            raise RuntimeError('Failed connection: ' + pin)

    view = node('Transform', transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                transform_type=u.MaterialVectorCoordTransform.TRANSFORM_INSTANCE)
    wire(node('CameraVectorWS'), view)
    normal = node('Transform', transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                  transform_type=u.MaterialVectorCoordTransform.TRANSFORM_INSTANCE)
    wire(node('VertexNormalWS'), normal)
    world = node('WorldPosition')
    position = node('TransformPosition', transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                    transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    wire(world, position)
    distance = node('Distance')
    wire(world, distance, 'A')
    wire(node('CameraPositionWS'), distance, 'B')
    inputs = {'ViewLocal': view, 'SurfaceNormal': normal, 'Position': position, 'DistanceCm': distance}
    rename = {'WallReliefDepthCm': 'DepthCm', 'WallNormalStrength': 'ReliefStrength',
              'WallReliefSteps': 'Steps', 'WallReliefRefineSteps': 'RefineSteps',
              'WallReliefFadeStartCm': 'FadeStart', 'WallReliefFadeEndCm': 'FadeEnd'}
    for key, value in PARAMETERS.items():
        inputs[rename.get(key, key)] = node('ScalarParameter', parameter_name=key, default_value=value)
    for pin, (tex, sampler) in textures.items():
        inputs[pin] = node('TextureObjectParameter', parameter_name=pin, texture=tex, sampler_type=sampler)
    custom = node('Custom', code=CODE, output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
                  desc='Instance-space mortar POM and coherent height-authored PBR')
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)
    outputs = []
    for name, kind in [('NormalLocal', u.CustomMaterialOutputType.CMOT_FLOAT3), ('AO', u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        out = u.CustomOutput()
        out.set_editor_property('output_name', name)
        out.set_editor_property('output_type', kind)
        outputs.append(out)
    custom.set_editor_property('additional_outputs', outputs)
    for pin, src in inputs.items():
        wire(src, custom, pin)
    color = node('ComponentMask', r=True, g=True, b=True, a=False)
    rough = node('ComponentMask', r=False, g=False, b=False, a=True)
    wire(custom, color)
    wire(custom, rough)
    normal_world = node('Transform', transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,
                        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(custom, normal_world, output='NormalLocal')
    for src, pin, prop in [(color, '', 'BASE_COLOR'), (rough, '', 'ROUGHNESS'),
                           (normal_world, '', 'NORMAL'), (custom, 'AO', 'AMBIENT_OCCLUSION'),
                           (node('Constant', r=0.), '', 'METALLIC'), (node('Constant', r=.27), '', 'SPECULAR')]:
        if not L.connect_material_property(src, pin, getattr(u.MaterialProperty, 'MP_'+prop)):
            raise RuntimeError('Failed material output: ' + prop)
    L.layout_material_expressions(mat)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material graph errors: ' + str(errors))
    # A successful NullRHI recompile is not evidence of a runtime shader compile.
    E.set_metadata_tag(mat, 'WallReliefSource', SIGNATURE)
    save(mat)
    return mat


def configure_instance(mi, master):
    name = mi.get_name()
    if name not in RELIEF_INSTANCES:
        raise RuntimeError('Only exposed bed and bonding mortar use this UV contract')
    import sys
    sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
    import dungeon_wall_release
    if dungeon_wall_release.apply_instance(mi):return
    backup(mi)
    mi.modify()
    L.set_material_instance_parent(mi, master)
    depth, normal = RELIEF_INSTANCES[name]
    for key, value in {'WallReliefDepthCm': depth, 'WallNormalStrength': normal,
                       'WallReliefSteps': 12., 'WallReliefRefineSteps': 4.,
                       'WallReliefFadeStartCm': 250., 'WallReliefFadeEndCm': 650.,
                       'SurfaceTileCm': 128.}.items():
        L.set_material_instance_scalar_parameter_value(mi, key, value)
    L.update_material_instance(mi)
    save(mi)


def install():
    master = ensure_master()
    report = {'stage': 'saving', 'master': MASTER, 'shader_sha256': hashlib.sha256(CODE.encode()).hexdigest(),
              'instances': {}, 'runtime_tested': False, 'geometry_changed': False, 'textures_reimported': False}
    receipt = ROOT / 'Receipts/install-v2.json'
    for name in RELIEF_INSTANCES:
        mi = u.load_asset(BASE+'/'+name)
        if not mi:
            raise RuntimeError('Missing live material instance ' + name)
        previous = mi.get_editor_property('parent').get_path_name()
        configure_instance(mi, master)
        values = {str(p.parameter_info.name): float(p.parameter_value) for p in mi.get_editor_property('scalar_parameter_values')}
        report['instances'][name] = {'previous_parent': previous, 'saved_parent': mi.get_editor_property('parent').get_path_name(),
                                     'saved_parameters': values}
        receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
    report['stage'] = 'materials_saved'
    receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('WALL_RELIEF_RESTORED', json.dumps(report), flush=True)


if __name__ == '__main__':
    install()
