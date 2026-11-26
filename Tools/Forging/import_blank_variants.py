"""Import current author_blank_variants.py outputs and install saved profiles.

The 2026-10-15 source/assets remain available as the previous version. Current
outputs use the compact hammer revision and its dedicated readable guide.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name('import_hammer_refinement.py')), run_name='__main__')
