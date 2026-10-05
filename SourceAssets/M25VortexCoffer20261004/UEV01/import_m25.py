"""Produce and save M25 locomotion packages; no gameplay, rendering or acceptance runs."""
from pathlib import Path
import json, math, sys, traceback
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
RIG = ROOT.parent/'RigV01'
DEST = '/Game/Monsters/VortexCofferM25'
REV = 'M25Locomotion20261004V1'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
MEL = u.MaterialEditingLibrary
sys.path.insert(0, str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale

receipt = ROOT/'ue_asset_receipt.json'
report = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {
    'revision': REV, 'saved': [], 'runtime_tested': False, 'rendered': False,
    'source_triangles': 6524740, 'decimated': False
}
def record():
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
def own(asset):
    LIB.set_metadata_tag(asset, 'M25.Revision', REV)
def save(asset):
    own(asset)
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:
        report['saved'].append(asset.get_path_name())
    record()
def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Required asset missing: '+path)
    return asset
def existing(path):
    if not LIB.does_asset_exist(path):
        return None
    asset = load(path)
    if LIB.get_metadata_tag(asset, 'M25.Revision') != REV:
        raise RuntimeError('Preserving unowned asset: '+path)
    return asset
def create(name, cls, factory, folder=DEST):
    asset = existing(folder+'/'+name)
    if asset:
        return asset
    asset = TOOLS.create_asset(name, folder, cls, factory)
    if asset is None:
        raise RuntimeError('Create failed: '+name)
    own(asset)
    return asset
def imp(file, name, folder, options=None):
    asset = existing(folder+'/'+name)
    if asset:
        return asset
    report['operation'] = 'import '+name
    record()
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_name = name
    task.destination_path = folder
    task.automated = True
    task.save = False
    task.replace_existing = False
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(folder+'/'+name)
    if asset is None:
        asset = next((a for p in task.imported_object_paths if isinstance((a:=u.load_asset(p)), u.AnimSequence)), None)
    if asset is None:
        raise RuntimeError('Import did not produce '+name)
    own(asset)
    return asset

def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserving unsaved M25 packages')
    report['stage'] = 'importing'
    report.pop('error', None)
    record()
    textures = {}
    for semantic in ('BaseColor','MetallicRoughness','Normal'):
        tex = imp(RIG/'Textures'/('T_M25_'+semantic+'.jpg'), 'T_M25_'+semantic, DEST+'/Textures')
        tex.set_editor_property('srgb', semantic=='BaseColor')
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal' else u.TextureCompressionSettings.TC_MASKS if semantic=='MetallicRoughness' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('max_texture_size', 2048)
        tex.set_editor_property('never_stream', False)
        if semantic=='Normal':
            tex.set_editor_property('flip_green_channel', True)
        save(tex)
        textures[semantic] = tex

    material = existing(DEST+'/Materials/M_M25_MeshySurface')
    if material is None:
        material = create('M_M25_MeshySurface', u.Material, u.MaterialFactoryNew(), DEST+'/Materials')
        material.set_editor_property('used_with_skeletal_mesh', True)
        material.set_editor_property('two_sided', True)
        material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for index, semantic in enumerate(textures):
            node = MEL.create_material_expression(material, u.MaterialExpressionTextureSample, -450, index*260)
            node.set_editor_property('texture', textures[semantic])
            node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if semantic=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            links = [('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)] if semantic=='MetallicRoughness' else [('RGB',u.MaterialProperty.MP_NORMAL if semantic=='Normal' else u.MaterialProperty.MP_BASE_COLOR)]
            for output, prop in links:
                if not MEL.connect_material_property(node, output, prop):
                    raise RuntimeError('Material connection failed: '+semantic)
        MEL.recompile_material(material)
        save(material)

    cvar = 'Interchange.FeatureFlags.Import.FBX'
    old = u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None, cvar+' 0')
    try:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal = True
        options.import_mesh = True
        options.import_animations = False
        options.import_materials = False
        options.import_textures = False
        options.create_physics_asset = False
        data = options.skeletal_mesh_import_data
        data.set_editor_property('normal_import_method', u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        data.set_editor_property('use_t0_as_ref_pose', False)
        data.set_editor_property('update_skeleton_reference_pose', False)
        mesh = imp(RIG/'SK_M25_VortexCoffer_V01.fbx', 'SK_M25_VortexCoffer', DEST, options)
        skeleton = mesh.get_editor_property('skeleton')
        slots = list(mesh.get_editor_property('materials'))
        for index, slot in enumerate(slots):
            slot.material_interface = material
            slots[index] = slot
        mesh.set_editor_property('materials', slots)
        mesh.set_editor_property('enable_per_poly_collision', False)
        save(skeleton)
        save(mesh)
        clips = {}
        for role, name in [('Idle','A_M25_Idle'),('Move','A_M25_Crawl_InPlace')]:
            op = u.FbxImportUI()
            op.automated_import_should_detect_type = False
            op.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            op.import_as_skeletal = True
            op.import_mesh = False
            op.import_animations = True
            op.import_materials = False
            op.import_textures = False
            op.skeleton = skeleton
            data = op.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate', False)
            data.set_editor_property('custom_sample_rate', 30)
            data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            data.set_editor_property('remove_redundant_keys', False)
            clip = imp(RIG/'Animations'/(name+'.fbx'), name, DEST+'/Animations', op)
            clip.set_editor_property('enable_root_motion', False)
            clip.set_editor_property('force_root_lock', False)
            clip.set_editor_property('rate_scale', 1.)
            clip.set_preview_skeletal_mesh(mesh)
            report.setdefault('root_unit_adaptation', {})[role] = match_bind_root_scale(clip, mesh)
            save(clip)
            clips[role] = clip
        report.update(mesh=mesh.get_path_name(), skeleton=skeleton.get_path_name(),
                      material=material.get_path_name(),
                      animations={k:v.get_path_name() for k,v in clips.items()})
        record()
    finally:
        u.SystemLibrary.execute_console_command(None, cvar+' '+str(old))

    # Fit the imported FBX axes to the character's +X facing.
    op = u.AnimPoseEvaluationOptions()
    op.set_editor_property('optional_skeletal_mesh', mesh)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clips['Idle'], 0., op)
    front = u.AnimPoseExtensions.get_ref_bone_pose(pose, 'body_06', u.AnimPoseSpaces.WORLD).translation
    rear = u.AnimPoseExtensions.get_ref_bone_pose(pose, 'body_00', u.AnimPoseSpaces.WORLD).translation
    yaw = -math.degrees(math.atan2(front.y-rear.y, front.x-rear.x))
    report['mesh_yaw'] = yaw
    if not hasattr(u, 'VortexCofferM25') or not hasattr(u, 'M25AnimInstance'):
        report.update(stage='assets_saved_native_binding_pending', native_rebuild_required=True)
        record()
        u.log('M25_ASSETS_SAVED_NATIVE_BINDING_PENDING')
        return

    factory = u.BlueprintFactory()
    factory.set_editor_property('parent_class', u.MonsterAIController.static_class())
    ai = create('BP_M25AIController', u.Blueprint, factory)
    u.BlueprintEditorLibrary.compile_blueprint(ai)
    u.get_default_object(ai.generated_class()).set_editor_property('behavior', load('/Game/Monsters/AI/BT_Monster'))
    save(ai)

    factory = u.BlueprintFactory()
    factory.set_editor_property('parent_class', u.VortexCofferM25.static_class())
    bp = create('BP_VortexCofferM25', u.Blueprint, factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    for prop, value in [('visual_mesh',mesh),('idle_clip',clips['Idle']),('move_clip',clips['Move']),
                        ('mesh_yaw',yaw),('walk_speed',16.),('animation_walk_speed',16.),
                        ('ai_controller_class',ai.generated_class())]:
        cdo.set_editor_property(prop, value)
    component = cdo.get_editor_property('mesh')
    component.set_skeletal_mesh_asset(mesh)
    component.set_anim_instance_class(u.M25AnimInstance.static_class())
    component.set_editor_property('relative_rotation', u.Rotator(pitch=0., yaw=yaw, roll=0.))
    component.set_editor_property('relative_location', u.Vector(0.,0.,-225.))
    component.set_editor_property('override_materials', [material])
    save(bp)
    if hasattr(u, 'PoisonMaggotMonster'):
        if not u.PoisonMaggotMonster.compile_material_assets([material]):
            raise RuntimeError('M25 material compilation failed')
    save(material)
    report.update(stage='assets_saved', native_rebuild_required=False, blueprint=bp.get_path_name(),
                  ai_controller=ai.get_path_name(), f6_id='VortexCofferM25', f6_name='涡电匣 M-25',
                  walk_speed_cm_s=16., blend_seconds=.25, root_motion=False,
                  combat_scope='locomotion only; damage disabled; no attack/death/VFX')
    record()
    u.log('M25_LOCOMOTION_ASSETS_SAVED '+DEST)

try:
    main()
except Exception:
    report['stage'] = 'production_failed'
    report['error'] = traceback.format_exc()
    record()
    raise
