"""One locked authoring batch: save the grip, its materials and its UI icon."""
import runpy
from pathlib import Path
O=Path(__file__).parent
runpy.run_path(str(O/'import_assets.py'),run_name='__main__')
runpy.run_path(str(O/'install_icons.py'),run_name='__main__')
print('RSH_QUICKDRAW_GRIP_IMPORT_COMPLETE',flush=True)
