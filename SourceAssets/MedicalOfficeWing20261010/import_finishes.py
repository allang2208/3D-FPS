import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('import_assets.py')),init_globals={'GEOMETRY_ONLY':True,'IMPORT_KINDS':{'FloorFinish','FloorWayfinding','CeilingGrid','Tiles','Signs'}})
