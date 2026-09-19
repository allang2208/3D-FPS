import unreal,json
from pathlib import Path
E=unreal.LevelSequenceEditorBlueprintLibrary
r=unreal.ControlRigSequencerLibrary.get_control_rigs(E.get_current_level_sequence())[0].control_rig
d={'methods':{n:str(getattr(r,n).__doc__) for n in dir(r) if 'event' in n or 'evaluate' in n},'can':r.can_execute(),'events':[str(x) for x in r.get_supported_events()]}
d['class']=r.get_class().get_path_name()
d['execute_results']={str(x):r.execute_event(x) for x in r.get_supported_events()}
d['baseline']={str(k.name):str(r.get_hierarchy().get_global_transform(k)) for k in r.get_hierarchy().get_bones() if str(k.name) in ['upperarm_l','lowerarm_l','hand_l']}
Path(__file__).with_suffix('.json').write_text(json.dumps(d,indent=2))
