"""Promote the user-accepted V24 opening and V25 reverse recover."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'IntegratedV30/save_editable.py'),run_name='__main__')
