"""MCP entry for a scoped kitchen installation; fresh Python module globals."""
from pathlib import Path
import runpy,sys
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
runpy.run_path(str(R/'install_level.py'),run_name='__main__')
