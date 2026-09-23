import os
from pathlib import Path
source=Path(__file__).with_name('import_meshes.py')
os.environ['DUNGEON_SLIME_FLUID_ONLY']='1'
try:exec(compile(source.read_text(),str(source),'exec'),globals())
finally:os.environ.pop('DUNGEON_SLIME_FLUID_ONLY',None)
