import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name('create_subject.py')),
              init_globals={'INCINERATOR_LINE_EXISTING_EDITOR': True})
