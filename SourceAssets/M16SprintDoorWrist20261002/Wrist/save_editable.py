"""Save the copied common wrist bind as an editable native M16 Blender source."""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/save_bare_family_blends.py', init_globals={
    'AUTHOR_ROOT': str(HERE), 'NATIVE_SOURCE_ROOT': str(HERE / 'NativeSources'),
    'FAMILY_VERSION': 'V7CommonM4Wrist20261002',
})
