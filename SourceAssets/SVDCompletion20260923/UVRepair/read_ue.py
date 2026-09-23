import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/UVRepair');B='/Game/Weapons/SVDDragunov20260922'
r={'play_world':str(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'dirty':[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if 'svd' in x.get_name().lower()],'materials':{}}
mesh=u.load_asset(B+'/Complete20260923/SK_SVD_Manny');r['materials']={str(x.material_slot_name):x.material_interface.get_path_name() for x in mesh.materials}
for key in ['Body','ScopeBody']:
 m=u.load_asset(B+'/Materials/MI_SVD_'+key);r[key]={str(n):str(u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(m,n)) for n in u.MaterialEditingLibrary.get_texture_parameter_names(m)}
(O/'ue_before.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
