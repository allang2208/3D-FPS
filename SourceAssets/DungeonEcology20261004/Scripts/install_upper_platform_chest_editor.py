from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('install_upper_platform_chest.py')),
    init_globals={'ECOLOGY_EDITOR_BATCH':True},run_name='__main__')
