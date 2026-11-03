"""Restrict only the disposable host's cook profile to the hammer scenario."""
from pathlib import Path
import json,re
R=Path('D:/FPS3D/FPSGAME');H=Path('D:/FPS3D/ThunderHammerFullReviewHost20261102');O=Path(__file__).parent
pre=json.loads((O/'dependency-preflight.json').read_text(encoding='utf-8'))
dirs={a['package'].rsplit('/',1)[0] for a in pre['assets'] if a['exists']}
dirs.add('/Game/Weapons/SteelWarhammer20261014')
dirs.add('/Game/ColdSteelData/AttachmentIcons20260913')
dirs={x for x in dirs if not any(x!=y and x.startswith(y+'/') for y in dirs)}
cfg=(R/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
cfg+='\n[/Script/UnrealEd.ProjectPackagingSettings]\n!DirectoriesToAlwaysCook=ClearArray\n!MapsToCook=ClearArray\n'
cfg+='\n'.join(f'+DirectoriesToAlwaysCook=(Path="{d}")' for d in sorted(dirs))
cfg+='\n+MapsToCook=(FilePath="/Engine/Maps/Entry")\nbCookAll=False\nbCookMapsOnly=False\n'
(H/'Config/DefaultGame.ini').write_text(cfg,encoding='utf-8-sig')
engine=(R/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
engine+='\n[/Script/EngineSettings.GameMapsSettings]\nGameDefaultMap=/Engine/Maps/Entry\nServerDefaultMap=/Engine/Maps/Entry\n'
(H/'Config/DefaultEngine.ini').write_text(engine,encoding='utf-8-sig')
(O/'package-scope.json').write_text(json.dumps({'scope':'hammer-specific Development package, not full-game release','source_project':str(R),'host':str(H),'maps':['/Engine/Maps/Entry'],'cook_directories':sorted(dirs),'production_configs_changed':False},indent=2),encoding='utf-8')
print('Prepared isolated package scope:',len(dirs),'cook directories')
