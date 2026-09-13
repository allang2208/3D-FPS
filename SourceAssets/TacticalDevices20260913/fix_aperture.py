from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('brighten_laser.py')), init_globals={'APERTURE_ONLY': True})
