"""Import this monster's existing delivery, author its PBR surface, and save assets.
No map edits, actor spawning, renders, PIE, or runtime tests.
"""
from pathlib import Path
import json, sys, math
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCE = ROOT / 'DeliveryV1'
DEST = '/Game/Monsters/HundredEyedSlag/V1'
REV = 'HundredEyedSlagLocalRig20260930V1'
RECEIPT = ROOT / 'ue_installation.json'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
MEL = u.MaterialEditingLibrary
sys.path.insert(0, str(PROJECT / 'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale

report = json.loads(RECEIPT.read_text(encoding='utf-8-sig')) if RECEIPT.exists() else {
    'stage': 'importing', 'revision': REV, 'saved': [], 'animations': {},
    'runtime_tested': False, 'preview_rendered': False, 'native_class_built': False}

def record():
    RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

def save(asset):
    LIB.set_metadata_tag(asset, 'HundredEyedSlag.Revision', REV)
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    if asset.get_path_name() not in report['saved']:
        report['saved'].append(asset.get_path_name())
    record()

def owned(path):
    asset = u.load_asset(path)
    if asset and LIB.get_metadata_tag(asset, 'HundredEyedSlag.Revision') != REV:
        raise RuntimeError('Preserving independently owned asset ' + path)
    return asset

def imp(file, name, folder=DEST, options=None):
    asset = owned(folder + '/' + name)
    if asset and asset.get_path_name() in report['saved']:
        return asset
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_name = name
    task.destination_path = folder
    task.automated = True
    task.replace_existing = False
    task.save = False
    if options: task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(folder + '/' + name)
    if not asset:
        raise RuntimeError('Import produced no asset: ' + str(file))
    LIB.set_metadata_tag(asset, 'HundredEyedSlag.Revision', REV)
    return asset

if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Preserving active PIE: import in a background commandlet after the editor closes')
if any(p.get_name().casefold().startswith(DEST.casefold())
       for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved HundredEyedSlag packages')
record()

textures = {}
for semantic in ('BaseColor', 'Metallic', 'Roughness', 'Normal'):
    name = 'T_HundredEyedSlag_' + semantic
    tex = imp(SOURCE / 'Textures' / (name + '.png'), name, DEST + '/Textures')
    tex.set_editor_property('srgb', semantic == 'BaseColor')
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP
        if semantic == 'Normal' else u.TextureCompressionSettings.TC_MASKS
        if semantic in ('Metallic', 'Roughness') else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('never_stream', False)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP
        if semantic == 'Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if semantic == 'Normal': tex.set_editor_property('flip_green_channel', True)
    save(tex)
    textures[semantic] = tex

material = owned(DEST + '/Materials/M_HundredEyedSlag_Skin')
if not material:
    material = TOOLS.create_asset('M_HundredEyedSlag_Skin', DEST + '/Materials',
                                  u.Material, u.MaterialFactoryNew())
existing_expressions=list(MEL.get_material_expressions(material))
material.set_editor_property('used_with_skeletal_mesh', True)
surface = next((n for n in existing_expressions if isinstance(n,u.MaterialExpressionSubstrateShadingModels)),None)
if surface is None:surface = MEL.create_material_expression(material, u.MaterialExpressionSubstrateShadingModels)
surface.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
for i, (semantic, pin, output, prop) in enumerate((('BaseColor', 'BaseColor', 'RGB', u.MaterialProperty.MP_BASE_COLOR),
        ('Metallic', 'Metallic', 'R', u.MaterialProperty.MP_METALLIC), ('Roughness', 'Roughness', 'R', u.MaterialProperty.MP_ROUGHNESS), ('Normal', 'Normal', 'RGB', u.MaterialProperty.MP_NORMAL))):
    node = next((n for n in existing_expressions if isinstance(n,u.MaterialExpressionTextureSample)
        and n.get_editor_property('texture')==textures[semantic]),None)
    if node is None:node = MEL.create_material_expression(material, u.MaterialExpressionTextureSample, -500, i * 200)
    node.texture = textures[semantic]
    node.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic == 'Normal' else (
        u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic == 'BaseColor'
        else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if not MEL.connect_material_expressions(node, output, surface, pin):
        raise RuntimeError('Could not connect PBR ' + semantic)
    if not MEL.connect_material_property(node, output, prop):
        raise RuntimeError('Could not connect PBR material output ' + semantic)
if not MEL.connect_material_property(surface, '', u.MaterialProperty.MP_FRONT_MATERIAL):
    raise RuntimeError('Could not connect Substrate surface')
MEL.recompile_material(material)
if not u.PoisonMaggotMonster.compile_material_assets([material]):
    raise RuntimeError('Native material compilation failed')
save(material)

cvar = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None, cvar + ' 0')
try:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = True
    data = options.skeletal_mesh_import_data
    data.set_editor_property('normal_import_method', u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('use_t0_as_ref_pose', False)
    data.set_editor_property('update_skeleton_reference_pose', False)
    mesh = imp(SOURCE / 'SK_HundredEyedSlag_V1.fbx', 'SK_HundredEyedSlag_V1', options=options)
    skeleton = mesh.get_editor_property('skeleton')
    physics = mesh.get_editor_property('physics_asset')
    if not physics: raise RuntimeError('Physics asset was not created')
    slots = list(mesh.get_editor_property('materials'))
    for i, slot in enumerate(slots):
        slot.material_interface = material
        slots[i] = slot
    mesh.set_editor_property('materials', slots)
    mesh.set_editor_property('enable_per_poly_collision', False)
    save(skeleton); save(physics); save(mesh)
    report.update(mesh=mesh.get_path_name(), skeleton=skeleton.get_path_name(),
                  physics=physics.get_path_name(), geometry_reduced=False)
    record()
    contract = json.loads((SOURCE / 'animation_contract.json').read_text(encoding='utf-8'))
    for row in contract['actions']:
        name = row['action']
        if name in report['animations']: continue
        op = u.FbxImportUI()
        op.automated_import_should_detect_type = False
        op.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal = True
        op.import_mesh = False
        op.import_animations = True
        op.import_materials = False
        op.import_textures = False
        op.skeleton = skeleton
        op.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        op.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
        clip = imp(SOURCE / row['file'], name, DEST + '/Animations', op)
        units = match_bind_root_scale(clip, mesh)
        clip.set_editor_property('enable_root_motion', row['name'] == 'SpecialCharge_RM')
        clip.set_preview_skeletal_mesh(mesh)
        save(clip)
        report['animations'][name] = {'asset': clip.get_path_name(), 'root_units': units}
        record()
    idle = u.load_asset(DEST + '/Animations/A_HundredEyedSlag_Idle')
    pose_options = u.AnimPoseEvaluationOptions()
    pose_options.evaluation_type = u.AnimDataEvalType.SOURCE
    pose_options.optional_skeletal_mesh = mesh
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(idle, 0., pose_options)
    # Derive component-facing from the imported rest convention, without spawning an actor.
    a = u.AnimPoseExtensions.get_ref_bone_pose(pose, 'chest', u.AnimPoseSpaces.WORLD).translation
    b = u.AnimPoseExtensions.get_ref_bone_pose(pose, 'pelvis', u.AnimPoseSpaces.WORLD).translation
    report['mesh_yaw_degrees'] = -math.degrees(math.atan2(a.y - b.y, a.x - b.x))
    report['stage'] = 'model_pbr_physics_and_16_animations_saved'
    record()
    u.log('HUNDRED_EYED_SLAG_ASSETS_SAVED ' + json.dumps({
        'mesh': report['mesh'], 'animations': len(report['animations']),
        'mesh_yaw_degrees': report['mesh_yaw_degrees'], 'runtime_tested': False}))
finally:
    u.SystemLibrary.execute_console_command(None, cvar + ' ' + str(previous))
