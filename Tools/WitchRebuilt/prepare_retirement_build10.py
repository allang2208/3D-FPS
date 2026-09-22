"""Capture retirement dependencies, then normally exit a clean editor for the build."""
from pathlib import Path
folder=Path(__file__).parent
for name in ('read_retirement10_inputs.py','close_for_build.py'):
 p=folder/name
 exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p)})
