"""Editor integration: register copied sources and record source animation contracts.
No PIE, rendering, gameplay validation or modification of existing animations.
"""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
configuration = json.loads((root / "Content/ColdSteelData/player_body.json").read_text(encoding="utf-8"))
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(["/Game/Characters/Mannequins/Anims"], force_rescan=True)
sources = []
for key, path in configuration["clips"].items():
    clip = unreal.load_asset(path)
    if not clip:
        raise RuntimeError("Cannot load template clip: " + path)
    sources.append({"key": key, "path": path, "seconds": clip.get_play_length(), "additive": str(clip.get_editor_property("additive_anim_type")), "frames": unreal.AnimationLibrary.get_num_frames(clip)})
(root / "SourceAssets/PlayerBody20260921/animation_sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
print(json.dumps({"registered": len(sources), "action_sources": [s for s in sources if s["key"].endswith(("Reload", "Equip"))], "project": str(root)}))
