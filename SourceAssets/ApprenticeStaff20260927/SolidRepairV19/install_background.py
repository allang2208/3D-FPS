from pathlib import Path
import runpy
root=Path(__file__).resolve().parent
runpy.run_path(str(root/'import_model.py'),run_name='__main__')
runpy.run_path(str(root/'export_ue_after.py'),run_name='__main__')
