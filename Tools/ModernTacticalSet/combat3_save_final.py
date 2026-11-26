"""Select the complete plan explicitly in both commandlet and existing editor."""
import os,runpy
previous=os.environ.get('TS01_SHIRT_SAVE_PLAN')
try:
    os.environ['TS01_SHIRT_SAVE_PLAN']='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/authored.json'
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/combat3_save.py',run_name='__main__')
finally:
    if previous is None:os.environ.pop('TS01_SHIRT_SAVE_PLAN',None)
    else:os.environ['TS01_SHIRT_SAVE_PLAN']=previous
