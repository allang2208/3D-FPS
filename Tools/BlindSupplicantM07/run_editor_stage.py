"""One saved M07 production stage through the existing editor batch bridge."""
from pathlib import Path
stage=globals().get('M07_REQUESTED_STAGE')
scope={'__name__':'m07_authoring','M07_EXECUTION_MODE':'existing_editor_batch'}
if stage:scope['M07_STOP_AFTER']=stage
script=Path('D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/import_assets.py')
try:
    exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),scope)
except Exception as exc:
    saved_stage=scope.get('M07SavedStage')
    if saved_stage is None or not isinstance(exc,saved_stage):raise
    print('M07 production stage saved: '+str(exc))
