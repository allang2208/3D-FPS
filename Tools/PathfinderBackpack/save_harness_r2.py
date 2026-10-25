import os,runpy
runpy.run_path('D:/FPS3D/FPSGAME/Tools/PathfinderBackpack/save_assets.py',
              init_globals={'SAVE_STAGE':'harness','SAVE_MAX_HARNESSES':12 if os.environ.get('PATHFINDER_NEW_ASSETS_ONLY')=='1' else 2},run_name='__main__')
