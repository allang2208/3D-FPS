from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('install.py')),run_name='__main__',init_globals={
    'SERVICES_SKIP_MATERIALS':True,'SERVICES_MESH_NAMES':['SM_Services_CableTrays','SM_Services_HangingCables']})
