import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
print('GAME_WORLD',w.get_path_name() if w else None)
for profile in ['M4','PKM']:
 path=c['items']['ue_field_gloves']['skin_meshes'][profile]
 mesh=u.load_asset(path)
 print(profile,[(str(m.material_slot_name),m.material_interface.get_path_name() if m.material_interface else '') for m in mesh.get_editor_property('materials')])
print('API',u.GeometryScriptMeshReadLOD.__doc__,u.GeometryScriptMeshWriteLOD.__doc__)
