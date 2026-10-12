"""Read the configured regression assets, then save independent recovery assets."""
from pathlib import Path
root = Path('D:/FPS3D/FPSGAME/Tools/PlayerBody')
for name in ('read_melee_regression20261010.py', 'save_melee_recovery20261010.py'):
    path = root/name
    exec(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec'), {'__file__': str(path), '__name__': '__main__'})
