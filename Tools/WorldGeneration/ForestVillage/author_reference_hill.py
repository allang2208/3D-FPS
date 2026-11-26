"""Bake the complete authored hill, the settlement cutout and the matching PCG into a private host."""
import json
import os
from pathlib import Path
import unreal as u

directory=Path(os.environ['FPS_REFERENCE_HILL_SOURCE'])
batch=Path(os.environ['FPS_REFERENCE_HILL_BATCH'])
site=json.loads((directory/'hill.json').read_text())
target='/Game/GameMaps/L_ForestPathVillage'
sample='/Game/ForestPathStudy/VillageRegion/SurfaceSample/'
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:
    raise RuntimeError('Cannot open the village map for authoring')
scene=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
region=next(a for a in scene if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(target+'.'))
templates=[c for a in scene if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name()
           for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
if not region.install_hill_site(str(directory),u.IntPoint(*site['site_min_m']),site['village_datum_cm']):
    raise RuntimeError('Cannot install the surveyed settlement and its height corrections')
if not region.bake_ground(str(directory)):
    raise RuntimeError('Cannot bake the hill and its collision tiles')
materials=[u.load_asset(sample+n) for n in ('M_ForestVillageSurface','MI_ForestVillageFringe','M_ForestVillageGateApron')]
if not region.apply_surface_sample(str(directory),*materials):
    raise RuntimeError('Cannot bake the hill surface layers')
cover=directory/'Grass'
if not region.bake_vegetation(str(cover/'planting.bin'),templates):
    raise RuntimeError('Woodland PCG generation did not finish')
if not region.install_grass_cover(str(cover/'near_grass.u8')):
    raise RuntimeError('Cannot install the near grass cells')
if not u.EditorLoadingAndSavingUtils.save_map(world,target):
    raise RuntimeError('Cannot save the village and mountain map')
(batch/'baked.json').write_text(json.dumps(dict(map=target,site=site,grass=json.loads((cover/'generation.json').read_text())),indent=2),encoding='utf8')

