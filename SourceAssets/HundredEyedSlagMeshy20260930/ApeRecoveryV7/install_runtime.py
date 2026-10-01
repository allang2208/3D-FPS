"""Save arclength skin and the two heavy long-arm attacks at current runtime paths."""
import json, shutil, sys
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
BASE = '/Game/Monsters/HundredEyedSlag'
REV = 'HundredEyedSlagApeRecoveryV7_20261001'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EDITOR = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
SKELETON_PATH = BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton'
MESH_PATHS = [BASE+'/PolishV2/SK_HundredEyedSlag_V2', BASE+'/V1/SK_HundredEyedSlag_V1']
PHYSICS_PATHS = [BASE+'/PolishV2/PA_HundredEyedSlag_V2', BASE+'/V1/PA_HundredEyedSlag_V2']
CLIP_PATHS = [BASE+'/V1/Animations/A_HundredEyedSlag_'+role for role in ('AttackSweep_R','AttackSlam_R')]

def begin():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if u.EditorLevelLibrary.get_game_world() is not None:
        raise RuntimeError('Active PIE preserved; installation pending')
    paths = MESH_PATHS+[SKELETON_PATH]+CLIP_PATHS
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflict = dirty.intersection(paths)
    if conflict:
        raise RuntimeError('Unsaved target assets preserved: '+str(sorted(conflict)))
    for path in paths:
        source = PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup = OUT/'Before'/(path.removeprefix('/Game/')+'.uasset')
        if source.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)

def save(asset):
    LIB.set_metadata_tag(asset, 'HundredEyedSlag.Revision', REV)
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed '+asset.get_path_name())

def imp(file, path, options):
    folder, name = path.rsplit('/', 1)
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_name = name
    task.destination_path = folder
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(path)
    if asset is None or path not in [p.split('.')[0] for p in task.imported_object_paths]:
        raise RuntimeError('Import did not replace '+path+'; imported='+str(task.imported_object_paths))
    return asset

def install():
    begin()
    skeleton = u.load_asset(SKELETON_PATH)
    lod = u.load_asset(BASE+'/RuntimeV3/LOD_HundredEyedSlag_RuntimeV3')
    material = u.load_asset(BASE+'/PolishV2/Materials/M_HundredEyedSlag_Skin_V2')
    if skeleton is None or lod is None or material is None:
        raise RuntimeError('Existing saved skeleton, LOD settings and skin material required')
    variable = 'Interchange.FeatureFlags.Import.FBX'
    previous = u.SystemLibrary.get_console_variable_int_value(variable)
    u.SystemLibrary.execute_console_command(None, variable+' 0')
    try:
        meshes = []
        for path, physics_path in zip(MESH_PATHS, PHYSICS_PATHS):
            physics = u.load_asset(physics_path)
            if physics is None:
                raise RuntimeError('Existing anatomical physics asset required: '+physics_path)
            op = u.FbxImportUI()
            op.automated_import_should_detect_type = False
            op.override_full_name = True
            op.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
            op.import_as_skeletal = True
            op.import_mesh = True
            op.import_animations = False
            op.import_materials = False
            op.import_textures = False
            op.create_physics_asset = False
            op.skeleton = skeleton
            data = op.skeletal_mesh_import_data
            data.set_editor_property('normal_import_method', u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            data.set_editor_property('use_t0_as_ref_pose', False)
            data.set_editor_property('update_skeleton_reference_pose', False)
            mesh = imp(OUT/'Delivery/SK_HundredEyedSlag_ApeRecoveryV7.fbx', path, op)
            mesh.set_editor_property('enable_per_poly_collision', False)
            mesh.set_editor_property('physics_asset', physics)
            slots = list(mesh.get_editor_property('materials'))
            for slot in slots:
                slot.material_interface = material
            mesh.set_editor_property('materials', slots)
            build = EDITOR.get_lod_build_settings(mesh, 0)
            build.set_editor_property('recompute_normals', False)
            build.set_editor_property('recompute_tangents', True)
            build.set_editor_property('use_mikk_t_space', True)
            EDITOR.set_lod_build_settings(mesh, 0, build)
            mesh.set_editor_property('lod_settings', lod)
            # Derive the two lower LODs from the repaired skin, retaining V3 budgets.
            if not EDITOR.regenerate_lod(mesh, 3, False, False):
                raise RuntimeError('LOD generation failed '+path)
            save(mesh)
            meshes.append({'path':mesh.get_path_name(), 'saved':True, 'lods_generated':3,
                'physics_reused':physics.get_path_name(), 'material':material.get_path_name(),
                'bind_and_geometry_preserved':True})
            (OUT/'mesh_installation.json').write_text(json.dumps(meshes, indent=2))
            print('APE_V7_MESH_SAVED '+path, flush=True)

        mesh = u.load_asset(MESH_PATHS[0])
        sys.path.insert(0, str(PROJECT/'Tools/InfectedDog'))
        from meshy_animation_units import match_bind_root_scale
        reports = []
        contracts = json.loads((OUT/'animation_contract.json').read_text())['actions']
        for contract in contracts:
            path = BASE+'/V1/Animations/A_HundredEyedSlag_'+contract['name']
            op = u.FbxImportUI()
            op.automated_import_should_detect_type = False
            op.override_full_name = True
            op.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            op.import_as_skeletal = True
            op.import_mesh = False
            op.import_animations = True
            op.import_materials = False
            op.import_textures = False
            op.skeleton = skeleton
            op.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
            op.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
            clip = imp(OUT/'Delivery'/contract['file'], path, op)
            units = match_bind_root_scale(clip, mesh)
            clip.set_preview_skeletal_mesh(mesh)
            save(clip)
            reports.append({'role':contract['name'], 'path':clip.get_path_name(), 'saved':True,
                'seconds':clip.get_play_length(), 'units':units, 'hit_window_s':contract['hit_window_s'],
                'motion_source':'Original heavy ape-style authoring; no store animation sampled'})
            (OUT/'animation_installation.json').write_text(json.dumps(reports, indent=2))
            print('APE_V7_ATTACK_SAVED '+path, flush=True)
        save(skeleton)
    finally:
        u.SystemLibrary.execute_console_command(None, variable+' '+str(previous))
