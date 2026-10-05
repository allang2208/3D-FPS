"""Restore retained dependencies and the V9 prototype. V9 is rejected-pending-rework."""
import runpy
from pathlib import Path
root=Path(__file__).resolve().parent
runpy.run_path(str(root/'install_ue.py'),run_name='__main__')
runpy.run_path(str(root/'VisibilityV5/install_ue.py'),run_name='__main__')
runpy.run_path(str(root/'CoherentV9/install_ue.py'),run_name='__main__')
