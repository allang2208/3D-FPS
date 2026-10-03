"""Save M07 authored navigation and final gameplay receipt without starting PIE."""
from pathlib import Path

source = Path('D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/import_gameplay.py')
namespace = {'__name__': 'm07_gameplay_navigation_production', 'M07_EXECUTION_MODE': 'existing_editor_batch_bridge'}
exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), namespace)
