"""Rebuild only the user-requested refinement groups into distinct V2 assets."""
import runpy
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
out=ROOT/'Authored'
subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe','-X','utf8','-c',
    'import runpy;runpy.run_path('+repr(str(HALL/'Scripts/author_labels.py'))+',init_globals={"EXPORT_OUT":'+repr(str(out))+'})'],check=True)
runpy.run_path(str(HALL/'Scripts/author_station.py'),init_globals=dict(EXPORT_OUT=out,EXPORT_SUFFIX='_V2',EXPORT_REVISION='flue_gas_controls_pipes_rails_v2_20261001',
    EXPORT_KINDS={'WetPipework','GasDucts','Exhaust','Instruments','PipeCouplings','Valves','ControlPanel','ControlHardware',
        'Signs','FloorMarkings','Railings','StairRails'}))
