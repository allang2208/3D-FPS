import runpy
from pathlib import Path
S=Path(__file__).resolve().parent.parent
for folder in ('M4TacticalSprint20260915','RifleTacticalSprint20260915'):
    runpy.run_path(str(S/folder/'import_sprint.py'),run_name='__main__')
