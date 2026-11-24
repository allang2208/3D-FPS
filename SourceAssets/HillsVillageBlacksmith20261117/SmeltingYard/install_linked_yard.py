"""Publish only the linked smith canopy, PCG soil mask, and local removals in the active level."""
from pathlib import Path
import sys
import runpy
import hashlib
import json
import unreal as u

here=Path(__file__).resolve().parent
root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
tools=root/'Tools/WorldGeneration/AbandonedVillage'
sys.path.insert(0,str(tools))
from smith_yard_clearance import clear_yard
from smith_yard_states import build as build_yard_states
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
disk=root/'Content'/(level.removeprefix('/Game/')+'.umap')
runpy.run_path(str(here/'import_canopy.py'),run_name='__main__')
runpy.run_path(str(tools/'save_village_wear.py'),run_name='__main__')
original=hashlib.sha256(disk.read_bytes()).digest()
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Could not open '+level)
removed=clear_yard(world)
if build_yard_states(world) or removed:
    if hashlib.sha256(disk.read_bytes()).digest()!=original:
        raise RuntimeError('Village changed while editing the yard. Rerun against the latest saved map.')
    if not u.EditorLoadingAndSavingUtils.save_map(world,level):
        raise RuntimeError('Could not save '+level)
u.log('SMITH_LINKED_YARD_PUBLISHED '+json.dumps(removed))
