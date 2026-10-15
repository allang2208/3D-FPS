import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/ClawSweepV04')
DEST='/Game/Monsters/IncineratorBossM66/ClawSweepV04'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((ROOT/'Records/animation_manifest.json').read_text(encoding='utf-8'))
report={'saved':[],'clips':{},'root_units':{},'runtime_tested':False}
REPORT=ROOT/'Records/motion_import.json'
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving M66 animations')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 animation packages have unsaved changes')
mesh=u.load_asset('/Game/Monsters/IncineratorBossM66/RigV01/SK_M66_BackCompleted')
if not mesh:raise RuntimeError('M66 source skeletal mesh is missing')

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def match_root_units(clip):
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
    options.optional_skeletal_mesh=mesh
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,options)
    root=u.AnimPoseExtensions.get_bone_names(pose)[0]
    ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
    first=u.AnimPoseExtensions.get_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
    target=[ref.scale3d.x,ref.scale3d.y,ref.scale3d.z];previous=[first.scale3d.x,first.scale3d.y,first.scale3d.z]
    changed=max(abs(a-b) for a,b in zip(target,previous))>1e-5
    if changed:
        count=clip.get_editor_property('data_model_interface').get_number_of_keys();positions=[];rotations=[];scales=[]
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/max(1,count-1),options)
            value=u.AnimPoseExtensions.get_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
            positions.append(value.translation);rotations.append(value.rotation);scales.append(u.Vector(*target))
        ctrl=clip.get_editor_property('controller');ctrl.open_bracket('Match M66 imported root units',False)
        try:
            if not ctrl.set_bone_track_keys(root,positions,rotations,scales,False):raise RuntimeError('Root bind scale repair failed')
        finally:ctrl.close_bracket(False)
    return {'root':str(root),'before':previous,'bind':target,'changed':changed}

old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for row in manifest['clips']:
        name='A_M66_'+row['role']+'_V04';path=DEST+'/'+name
        clip=u.load_asset(path) if E.does_asset_exist(path) else None
        if not clip:
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True;options.skeleton=mesh.skeleton
            options.import_materials=False;options.import_textures=False
            data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True
            data.force_front_x_axis=True;data.import_uniform_scale=1.
            data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=DEST;task.destination_name=name
            task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
            A.import_asset_tasks([task]);clip=u.load_asset(path)
            if not clip:raise RuntimeError('Animation import failed '+path)
        # Finish asynchronous compression before reading or adjusting source tracks.
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation finalization failed')
        report['root_units'][row['role']]=match_root_units(clip)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',row['loop']);clip.set_preview_skeletal_mesh(mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation finalization failed')
        E.set_metadata_tag(clip,'M66.Authoring','M66 first attack: original planted claw sweep V04; no runtime acceptance')
        E.set_metadata_tag(clip,'M66.AttackRole',row['role'])
        report['clips'][row['role']]=clip.get_path_name();save(clip)
    save(mesh.skeleton);report['complete']=True
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M66_MOTION_SAVED '+json.dumps(report,ensure_ascii=False))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
