"""Match the existing flue penetration to the house's mortar; no assembly rebuild."""
import json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/WindowR7'
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve active PIE or unsaved map')
backup=OUT/'BeforeInfill.umap'
if not backup.exists():shutil.copy2(ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap',backup)
world=u.EditorLoadingAndSavingUtils.load_map(level)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
shop=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Village_Blacksmith_Common')
components=[c for c in shop.get_components_by_class(u.StaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_SmithLoft_FlueInfill']
if len(components)!=1:raise RuntimeError('Expected one owned flue penetration')
material=u.load_asset('/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A')
if not material:raise RuntimeError('Native house mortar unavailable')
shop.modify()
for c in components:c.modify();c.set_material(0,material)
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Save village')
(OUT/'infill-saved.json').write_text(json.dumps({'map':level,'components_changed':1,'material':material.get_path_name(),'geometry_changed':False},indent=2))
u.log('SMITH_CHIMNEY_INFILL_SAVED components=1')
