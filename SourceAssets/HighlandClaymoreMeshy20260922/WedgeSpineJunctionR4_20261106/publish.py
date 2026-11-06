"""Install the refined junction and its texture/icon source using stable paths."""
from pathlib import Path
import runpy

P=Path(__file__).resolve().parent
runpy.run_path(str(P.parent/'WedgeSpine20261105/publish.py'),init_globals={'AUTHOR_FOLDER':P})
print('RIDGE_JUNCTION_R4_SAVED')
