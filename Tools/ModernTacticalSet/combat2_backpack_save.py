"""Execute the standard scoped backpack asset producer in this asset host."""
import os,runpy
os.environ['BACKPACK_FIT_RUN_DIR']='D:/FPS3D/FPSGAME/SourceAssets/BackpackFit20261024/ModernTacticalShirtR220261114'
os.environ['BACKPACK_FIT_SHIRT']='ue_modern_kevlar_vest'
os.environ['BACKPACK_FIT_NEW_ASSETS_ONLY']='1'
runpy.run_path('D:/FPS3D/FPSGAME/Tools/BackpackFit/save_assets.py',run_name='__main__')
