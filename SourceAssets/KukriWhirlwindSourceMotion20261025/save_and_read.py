"""Save and inspect only the new V7 packages in one background UE batch."""
from pathlib import Path
import runpy
folder=Path(__file__).resolve().parent
runpy.run_path(str(folder/'save_assets.py'),run_name='__main__')
runpy.run_path(str(folder/'read_saved.py'),run_name='__main__')
