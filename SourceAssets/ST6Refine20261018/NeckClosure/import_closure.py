"""Save only the revised ST6 mesh family; preserve the saved fabric materials."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;BASE=O.parent
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('The game is running. Preserve its loaded outfit meshes until PIE ends.')
file=BASE/'import_assets.py'
context={'__file__':str(file)}
exec(compile(file.read_text().split("\nif '-run='",1)[0],str(file),'exec'),context)
receipt=json.loads((BASE/'import_receipt.json').read_text())
receipt['completed']=False
receipt['saved']=[p for p in receipt['saved'] if '/Materials/' in p]
receipt['source_sha256']={}
context['receipt']=receipt
context['skeletal']('collar.json','SK_Jason_ST6Trims')
context['skeletal']('world_shirt.json','SK_Jason_ST6Refined')
context['pickup']()
receipt['completed']=True
(BASE/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
(O/'saved.json').write_text(json.dumps(receipt,indent=2))
print('ST6_NECK_CLOSURE_SAVED',flush=True)
