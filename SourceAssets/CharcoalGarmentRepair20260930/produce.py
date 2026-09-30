"""Offline authoring recipe; publishing is a separate explicit step."""
import runpy,sys
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from author import body,traversal
from finish import finish
body();traversal();finish(profiles=['Body'])
from trim_edges import trim
trim()
from body_exposed_skin import build
build()
runpy.run_path(str(R/'export.py'),run_name='__main__')
