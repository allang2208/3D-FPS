"""Bounded live-editor save batch for the expanded palm coverage, without pose changes."""
import json,runpy
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
dest='/Game/Characters/ModularOutfit20260924/FingerlessHuntV2'
targets={f'{dest}/{row["profile"]}/SK_{row["profile"]}_{suffix}'
         for row in json.loads((R/'manifest.json').read_text())
         for suffix in ('FingerlessHuntV2','FingerlessSkin')}
dirty={package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets & dirty:
    raise RuntimeError('Glove assets already have unsaved editor changes: '+str(sorted(targets & dirty)))
runpy.run_path(str(P/'Tools/ModularOutfit/import_fingerless_hunt_v2.py'),
               init_globals=dict(MESHES_ONLY=True,MAX_SAVES=globals().get('SAVE_LIMIT',4)))
runpy.run_path(str(P/'Tools/ModularOutfit/import_fingerless_skin_companions.py'),
               init_globals=dict(MAX_SAVES=globals().get('SAVE_LIMIT',4)))
gloves=json.loads((R/'asset-receipt.json').read_text())
skin=json.loads((R/'SkinCoverage/asset-receipt.json').read_text())
print('ROOT_COVERAGE_SAVE_PROGRESS',len(gloves['profiles']),len(skin['profiles']),flush=True)
