from pathlib import Path
import runpy
for name in ('install.py','compile_materials.py'):
    runpy.run_path(str(Path(__file__).parent/name),run_name='__main__')
