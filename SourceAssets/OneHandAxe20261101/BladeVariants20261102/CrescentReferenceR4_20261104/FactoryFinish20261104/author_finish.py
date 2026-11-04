"""Current production entry: preserve R4 geometry and author its factory-sourced finish."""
from pathlib import Path
import runpy,subprocess
P=Path(__file__).resolve().parent
runpy.run_path(str(P/'extract_surface.py'),run_name='__main__')
subprocess.run(['py','-3.11',str(P/'transfer_textures.py')],check=True)
runpy.run_path(str(P/'apply_source.py'),run_name='__main__')
