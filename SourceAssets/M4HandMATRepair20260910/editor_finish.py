import unreal,json,base64
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4HandMATRepair20260910')
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;report={}
for clip,end in [('reload',126),('reload_empty',162),('equip_charge',38)]:
 prod=unreal.load_asset('/Game/Weapons/M4HK416Replica/A_M4_HK416_'+clip);candidate=unreal.load_asset('/Game/Weapons/M4HandMATRepair/A_M4_MAT_'+clip);err=0
 for f in range(end*2+1):
  a=unreal.AnimPoseExtensions.get_anim_pose_at_time(prod,f/120,opt);b=unreal.AnimPoseExtensions.get_anim_pose_at_time(candidate,f/120,opt)
  for n in ['hand_l','hand_r','lowerarm_twist_01_l','index_03_l','middle_03_l','thumb_03_l','WPN_root','WPN_SOCKET_Magazine','WPN_ChargingHandle']:
   x=unreal.AnimPoseExtensions.get_bone_pose(a,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(b,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.01,(clip,err);report[clip]={'runtime_asset_matches_reviewed_candidate_cm':err,'samples':end*2+1}
(O/'published_pose_validation.json').write_text(json.dumps(report,indent=2))
seq=unreal.load_asset('/Game/Weapons/M4HandMATRepair/LS_M4_Hand_reload_empty');unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq);unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(130)
widget=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT'));proxy=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0];widget.set_editor_property('SelectedControlRig',proxy)
proxy.control_rig.clear_control_selection();proxy.control_rig.select_control('hand_l_fk_ctrl',True)
if hasattr(unreal,'SlateInspectorToolset'):
 snap=unreal.get_default_object(unreal.SlateInspectorToolset).call_method('Snapshot',('',15,False));(O/'mat_ui_snapshot.txt').write_text(str(snap),encoding='utf-8')
