import unreal,json
from pathlib import Path
seq=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
d=[]
for b in seq.get_bindings():
 for t in b.get_tracks():
  if isinstance(t,unreal.MovieSceneControlRigParameterTrack):
   for s in t.get_sections():
    d.append({'active':s.is_active(),'channels':len(s.get_all_channels()),'rows':[{'name':str(ch.channel_name),'keys':ch.get_num_keys(),'first':str(ch.get_keys()[0].get_value()) if ch.get_num_keys() else None} for ch in s.get_all_channels() if 'upperarm_l' in str(ch.channel_name) or 'root_fk' in str(ch.channel_name)]})
Path(__file__).with_suffix('.json').write_text(json.dumps(d,indent=2))
