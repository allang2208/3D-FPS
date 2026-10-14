import unreal as u,json,builtins
from pathlib import Path
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/gunbench_import_20261006');assert '-GunWorkbenchApproved20261006' in u.SystemLibrary.get_command_line()
m=u.load_asset('/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench');root='/Game/Building/GunWorkbenchApproved20261006/Materials/'
mapping={'Ammo_ammo_556_0':'M_GWDesign_Ammo_556_Paper','Ammo_ammo_556_1':'M_GWDesign_AmmoMetal','Ammo_ammo_762_0':'M_GWDesign_Ammo_762_Paper','Ammo_ammo_762_1':'M_GWDesign_AmmoMetal'};changes=[]
for i,slot in enumerate(m.static_materials):
 name=str(slot.material_slot_name)
 if name in mapping:
  mat=u.load_asset(root+mapping[name]);assert mat;changes.append({'slot':name,'previous':slot.material_interface.get_path_name(),'new':mat.get_path_name()});m.set_material(i,mat)
assert len(changes)==4;assert u.EditorAssetLibrary.save_loaded_asset(m,False)
(W/'ammo_binding_fix.json').write_text(json.dumps(changes,indent=2));print('APPROVED_AMMO_BINDINGS',json.dumps(changes))
