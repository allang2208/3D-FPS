from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parent
for script in ('import_tools.py','install_tools.py'):
    print('FAB_WORKSHOP_STAGE '+script)
    runpy.run_path(str(ROOT/script),run_name='__main__')
