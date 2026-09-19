import unreal,json,datetime
from pathlib import Path
O=Path(__file__).parent;E=unreal.LevelSequenceEditorBlueprintLibrary
seq=E.get_current_level_sequence();assert seq.get_name()=='LS_M4_Vertical_Idle_IK_Edit'
name='LS_Before_ArmRelax_'+datetime.datetime.now().strftime('%H%M%S')
backup=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,'/Game/Weapons/M4ArmsIKEditor',seq)
assert backup;unreal.EditorAssetLibrary.save_loaded_asset(backup,False)
r=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig;h=r.get_hierarchy()
def tf(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
out={'backup':backup.get_path_name(),'frame':str(E.get_current_time()),'bones':{},'controls':{},'channels':{}}
for b in h.get_bones():out['bones'][str(b.name)]={'pose':tf(h.get_global_transform(b)),'rest':tf(h.get_global_transform(b,True)),'parent':str(h.get_first_parent(b).name)}
for k in h.get_controls():out['controls'][str(k.name)]={'global':tf(h.get_global_transform(k)),'local':tf(h.get_local_transform(k))}
for b in seq.get_bindings():
 for t in b.get_tracks():
  if isinstance(t,unreal.MovieSceneControlRigParameterTrack):
   for s in t.get_sections():
    for ch in s.get_all_channels():out['channels'][str(ch.channel_name)]=[[k.get_time().frame_number.value,k.get_value()] for k in ch.get_keys()]
(O/'arm_before.json').write_text(json.dumps(out))
unreal.log('ARM_RELAX_BACKUP '+backup.get_path_name())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'viewmode unlit')
