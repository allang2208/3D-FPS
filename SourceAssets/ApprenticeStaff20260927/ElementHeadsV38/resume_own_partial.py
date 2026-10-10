"""Resume only the unsaved material created by this batch's first failed call."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('install_ue.py')),
    init_globals={'OWNED_INCOMPLETE_ASSETS':{
        '/Game/Weapons/ApprenticeStaff20260927/ElementHeadsV38/Materials/M_StaffCraft_StormInner_V38'}})
