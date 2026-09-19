import unreal,json
from pathlib import Path
O=Path(__file__).parent
E=unreal.LevelSequenceEditorBlueprintLibrary
seq=E.get_current_level_sequence(); assert '/M4VerticalGripClassRaised/Vertical/' in seq.get_path_name()
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig
h=rig.get_hierarchy()
def tf(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
d={'source':seq.get_path_name(),'frame':E.get_current_time(),'start':seq.get_playback_start(),'end':seq.get_playback_end(),'fps':seq.get_display_rate().numerator,'controls':[str(k.name) for k in h.get_controls()],'poses':[]}
dest='/Game/Weapons/M4ArmsIKEditor/LS_Vertical_UserFK_Backup'
assert not unreal.EditorAssetLibrary.does_asset_exist(dest)
backup=unreal.EditorAssetLibrary.duplicate_loaded_asset(seq,dest);assert backup
unreal.EditorAssetLibrary.save_loaded_asset(backup,False)
for frame in range(d['start'],d['end']):
 E.set_current_time(frame)
 d['poses'].append({str(k.name):tf(h.get_global_transform(k)) for k in h.get_bones()})
E.set_current_time(d['frame'])
(O/'source_snapshot.json').write_text(json.dumps(d))
unreal.log('ARMS_IK_SOURCE_SNAPSHOT_READY '+str(len(d['poses'])))
