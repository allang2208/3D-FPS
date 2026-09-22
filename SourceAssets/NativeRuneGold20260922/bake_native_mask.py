"""Current native-mask entry point, including the guard-root inscriptions.
The original blade-only recipe is preserved in RuneSwordVisualPolish20260922/Before.
"""
from pathlib import Path
import runpy
revision=Path(__file__).resolve().parent.parent/'RuneSwordVisualPolish20260922'
runpy.run_path(str(revision/'bake_root_correction.py'),run_name='__main__')