import unreal,json
from pathlib import Path
seq=unreal.load_asset('/Game/Weapons/M4ArmsIKEditor/LS_Vertical_UserFK_Backup')
d=[]
for b in seq.get_bindings():
 for t in b.get_tracks():
  if isinstance(t,unreal.MovieSceneControlRigParameterTrack):
   for s in t.get_sections():
    for ch in s.get_all_channels():
     if any(x in str(ch.channel_name) for x in ['index_02_l','hand_l','upperarm_l']):
      keys=ch.get_keys();values=[k.get_value() for k in keys]
      d.append({'name':str(ch.channel_name),'count':len(keys),'unique':len(set(values)),'first':values[:3],'last':values[-1:]})
Path(__file__).with_suffix('.json').write_text(json.dumps(d,indent=2))
