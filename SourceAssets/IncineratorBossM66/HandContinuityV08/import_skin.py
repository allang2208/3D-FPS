import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/HandContinuityV08')
DEST='/Game/Monsters/IncineratorBossM66';VERSION=DEST+'/HandContinuityV08'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before importing the M66 hand repair')
owned_resume={VERSION+'/SK_M66_HandContinuity_V08',DEST+'/RigV01/SK_M66_BackCompleted_Skeleton'} if globals().get('M66_RESUME_OWNED_IMPORT',False) else set()
if any(p.get_path_name().startswith(DEST) and p.get_path_name() not in owned_resume for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
manifest=json.loads((ROOT/'Records/animation_manifest.json').read_text())
bp=u.load_asset(DEST+'/BP_M66RigPreview');cdo=u.get_default_object(bp.generated_class())
original=cdo.get_editor_property('visual_mesh');physics=cdo.get_editor_property('reaction_physics')
if not original or not physics:raise RuntimeError('Current M66 mesh or reaction physics missing')
path=VERSION+'/SK_M66_HandContinuity_V08'
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    revised=u.load_asset(path) if E.does_asset_exist(path) else None
    if not revised:
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
        options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
        options.skeleton=original.skeleton
        data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True
        data.force_front_x_axis=True;data.import_uniform_scale=1.
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.set_editor_property('update_skeleton_reference_pose',False)
        task=u.AssetImportTask();task.filename=manifest['fbx'];task.destination_path=VERSION
        task.destination_name='SK_M66_HandContinuity_V08';task.automated=True;task.save=False
        task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);revised=u.load_asset(path)
        if not revised:raise RuntimeError('M66 hand skin import failed')
    revised.set_editor_property('materials',original.get_editor_property('materials'))
    revised.set_editor_property('physics_asset',physics)
    u.SkeletalMeshEditorSubsystem.set_allow_cpu_access(revised,True)
    E.set_metadata_tag(revised,'M66.HandSkin','V08: distal hand foreign leg/trunk weights removed; original geometry, UVs and V05 eye controls retained')
    saved=[]
    for asset in (revised.skeleton,revised):
        if not E.save_loaded_asset(asset,False):raise RuntimeError('M66 hand asset save failed: '+asset.get_path_name())
        saved.append(asset.get_path_name())
    report={'complete':True,'saved':saved,'previous_mesh':original.get_path_name(),
        'physics_preserved':physics.get_path_name(),'edited_vertices':manifest['edited_vertices'],
        'surface_fallback_cpu_access_enabled':True,'runtime_tested':False,'multiplayer_tested':False}
    (ROOT/'Records/skin_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('M66_HAND_SKIN_SAVED '+json.dumps(report))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
