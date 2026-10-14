import json
from pathlib import Path
import unreal as u
m=u.load_asset('/Game/Weapons/TacticalDevices20260913/DualFit20261008/HK416/SM_laser_1')
s=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
r={'slots':[str(v.material_slot_name) for v in m.static_materials],
   'section_slots':[s.get_lod_material_slot(m,0,i) for i in range(m.get_num_sections(0))]}
(Path(__file__).parent/'import-slots.json').write_text(json.dumps(r,indent=2))
print('HK416_IMPORT_SLOTS',json.dumps(r))
