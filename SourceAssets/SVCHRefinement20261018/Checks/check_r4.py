from pathlib import Path
import runpy
O=Path(__file__).parent
for script in ('save_fine_finish.py','check_saved_assets.py','read_arm_surface.py'):
    runpy.run_path(str(O/script))
