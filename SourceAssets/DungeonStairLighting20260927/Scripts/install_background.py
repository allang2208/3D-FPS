"""Commandlet entry for the same scoped asset save, without opening the editor."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('install.py')),run_name='__main__',init_globals={'BACKGROUND':True})
