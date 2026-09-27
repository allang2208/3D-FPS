"""Read only the live material binding required for this production batch."""
import unreal as u,json
from pathlib import Path
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
mesh=u.load_asset('/Game/Weapons/DarkBow20260925/ModularV13/SM_Bow_ArrowRestWood')
if not mesh:raise RuntimeError('Current wooden rest missing')
result={'game_world_active':bool(editor.get_game_world()),'materials':{
    str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
Path(__file__).with_name('source-binding.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('BOW_REST_SOURCE',json.dumps(result))
