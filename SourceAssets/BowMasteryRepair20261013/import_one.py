"""Serialized bridge entry: only import this turn's corrected bow icon."""
import os
import runpy
key='FPS_SKILL_ICON_IMPORT_ONLY'
before=os.environ.get(key)
try:
    os.environ[key]='bowMastery'
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/UI/import_unified_skill_icons.py',run_name='__main__')
finally:
    if before is None:os.environ.pop(key,None)
    else:os.environ[key]=before
