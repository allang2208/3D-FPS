"""Saiga 12K / SVCh production batch using the shared assembly pipeline.

Blender: --python this_file -- prepare (or author).
UE Python: runpy.run_path(this_file, init_globals={'ASSEMBLY_STAGE': 'export' or 'import'}).
"""
import runpy
import sys
from pathlib import Path

project = Path('D:/FPS3D/FPSGAME')
root = project/'SourceAssets/GunAssemblyExpansion20261025'
stage = globals().get('ASSEMBLY_STAGE')
if stage is None:
    stage = sys.argv[sys.argv.index('--')+1]
scripts = {'export': 'export_missing_assembly_sources.py', 'prepare': 'prepare_missing_assembly_sources.py',
           'author': 'author_missing_assembly.py', 'import': 'import_missing_assembly.py'}
runpy.run_path(str(project/'Tools/GunWorkbench'/scripts[stage]), init_globals={
    'ASSEMBLY_ROOT': root, 'ASSEMBLY_WEAPONS': [('saiga12k', 'Saiga12K'), ('svch', 'SVCH')]})
