"""Regenerate and save the production hill's forest graph with the original canopy templates."""
import json,os
from pathlib import Path
import runpy
import unreal as u
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
target='/Game/GameMaps/L_ForestPathVillage'
world=u.EditorLoadingAndSavingUtils.load_map(target)
scene=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
region=next(a for a in scene if isinstance(a,u.ForestVillageRegion))
templates=[c for a in scene if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name() for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
if not region.bake_vegetation(str(src/'Grass'/'planting.bin'),templates): raise RuntimeError('PCG generation incomplete')
if not region.install_grass_cover(str(src/'Grass'/'near_grass.u8')): raise RuntimeError('Near cover failed')
if u.EditorAssetLibrary.does_asset_exist('/Game/ForestPathStudy/VillageRegion/FarGrass/M_HillsFarGrass'):
    far=runpy.run_path(str(Path(__file__).with_name('author_grass_distance.py')))
    (batch/'cover-far.json').write_text(json.dumps(far['rebuild'](world,region),indent=2))
if not u.EditorLoadingAndSavingUtils.save_map(world,target): raise RuntimeError('Map save failed')
counts={}
for c in region.get_components_by_class(u.InstancedStaticMeshComponent):
    key=c.static_mesh.get_name()
    counts[key]=counts.get(key,0)+c.get_instance_count()
(batch/'woodland.json').write_text(json.dumps(counts,indent=2))
if (src/'quarry.json').exists():
    trees={}
    for c in region.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=c.static_mesh
        if not mesh or not mesh.get_name().startswith(('SM_EuropeanHornbeam_Forest','SM_CommonHazel_Forest')):continue
        trees[mesh.get_name()]=dict(lods=mesh.get_num_lods(),
            nanite=mesh.get_editor_property('nanite_settings').get_editor_property('enabled'),
            wind_end_cm=c.get_editor_property('world_position_offset_disable_distance'),
            cull_end_cm=c.get_editor_property('instance_end_cull_distance'),
            ray_tracing=c.get_editor_property('visible_in_ray_tracing'))
    (batch/'tree-lods.json').write_text(json.dumps(trees,indent=2))
