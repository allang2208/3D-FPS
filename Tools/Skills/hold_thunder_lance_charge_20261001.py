"""Keep the existing lance charge particles alive while the user holds charge."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir());sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import put,save
PATH='/Game/Skills/ElectricMagic/NS_ThunderCharge'
if any(str(p.get_path_name())==PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved thunder charge')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('End PIE before saving thunder charge')
system=u.load_asset(PATH)
if not system:raise RuntimeError('Missing existing thunder charge')
loop=u.RainAssetEditor.read_input(system,'','SystemUpdateScript','SystemState','Loop Behavior')
value=loop.replace('NewEnumerator1','NewEnumerator0').replace('"Once"','"Infinite"')
put(system,'','SystemUpdateScript','SystemState','Loop Behavior',value,'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
save(system)
folder=ROOT/'Saved/ThunderLanceCharge20261001';folder.mkdir(parents=True,exist_ok=True)
receipt={'saved_asset':system.get_path_name(),'system_loop':'Infinite','before':loop,'after':value,
         'cleanup':'component release/cancel/death/endplay','gameplay_tested':False,'rendered':False}
(folder/'charge-hold-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('THUNDER_LANCE_CHARGE_HOLD_SAVED '+json.dumps(receipt))
