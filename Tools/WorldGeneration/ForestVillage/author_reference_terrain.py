"""Bake the common ground and regenerate closed pools on the current authored terrain."""
import json,os
from pathlib import Path
import unreal as u
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
target='/Game/GameMaps/L_ForestPathVillage'
world=u.EditorLoadingAndSavingUtils.load_map(target)
region=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.ForestVillageRegion))
mat=u.load_asset('/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference')
if not mat or not region.bake_reference_surface(str(src),mat): raise RuntimeError('Reference ground bake failed')
if not region.bake_woodland_pools(str(src/'Grass'),237855): raise RuntimeError('No viable forest pool layout')
tiles=[c for c in region.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('SM_ForestGround_')]
bindings={c.get_name():[c.static_mesh.get_path_name(),c.get_material(0).get_path_name()] for c in tiles}
if not bindings or any(m!=mat.get_path_name() for _,m in bindings.values()): raise RuntimeError('Unexpected ground material/override '+str(bindings))
if not u.EditorLoadingAndSavingUtils.save_map(world,target): raise RuntimeError('Map save failed')
(batch/'terrain.json').write_text(json.dumps(bindings,indent=2))
