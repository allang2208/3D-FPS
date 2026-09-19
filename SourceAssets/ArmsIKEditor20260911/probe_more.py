import unreal,json
from pathlib import Path
O=Path(__file__).parent
seq=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
proxies=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)
r=proxies[0].control_rig
d={'rig':r.get_path_name(),'rig_methods':[n for n in dir(r) if 'hierarch' in n or 'bone' in n or 'execute' in n], 'api':{}}
for c,ns in [(unreal.SequencerTools,['export_anim_sequence']), (unreal.ControlRigSequencerLibrary,['get_local_control_rig_euler_transforms','get_local_control_rig_euler_transform','set_local_control_rig_euler_transforms']), (unreal.LevelSequenceEditorBlueprintLibrary,['get_current_time','set_current_time','get_current_time_seconds']), (unreal.ControlRigBlueprint,['create_control_rig']), (unreal.MovieSceneBindingExtensions,['get_id']), (unreal.EditorAssetLibrary,['duplicate_loaded_asset'])]:
 for n in ns:d['api'][c.__name__+'.'+n]=str(getattr(c,n,None).__doc__)
(O/'probe_more.json').write_text(json.dumps(d,indent=2))
