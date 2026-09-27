"""Headless import and publication of the expanded palm coverage; no previews or tests."""
import runpy

runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/import_fingerless_root_coverage.py',
               init_globals=dict(SAVE_LIMIT=0))
runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/publish_fingerless_root_coverage.py')
