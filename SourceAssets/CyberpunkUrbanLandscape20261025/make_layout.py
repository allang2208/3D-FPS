"""Active urban layout: riverfront-gap placement from the user's screenshot."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'layout_riverfront.py'),run_name='__main__')
