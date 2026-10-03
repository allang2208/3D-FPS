"""The user's requested scoped source inspection for five empty-reload branches."""
import sys,runpy
from pathlib import Path
O=Path(__file__).parent
for family in ['base','vertical','canted','prism','angled']:
 sys.argv=['sequence.py','--',family]+([] if family=='base' else ['--geometry-only'])
 runpy.run_path(str(O/'sequence.py'),run_name='__main__')
