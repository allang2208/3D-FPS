import unreal,json,math
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909');DEST='/Game/Weapons/M4EmptyReload'
old=unreal.load_asset('/Game/Weapons/M4InfimaRigV4/SK_M4_Infima');assert old
def imp(file,options):
    t=unreal.AssetImportTask();t.filename=str(OUT/file);t.destination_path=DEST;t.automated=True;t.replace_existing=True;t.save=True;t.options=options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);assert t.imported_object_paths
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False;o.skeleton=old.skeleton
imp('SK_M4_Infima_BoltReceiver.fbx',o)
mesh=unreal.load_asset(DEST+'/SK_M4_Infima_BoltReceiver');assert mesh.skeleton==old.skeleton
materials={str(m.material_slot_name):m.material_interface for m in old.materials};slots=mesh.materials
for i,m in enumerate(slots):m.material_interface=materials[str(m.material_slot_name)];slots[i]=m
mesh.set_editor_property('materials',slots);unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
o.import_mesh=False;o.import_as_skeletal=False;o.import_animations=True;o.skeleton=old.skeleton;o.import_materials=False;o.import_textures=False
o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
imp('A_M4_ReloadEmpty_BoltRelease.fbx',o)
a=unreal.load_asset(DEST+'/A_M4_ReloadEmpty_BoltRelease');assert a
a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
assert abs(a.get_play_length()-3.8)<.0001
assert a.get_editor_property('number_of_sampled_keys')==229
names=['WPN_root','WPN_bolt','WPN_Trigger','WPN_RearSight','WPN_FrontSight','hand_l','hand_r','index_02_r']
def pose(t,kind):
    opt=unreal.AnimPoseEvaluationOptions();opt.evaluation_type=kind;opt.optional_skeletal_mesh=mesh
    p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt);assert unreal.AnimPoseExtensions.is_valid(p)
    return {n:unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD) for n in names}
max_error=0;rigid_error=0;baseline=None;bolt=[]
for i in range(457):
    t=i/120;raw=pose(t,unreal.AnimDataEvalType.RAW);packed=pose(t,unreal.AnimDataEvalType.COMPRESSED)
    for n in names:max_error=max(max_error,raw[n].translation.distance(packed[n].translation))
    local={n:packed['WPN_root'].inverse_transform_location(packed[n].translation) for n in names if n.startswith('WPN_')}
    if baseline is None:baseline=local
    for n in ['WPN_Trigger','WPN_RearSight','WPN_FrontSight']:rigid_error=max(rigid_error,local[n].distance(baseline[n]))
    if i in [0,360,368,456]:bolt.append({'time':t,'relative':[local['WPN_bolt'].x,local['WPN_bolt'].y,local['WPN_bolt'].z]})
assert max_error<.05,max_error
assert rigid_error<.0002,rigid_error
report={'mesh':mesh.get_path_name(),'animation':a.get_path_name(),'duration':a.get_play_length(),'sample_count_120hz':457,
    'compression_max_position_error_cm':max_error,'receiver_parts_relative_error':rigid_error,'bolt_samples':bolt}
(OUT/'empty_import.json').write_text(json.dumps(report,indent=2));unreal.log('M4_EMPTY_IMPORT_VALIDATION_PASS')
