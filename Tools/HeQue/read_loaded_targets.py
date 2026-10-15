"""Read-only ownership check before writing this new asset family in a commandlet."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');DEST='/Game/Monsters/HeQue'
packages=set()
folder=ROOT/'Content/Monsters/HeQue'
if folder.exists():
    packages.update('/Game/'+str(p.relative_to(ROOT/'Content').with_suffix('')).replace('\\','/') for p in folder.rglob('*.uasset'))
packages.update([DEST+'/BP_HeQue',DEST+'/RigV01/SK_HeQue',DEST+'/RigV01/SK_HeQue_Skeleton',DEST+'/RigV01/PA_HeQue_HitSurface'])
loaded=[p for p in sorted(packages) if u.find_object(None,p) is not None]
report={'loaded_target_packages':loaded,'target_asset_files':len(list(folder.rglob('*.uasset'))) if folder.exists() else 0,
    'pie_running':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'only_owned_output_root':DEST}
(ROOT/'SourceAssets/HeQueBoss20261014/RigV01/Records/editor-target-ownership.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_TARGET_OWNERSHIP '+json.dumps(report),flush=True)
if loaded:raise RuntimeError('Use current editor for its loaded HeQue packages; do not write them externally')
