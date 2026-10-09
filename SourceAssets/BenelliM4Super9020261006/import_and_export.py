import runpy
from pathlib import Path
p=Path(__file__).parent
runpy.run_path(str(p/'import_super90.py'),run_name='__main__')
runpy.run_path(str(p/'export_equipment_sources.py'),run_name='__main__')
