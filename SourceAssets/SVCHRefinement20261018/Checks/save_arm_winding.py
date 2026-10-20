from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('save_clean_topology.py')),
              init_globals={'SOURCE_REVISION':'R3','TARGET_REVISION':'R4','RECEIPT':'arm_winding_save.json'})
