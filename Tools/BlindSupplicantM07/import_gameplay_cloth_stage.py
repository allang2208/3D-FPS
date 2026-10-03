"""Save M07 multi-section gill production in the already running editor."""
from pathlib import Path

source = Path('D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/import_gameplay.py')
namespace = {
    '__name__': 'm07_gameplay_cloth_production',
    'M07_EXECUTION_MODE': 'existing_editor_batch_bridge',
    'M07_GAMEPLAY_STOP_AFTER': 'interacting_gills',
}
try:
    exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), namespace)
except Exception as error:
    if error.__class__.__name__ != 'M07GameplaySavedStage':
        raise
