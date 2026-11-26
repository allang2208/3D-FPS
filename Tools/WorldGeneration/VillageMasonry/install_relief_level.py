"""Install the native bakery wall bays and the courtyard relief overrides in one map save."""
from pathlib import Path
import runpy
import unreal as ue

HERE = Path(__file__).resolve().parent

master = ue.load_asset('/Game/WorldGeneration/TemperateHills/VillageMasonry/Relief/M_VillageRelief_Triplanar')
if not master or not all(master.get_editor_property(usage) for usage in
                         ('used_with_instanced_static_meshes', 'used_with_nanite')):
    raise RuntimeError('Village masonry needs both instanced and Nanite material permutations')

# The shared installer backs up the latest map, edits the two component groups and
# checks that the source has not changed before publishing a single level package.
runpy.run_path(str(HERE / 'save_courtyards_and_bakery.py'), run_name='__main__')
