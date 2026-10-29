import runpy
from pathlib import Path
for label in ('jason','kaitlin'):
    runpy.run_path(str(Path(__file__).with_name('save_assets.py')),init_globals={'BODY_LABEL':label})
