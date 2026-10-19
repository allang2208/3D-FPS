"""Deploy the current approved-master icons; procedural V1 frames are retired."""
import runpy
from pathlib import Path
P=Path(__file__).resolve().parent
runpy.run_path(str(P/'CommonModsV2/deploy_icons.py'),run_name='__main__')
