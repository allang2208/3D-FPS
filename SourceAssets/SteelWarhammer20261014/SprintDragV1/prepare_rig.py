import runpy
from pathlib import Path
P=Path(__file__).resolve().parent
runpy.run_path(str(P.parent/'author_warhammer.py'),init_globals={'WARHAMMER_AUTHOR_ROOT':str(P/'RigSource')})
