import unreal,json,math
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4ReloadFinger20260909')
BASE='/Game/Weapons/M4InfimaRigV4'
DEST=BASE+'/ReloadFinger'
mesh=unreal.load_asset(BASE+'/SK_M4_Infima');assert mesh
report={}
names=['WPN_root','WPN_Trigger','WPN_SOCKET_Magazine','hand_r','hand_l','index_01_r','index_02_r','index_03_r']
def pose(a,t,kind):
    opt=unreal.AnimPoseEvaluationOptions();opt.evaluation_type=kind;opt.optional_skeletal_mesh=mesh
    p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt)
    assert unreal.AnimPoseExtensions.is_valid(p)
    return {n:unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD) for n in names}
def position_error(a,b):
    return math.sqrt(sum((x-y)**2 for x,y in zip([a.translation.x,a.translation.y,a.translation.z],[b.translation.x,b.translation.y,b.translation.z])))
def angle(a,b):
    qa=a.rotation;qb=b.rotation
    x=[qa.w,qa.x,qa.y,qa.z];y=[qb.w,qb.x,qb.y,qb.z]
    dot=abs(sum(i*j for i,j in zip(x,y)))/math.sqrt(sum(i*i for i in x)*sum(i*i for i in y))
    return math.degrees(2*math.acos(min(1,dot)))
for clip in ['reload','reload_empty']:
    name='A_AKM_'+clip
    o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
    o.import_mesh=False;o.import_as_skeletal=False;o.import_animations=True;o.skeleton=mesh.skeleton;o.import_materials=False;o.import_textures=False
    o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    task=unreal.AssetImportTask();task.filename=str(OUT/(name+'.fbx'));task.destination_path=DEST
    task.automated=True;task.replace_existing=True;task.save=True;task.options=o
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);assert task.imported_object_paths
    a=unreal.load_asset(DEST+'/'+name);old=unreal.load_asset(BASE+'/'+name);assert a and old
    a.set_editor_property('bone_compression_settings',unreal.load_asset(BASE+'/BC_M4Viewmodel'))
    unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
    assert a.get_editor_property('skeleton')==old.get_editor_property('skeleton')==mesh.skeleton
    assert abs(a.get_play_length()-old.get_play_length())<.0001
    assert a.get_editor_property('number_of_sampled_keys')==189
    compression=0;unchanged=0;endpoints=0;rotation_unchanged=0;curl_changes={}
    for i in range(377):
        t=min(i/120,a.get_play_length())
        raw=pose(a,t,unreal.AnimDataEvalType.RAW);compressed=pose(a,t,unreal.AnimDataEvalType.COMPRESSED);baseline=pose(old,t,unreal.AnimDataEvalType.RAW)
        for n in names:
            compression=max(compression,position_error(raw[n],compressed[n]))
            if not n.startswith('index_'):
                unchanged=max(unchanged,position_error(raw[n],baseline[n]));rotation_unchanged=max(rotation_unchanged,angle(raw[n],baseline[n]))
            if i in [0,376]:endpoints=max(endpoints,position_error(raw[n],baseline[n]))
            if i==120 and n.startswith('index_'):curl_changes[n]=angle(baseline[n],compressed[n])
    assert unchanged<.002,(clip,unchanged)
    assert rotation_unchanged<.01,(clip,rotation_unchanged)
    assert endpoints<.002,(clip,endpoints)
    assert compression<.05,(clip,compression)
    assert curl_changes['index_02_r']>40,curl_changes
    report[clip]={'asset':a.get_path_name(),'duration':a.get_play_length(),'samples_120hz':377,'compression_max_position_error_cm':compression,
        'untouched_world_position_error_cm':unchanged,'untouched_rotation_error_degrees':rotation_unchanged,'endpoint_position_error_cm':endpoints,'mid_reload_index_rotation_change_degrees':curl_changes}
(OUT/'ue_validation.json').write_text(json.dumps(report,indent=2))
unreal.log('M4_RELOAD_FINGER_IMPORT_VALIDATION_PASS')
