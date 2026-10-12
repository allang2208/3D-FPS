"""Targeted compressed-asset and final-pose comparison for the reported attack."""
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/Tools/PlayerBody')
for name in ('read_dash_assets20261010.py','capture_dash_graph20261010.py'):
    p=root/name
    exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
