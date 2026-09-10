import unreal,json
from pathlib import Path
O=Path(__file__).parent;report={}
for clip in ['reload','reload_empty','equip_charge']:
 seq=unreal.load_asset('/Game/Weapons/M4WrapGripFinal/LS_M4_WrapGrip_'+clip);assert seq
 channels=keys=0
 for binding in seq.get_bindings():
  for track in binding.get_tracks():
   if 'ControlRig' not in track.get_class().get_name():continue
   for section in track.get_sections():
    for channel in section.get_all_channels():
     channels+=1;keys+=len(channel.get_keys())
 assert keys>1000,(clip,channels,keys);report[clip]={'channels':channels,'keys':keys}
(O/'mat_saved_validation.json').write_text(json.dumps(report,indent=2));unreal.log('M4_MAT_SAVED_READBACK_PASS')
