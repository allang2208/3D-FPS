"""Finish paired body variants and inventory production after wrist tailoring."""
import runpy
from pathlib import Path
T=Path(__file__).parent
for name in ['combat3_cuff_tailor_world.py','combat3_cuff_assemble.py']:
    runpy.run_path(str(T/name),run_name='__main__')
