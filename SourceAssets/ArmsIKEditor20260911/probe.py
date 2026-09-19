import unreal, json
from pathlib import Path
O=Path(__file__).parent
seq=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
rows={'sequence':seq.get_path_name() if seq else None,'bindings':[], 'api':{}}
if seq:
 for b in seq.get_bindings():
  rows['bindings'].append({'name':b.get_name(),'id':str(b.get_id()),'tracks':[str(t.get_class().get_name()) for t in b.get_tracks()]})
for cls in ['ControlRigSequencerLibrary','ControlRig','RigHierarchy','LevelSequenceEditorBlueprintLibrary','MovieScene3DAttachSection','MovieSceneBindingExtensions','RigControlSettings']:
 c=getattr(unreal,cls)
 rows['api'][cls]={n:str(getattr(c,n).__doc__) for n in dir(c) if any(x in n for x in ['export','bake','bound','binding','control_rig','evaluate','execute','global_transform','control_settings','shape','initial'])}
rows['actors']=[{'label':a.get_actor_label(),'path':a.get_path_name()} for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if 'A_M4_Vertical_idle' in a.get_actor_label()]
(O/'probe.json').write_text(json.dumps(rows,indent=2))
