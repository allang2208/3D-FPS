"""Install the photographed open-claw shape through the existing editor batch gate."""
import unreal as u
import json, shutil
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = ROOT.parents[2]
DEST = '/Game/Monsters/Mutant3Meshy/KhaimeraV2'
lib = u.EditorAssetLibrary
contract = json.loads((ROOT/'animation_contract.json').read_text())
targets = [DEST+'/SK_Mutant3_Claw', DEST+'/SK_Mutant3_Claw_Skeleton']
targets += [DEST+'/Animations/A_Mutant3_'+role for role in contract['clips']]

def install():
    # Production helper repairs source AND cached render-section material indices.
    # A plain Materials-array restore after FBX import can leave section 1 with
    # only slot 0 present, producing the default surface despite valid textures.
    if not hasattr(u, 'Mutant3') or not hasattr(u.Mutant3, 'repair_surface_binding'):
        raise RuntimeError('Build FPSGAMEEditor with the Mutant3 surface repair helper before importing')
    # Protect actual unsaved edits to these packages, not unrelated editor work.
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = [p for p in targets if p in dirty]
    if conflicts:
        raise RuntimeError('Target packages have unsaved edits; no import performed: '+str(conflicts))
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if world:
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        (ROOT/'import_state.json').write_text(json.dumps({'state':'PIE end requested; no assets changed'}),encoding='utf-8')
        u.log('OPEN_CLAW_WAITING_FOR_PIE_END')
        return

    # Keep a disk recovery copy before replacing the previously delivered hand.
    backup = ROOT/'before_content'
    for asset in targets:
        relative = Path(asset.removeprefix('/Game/'))
        for suffix in ['.uasset','.uexp','.ubulk']:
            original = PROJECT/'Content'/relative.with_suffix(suffix)
            saved = backup/relative.with_suffix(suffix)
            if original.exists() and not saved.exists():
                saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original,saved)

    mesh = u.load_asset(targets[0])
    skeleton = u.load_asset(targets[1])
    materials = list(mesh.get_editor_property('materials'))
    physics = mesh.get_editor_property('physics_asset')
    compatible = list(skeleton.get_editor_property('compatible_skeletons'))
    state = {'state':'importing','mesh':targets[0],'saved':[]}
    def save(asset):
        if not lib.save_loaded_asset(asset,False): raise RuntimeError('Failed saving '+asset.get_path_name())
        state['saved'].append(asset.get_path_name())
        (ROOT/'import_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    def imp(file,name,path,options):
        task = u.AssetImportTask()
        task.filename=str(file); task.destination_name=name; task.destination_path=path
        task.options=options; task.automated=True; task.save=False
        task.replace_existing=True; task.replace_existing_settings=True
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not task.imported_object_paths: raise RuntimeError('No imported asset for '+name)
        return u.load_asset(path+'/'+name)

    cvar = 'Interchange.FeatureFlags.Import.FBX'
    old_importer = u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal=True; options.import_mesh=True; options.import_animations=False
        options.import_materials=False; options.import_textures=False; options.create_physics_asset=False
        options.skeleton=skeleton
        data=options.skeletal_mesh_import_data
        # Preserve the source body's baked-normal basis; UE computes Mikk tangents.
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.set_editor_property('use_t0_as_ref_pose',False)
        data.set_editor_property('convert_scene_unit',True)
        # The new skin and stronger finger neutral transforms must agree. Old
        # hand/body hierarchy stays the same; update this V2 skeleton, not V1.
        data.set_editor_property('update_skeleton_reference_pose',True)
        mesh=imp(ROOT/'SK_Mutant3_Claw.fbx','SK_Mutant3_Claw',DEST,options)
        mesh.set_editor_property('materials',materials)
        mesh.set_editor_property('physics_asset',physics)
        mesh_editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        build=mesh_editor.get_lod_build_settings(mesh,0)
        build.recompute_normals=False
        build.recompute_tangents=True
        build.use_mikk_t_space=True
        build.use_full_precision_u_vs=True
        mesh_editor.set_lod_build_settings(mesh,0,build)
        if not u.Mutant3.repair_surface_binding(mesh):
            raise RuntimeError('Failed to rebuild Mutant3 source/render material binding')
        skeleton=mesh.skeleton
        skeleton.set_editor_property('compatible_skeletons',compatible)
        lib.set_metadata_tag(mesh,'HandRevision','Open spread claw from user photo 2026-09-23')
        save(skeleton); save(mesh)

        for role,info in contract['clips'].items():
            name='A_Mutant3_'+role
            options=u.FbxImportUI(); options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False; options.import_as_skeletal=True; options.import_animations=True
            options.import_materials=False; options.import_textures=False; options.skeleton=skeleton
            data=options.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate',False)
            data.set_editor_property('custom_sample_rate',60)
            data.set_editor_property('convert_scene_unit',True)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            clip=imp(ROOT/'animations'/(name+'.fbx'),name,DEST+'/Animations',options)
            clip.set_preview_skeletal_mesh(mesh)
            clip.set_editor_property('loop',info['loop'])
            clip.set_editor_property('enable_root_motion',False)
            clip.set_editor_property('force_root_lock',True)
            lib.set_metadata_tag(clip,'HandRevision','Open spread claw; original V2 body action curves retained')
            lib.set_metadata_tag(clip,'SourceURL',contract['source_url'])
            save(clip)
        save(skeleton)
        state['state']='Mesh, skeleton and nine animations saved; no gameplay or visual tests'
        (ROOT/'import_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        contract['state']=state['state']
        (ROOT/'animation_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
        u.log('MUTANT3_OPEN_CLAW_SAVED '+str(len(contract['clips']))+' animations; mesh and skeleton')
    finally:
        u.SystemLibrary.execute_console_command(None,cvar+' '+str(old_importer))

install()
