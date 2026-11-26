"""Build the saved sample materials for the editor's active rendering platform."""
import json
import os
from pathlib import Path
import unreal as u

from_folder='/Game/ForestPathStudy/VillageRegion/SurfaceSample/'
compiled=[]
for name in ('M_ForestVillageSurface','M_ForestVillageFringe','M_ForestVillageGateApron'):
    mat=u.load_asset(from_folder+name)
    if not mat: raise RuntimeError('Missing '+name)
    errors=u.MaterialEditingLibrary.recompile_material(mat)
    if errors: raise RuntimeError(name+' '+str(errors))
    u.MaterialEditingLibrary.get_statistics(mat)  # Wait for the material's shader jobs.
    if not u.EditorAssetLibrary.save_loaded_asset(mat,False): raise RuntimeError('Save '+name)
    compiled.append(name)
edge=u.load_asset(from_folder+'MI_ForestVillageFringe')
u.MaterialEditingLibrary.update_material_instance(edge)
if not u.EditorAssetLibrary.save_loaded_asset(edge,False): raise RuntimeError('Save fringe instance')
compiled.append(edge.get_name())
(Path(os.environ['FPS_FOREST_VILLAGE_BATCH'])/'compiled.json').write_text(json.dumps(compiled,indent=2))
