from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
for script in ('read_inputs.py','import_finish.py','install_finish.py'):
    print('WORKSHOP_SURFACE_INSTALL_STAGE '+script)
    runpy.run_path(str(ROOT/'Scripts'/script),run_name='__main__')
