"""Use the bounded saved-asset writer for the scoped glove wrist repair."""
import os,runpy
from pathlib import Path
T=Path(__file__).parent;key='TS01_SHIRT_SAVE_PLAN';old=os.environ.get(key)
os.environ[key]='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1/gloves-authored.json'
try:runpy.run_path(str(T/'combat3_save.py'),run_name='__main__')
finally:
    if old is None:os.environ.pop(key,None)
    else:os.environ[key]=old
