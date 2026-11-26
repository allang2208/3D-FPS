"""Author the Forest Path Village persistent level. Save only the new world."""
from pathlib import Path
import hashlib
import json
import os
import unreal as u

target = "/Game/GameMaps/L_ForestPathVillage"
forest = "/Game/ForestPathStudy/Maps/L_ForestPathForest"
batch = Path(os.environ["FPS_FOREST_VILLAGE_BATCH"])
root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
target_file = root / "Content/GameMaps/L_ForestPathVillage.umap"
ticket = batch / "authoring.json"

# Retrying a partial authoring batch must not overwrite a subsequently edited level.
if target_file.exists():
    if not ticket.exists() or json.loads(ticket.read_text())["partial_sha256"] != hashlib.sha256(target_file.read_bytes()).hexdigest():
        raise RuntimeError("Destination map already exists outside this partial batch")

level = u.EditorLoadingAndSavingUtils.new_blank_map(False)
if not level:
    raise RuntimeError("Could not create the persistent level")
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
settings = level.get_world_settings()
settings.set_editor_property("default_game_mode", u.TemperateHillsGameMode.static_class())
world_owner = actors.spawn_actor_from_class(u.TemperateHillsWorld, u.Vector())
world_owner.set_actor_label("Forest village gameplay")
world_owner.set_editor_property("tags", [u.Name("ForestPathVillage")])
assets = u.load_asset("/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming")
if not assets:
    raise RuntimeError("Village gameplay asset data is unavailable")
world_owner.set_editor_property("assets", assets)
world_owner.set_editor_property("size_meters", 1024.0)

if not u.EditorLoadingAndSavingUtils.save_map(level, target):
    raise RuntimeError("Could not allocate the destination level")
ticket.write_text(json.dumps({"partial_sha256":hashlib.sha256(target_file.read_bytes()).hexdigest()}))
if not u.HillsNavigationSystem.install_on_map(level):
    raise RuntimeError("Could not install village navigation")
# Keep every authored Landscape vertex, painted layer, forest instance, decal and
# foreground actor in the original package and at its original absolute transform.
forest_stream = u.EditorLevelUtils.add_level_to_world(level, forest, u.LevelStreamingAlwaysLoaded)
if not forest_stream:
    raise RuntimeError("Could not attach the authored forest")
if not u.EditorLoadingAndSavingUtils.save_map(level, target):
    raise RuntimeError("Could not save the forest village world")
receipt = {
    "map":target, "forest_sublevel":forest, "forest_transform":"identity",
    "settlement_sublevel":"/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage",
    "east_gate_cm":[-10800,25800], "forest_start_cm":[-10775,25130],
    "save_slot":"ForestPathVillage_World",
    "map_sha256":hashlib.sha256(target_file.read_bytes()).hexdigest(),
    "map_bytes":target_file.stat().st_size,
}
(batch / "published.json").write_text(json.dumps(receipt, indent=2))
print("FOREST_VILLAGE_PUBLISHED",target)
