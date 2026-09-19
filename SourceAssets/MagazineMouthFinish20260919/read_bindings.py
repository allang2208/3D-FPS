import unreal as u,json
from pathlib import Path
paths=['/Game/Weapons/ExtMagPattern20260919/Surface/SM_ExtMag_M440','/Game/Weapons/ExtMagPattern20260919/Surface/SM_ExtMag_QBZ40','/Game/Weapons/ExtMagContact20260919/SM_ExtMag_AKM40_Closed']
r={}
for p in paths:
 m=u.load_asset(p);r[p]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in m.static_materials]
Path(__file__).with_name('current_bindings.json').write_text(json.dumps(r,indent=2))
