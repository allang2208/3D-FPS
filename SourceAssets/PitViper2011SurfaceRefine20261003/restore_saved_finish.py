"""Restore the saved 2011 surface contract after weapon/accessory reimport."""
import importlib.util
from pathlib import Path
import unreal as u
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('pv_surface_contract',O/'surface_contract.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
C.restore_saved(u)
