"""Publish the current bedroom assets into the existing apartment."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent.parent
sys.modules.pop('design',None)
sys.modules.pop('placements',None)
runpy.run_path(str(ROOT/'RefinementV3/publish.py'),run_name='__main__')
