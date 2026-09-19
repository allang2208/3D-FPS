import unreal,json,hashlib
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910');DEST='/Game/Weapons/M4HK416Replica'
old=unreal.load_asset('/Game/Weapons/M4FoldingSights/SK_M4_FoldingSights');assert old
skel=unreal.load_asset(DEST+'/SK_M4_HK416_Skeleton')
if not skel:skel=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('SK_M4_HK416_Skeleton',DEST,old.skeleton)
skel.add_compatible_skeleton(old.skeleton)
def imp(name,kind):
 o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=kind;o.skeleton=skel;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
 o.import_mesh=kind==unreal.FBXImportType.FBXIT_SKELETAL_MESH;o.import_as_skeletal=o.import_mesh;o.import_animations=not o.import_mesh
 if o.import_animations:
  o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 t=unreal.AssetImportTask();t.filename=str(OUT/(name+'.fbx'));t.destination_path=DEST;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True;t.options=o
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);assert t.imported_object_paths;return unreal.load_asset(DEST+'/'+name)
mesh=imp('SK_M4_FoldingSights_HK416',unreal.FBXImportType.FBXIT_SKELETAL_MESH)
materials={str(m.material_slot_name):m.material_interface for m in old.materials};slots=mesh.materials
for i,m in enumerate(slots):m.material_interface=materials[str(m.material_slot_name)];slots[i]=m
mesh.set_editor_property('materials',slots);unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
unreal.EditorAssetLibrary.save_loaded_asset(skel,only_if_is_dirty=False)
report={}
def pose(a,t,kind):
 opt=unreal.AnimPoseEvaluationOptions();opt.evaluation_type=kind;opt.optional_skeletal_mesh=mesh
 p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt);assert unreal.AnimPoseExtensions.is_valid(p)
 return p
get=lambda p,n:unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD)
for clip,length in [('reload',2.1),('reload_empty',2.7),('equip_charge',38/60),('drum_reload',2.1),('drum_reload_empty',2.7)]:
 a=imp('A_M4_HK416_'+clip,unreal.FBXImportType.FBXIT_ANIMATION);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
 unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False);assert abs(a.get_play_length()-length)<.0001
 err=0;drift=0;baseline=None;count=round(length*120)+1;handle=[];bolt=[]
 for i in range(count):
  t=min(i/120,length);raw=pose(a,t,unreal.AnimDataEvalType.RAW);packed=pose(a,t,unreal.AnimDataEvalType.COMPRESSED)
  for n in ['WPN_root','WPN_ChargingHandle','WPN_SOCKET_Magazine','WPN_bolt','hand_l','hand_r','index_03_r','pinky_03_l']:err=max(err,get(raw,n).translation.distance(get(packed,n).translation))
  root=get(packed,'WPN_root');rel={n:root.inverse_transform_location(get(packed,n).translation) for n in ['WPN_Trigger','WPN_RearSight','WPN_FrontSight']}
  if baseline is None:baseline=rel
  for n in rel:drift=max(drift,rel[n].distance(baseline[n]))
  handle.append(root.inverse_transform_location(get(packed,'WPN_ChargingHandle').translation));bolt.append(root.inverse_transform_location(get(packed,'WPN_bolt').translation))
 assert err<.05,(clip,err);assert drift<.002,(clip,drift)
 report[clip]={'duration':a.get_play_length(),'sampled_keys':a.get_editor_property('number_of_sampled_keys'),'samples_120hz':count,'compressed_error_cm':err,'rigid_drift_cm':drift*100,'handle_travel_cm':max(p.distance(handle[0]) for p in handle)*100,'bolt_travel_cm':max(p.distance(bolt[0]) for p in bolt)*100}
idle=unreal.load_asset('/Game/Weapons/M4InfimaRigV4/A_AKM_idle');p=pose(idle,0,unreal.AnimDataEvalType.COMPRESSED);assert get(p,'hand_l').translation.length()>1
report['old_idle_compatible']=True
t=unreal.AssetImportTask();t.filename=str(OUT/'Audio/equip.wav');t.destination_path='/Game/Weapons/M4HK416Audio';t.destination_name='S_HK416_Equip';t.automated=True;t.replace_existing=True;t.save=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);sound=unreal.load_asset('/Game/Weapons/M4HK416Audio/S_HK416_Equip');assert sound
sound.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE);unreal.EditorAssetLibrary.save_loaded_asset(sound,only_if_is_dirty=False)
report['equip_sound']={'duration':sound.duration,'source_sha256':hashlib.sha256((OUT/'Audio/equip.wav').read_bytes()).hexdigest()}
(OUT/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('M4_HK416_REPLICA_IMPORT_PASS '+json.dumps(report))
