"""Install the user's table / original lamp / work mat selection."""
from pathlib import Path
WORKBENCH_REVISION='GunWorkbenchCleared20260928'
script=Path('D:/FPS3D/FPSGAME/Tools/GunWorkbench/import_original_lamp.py')
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'))
