"""Current head-thrust authoring uses the corrected sword arm donor."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'author_head_thrust.py'),run_name='__main__')