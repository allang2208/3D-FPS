"""Active hollow-grip production entrypoint; V1 source remains in Before."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'HollowV2'/'author_hollow.py'),run_name='__main__')
