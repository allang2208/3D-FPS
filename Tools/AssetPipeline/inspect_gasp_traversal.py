"""Run in the downloaded official sample; inspect traversal assets without editing them."""
import json
from pathlib import Path

import unreal

OUTPUT = Path("D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910")
OUTPUT.mkdir(parents=True, exist_ok=True)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
rows = []
for asset in registry.get_assets_by_path("/Game", recursive=True):
    name = str(asset.asset_name)
    path = str(asset.package_name)
    cls = str(asset.asset_class_path.asset_name)
    if not any(term in path.lower() for term in ("travers", "vault", "mantle", "climb", "hurdle")):
        continue
    row = {"path": path, "class": cls}
    if cls in ("AnimSequence", "AnimMontage"):
        obj = asset.get_asset()
        row["duration"] = obj.get_play_length()
        skeleton = obj.get_editor_property("skeleton")
        row["skeleton"] = skeleton.get_path_name() if skeleton else None
        if cls == "AnimSequence":
            row["keys"] = obj.get_editor_property("number_of_sampled_keys")
            row["root_motion"] = obj.get_editor_property("enable_root_motion")
        lib = unreal.AnimationLibrary
        row["notifies"] = [
            {"event": str(n), "time": lib.get_anim_notify_event_trigger_time(n),
             "duration": lib.get_anim_notify_event_duration(n)}
            for n in lib.get_animation_notify_events(obj)
        ]
    rows.append(row)
(OUTPUT / "official_sample_inventory.json").write_text(
    json.dumps({"project_directory": unreal.Paths.project_dir(), "assets": rows}, indent=2),
    encoding="utf-8",
)
unreal.log("GASP_TRAVERSAL_INVENTORY_COMPLETE assets=" + str(len(rows)))
