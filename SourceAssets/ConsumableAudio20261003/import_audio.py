"""Import and save the four consumable sounds in a headless UE commandlet."""
from pathlib import Path
import json
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError("Stop the active PIE session before importing consumable sounds; no asset was changed.")

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "SourceAssets/ConsumableAudio20261003"
manifest = json.loads((OUT / "audio_manifest.json").read_text(encoding="utf-8"))
destination = manifest["destination"]
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
assets.make_directory(destination)
tools = unreal.AssetToolsHelpers.get_asset_tools()
receipt = {"saved": False, "assets": []}
for entry in manifest["recordings"]:
    task = unreal.AssetImportTask()
    task.filename = entry["wav"]
    task.destination_path = destination
    task.destination_name = entry["asset_name"]
    task.automated = True
    task.replace_existing = True
    task.save = False
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError("Consumable audio import failed: " + entry["asset_name"])
    sound = unreal.load_asset(task.imported_object_paths[0])
    sound.set_editor_property("looping", False)
    sound.set_editor_property("loading_behavior", unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not assets.save_loaded_asset(sound, False):
        raise RuntimeError("Consumable audio save failed: " + entry["asset_name"])
    receipt["assets"].append({"path": sound.get_path_name(), "source": entry["source"], "duration_seconds": entry["duration_seconds"]})
    unreal.log("CONSUMABLE_AUDIO_SAVED " + sound.get_path_name())
receipt["saved"] = True
(OUT / "import_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log("CONSUMABLE_AUDIO_IMPORT_COMPLETE count=" + str(len(receipt["assets"])))
