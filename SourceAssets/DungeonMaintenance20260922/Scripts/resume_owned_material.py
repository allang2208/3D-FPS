import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('install.py')),run_name='__main__',init_globals={
    'MAINTENANCE_RESUME_ASSETS':['/Game/Dungeons/AtmosphereV2/Maintenance/Materials/M_Maintenance_Enamel']})
