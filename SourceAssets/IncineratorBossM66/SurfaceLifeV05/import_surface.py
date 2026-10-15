"""Import the repaired skin on the existing skeleton, then save the active M66 defaults."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SurfaceLifeV05')
DEST='/Game/Monsters/IncineratorBossM66';VERSION=DEST+'/SurfaceLifeV05'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((ROOT/'Records/rig_completion.json').read_text(encoding='utf-8'))
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving the revised M66 skin')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
original=u.load_asset(DEST+'/RigV01/SK_M66_BackCompleted');bp=u.load_asset(DEST+'/BP_M66RigPreview')
physics=(u.get_default_object(bp.generated_class()).get_editor_property('reaction_physics') if bp else None)
if not physics:physics=u.load_asset(DEST+'/ReactionsV03/PA_M66_Reactions_V03')
if not original or not bp or not physics:raise RuntimeError('M66 existing mesh, character or physics asset is missing')
saved=[]
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    saved.append(asset.get_path_name())
path=VERSION+'/SK_M66_SurfaceLife_V05'
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
        task=u.AssetImportTask();task.filename=manifest['fbx'];task.destination_path=VERSION;task.destination_name='SK_M66_SurfaceLife_V05'
        task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);revised=u.load_asset(path)
        if not revised:raise RuntimeError('M66 revised skin import failed')
    revised.set_editor_property('materials',original.get_editor_property('materials'))
    revised.set_editor_property('physics_asset',physics)
    E.set_metadata_tag(revised,'M66.SkinRepair','Right oral wall uses trunk weights; small hand preserved; coincident seams share weights')
    E.set_metadata_tag(revised,'M66.Eyes','Seven local eye controls, original geometry and textures retained')
    save(revised.skeleton);save(revised)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for key,value in {'visual_mesh':revised,'walk_speed':160.,'return_speed':130.,'turn_speed':100.}.items():
        cdo.set_editor_property(key,value)
    component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(revised)
    component.set_physics_asset(physics,True);component.set_anim_instance_class(u.M66AnimInstance.static_class())
    movement=cdo.get_editor_property('character_movement')
    for key,value in {'max_walk_speed':160.,'max_acceleration':280.,'braking_deceleration_walking':440.,'rotation_rate':u.Rotator(0.,100.,0.)}.items():
        movement.set_editor_property(key,value)
    E.set_metadata_tag(bp,'M66.Stage','V05 oral skin repair, idle/move eye and posterior life motion, doubled movement/turn speed; attack 01 retained')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report={'complete':True,'saved':saved,'mesh':revised.get_path_name(),'skeleton':revised.skeleton.get_path_name(),
        'eyes':[eye['bone'] for eye in manifest['eyes']],'mouth_vertices':manifest['mouth_vertices'],
        'walk_cm_s':160,'return_cm_s':130,'turn_deg_s':100,'animation_stride_unchanged':True,
        'attack_timing_unchanged':True,'runtime_tested':False,'multiplayer_tested':False}
    (ROOT/'Records/ue_import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M66_SURFACE_LIFE_SAVED '+json.dumps(report,ensure_ascii=False))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
