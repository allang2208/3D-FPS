"""One mutex-protected project-bridge call for the component asset and map writes."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
for script in ('import_components.py','install_components.py'):
    print('WORKSHOP_COMPONENT_INSTALL_STAGE '+script)
    runpy.run_path(str(ROOT/'Scripts'/script),run_name='__main__')
