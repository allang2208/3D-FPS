"""Single-process, scoped import and publication entry; never starts PIE."""
from pathlib import Path
import runpy
root=Path(__file__).resolve().parent
if (root/'RefinementV4/installed.json').exists():
 runpy.run_path(str(root/'RefinementV4/publish.py'),run_name='__main__')
 raise SystemExit(0)
if (root/'RefinementV3/installed.json').exists():
 runpy.run_path(str(root/'RefinementV3/publish.py'),run_name='__main__')
 raise SystemExit(0)
if (root/'RefinementV2/installed.json').exists():
 runpy.run_path(str(root/'RefinementV2/publish.py'),run_name='__main__')
 raise SystemExit(0)
runpy.run_path(str(root/'import_assets.py'),run_name='__main__')
runpy.run_path(str(root/'install_level.py'),run_name='__main__')
