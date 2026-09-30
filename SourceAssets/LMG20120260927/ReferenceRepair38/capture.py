import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary
body='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';a=u.load_asset(body)
out={'pie':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'dirty':[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'body':body,'sha256':hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest(),'slots':[{'id':i,'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for i,s in enumerate(a.materials)]}
(O/'capture.json').write_text(json.dumps(out,indent=2));print(json.dumps({'pie':out['pie'],'dirty':out['dirty'],'sha256':out['sha256']}))
