"""Read the shared hammer animation assets; never start or change gameplay."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path("D:/FPS3D/FPSGAME")
OUT = ROOT / "SourceAssets/RuneboundWarhammer20261022/ThirdPersonRouting20261023"
config_file = ROOT / "Content/ColdSteelData/player_body.json"
config_bytes = config_file.read_bytes()
config = json.loads(config_bytes.decode("utf-8-sig"))
items = json.loads((ROOT / "Content/ColdSteelData/items.json").read_text(encoding="utf-8-sig"))
roles = {k: v for k, v in config["clips"].items() if k.startswith("Warhammer.")}
body = u.load_asset(config["body_mesh"])
body_skeleton = body.get_editor_property("skeleton") if body else None
assets = {}
for path in sorted(set(roles.values())):
    disk_file = ROOT / "Content" / (path.removeprefix("/Game/").split(".")[0] + ".uasset")
    asset = u.load_asset(path)
    row = {"saved_file_exists": disk_file.is_file(), "loaded": bool(asset)}
    if asset:
        skeleton = asset.get_editor_property("skeleton")
        row.update(
            seconds=asset.get_play_length(),
            skeleton=skeleton.get_path_name() if skeleton else None,
            body_skeleton_matches=skeleton == body_skeleton,
            markers={str(m.marker_name): m.time for m in u.AnimationLibrary.get_animation_sync_markers(asset)},
        )
    assets[path] = row

identity_keys = ("tool_kind", "isTwoHanded", "tool_viewmodel", "viewmodel_mesh", "tool_animation_prefix", "tool_scale")
weapon_data = {}
for key, catalog_file in (("ue_steel_warhammer", "warhammer-modules.json"), ("ue_runebound_warhammer", "runebound-warhammer-modules.json")):
    item = items[key]
    catalog = json.loads((ROOT / "Content/ColdSteelData" / catalog_file).read_text(encoding="utf-8-sig"))
    weapon_data[key] = {
        "identity": {field: item.get(field) for field in identity_keys},
        "module_catalog": catalog_file,
        "arms_mesh": catalog["arms_mesh"],
        "drive_bone": catalog["drive_bone"],
        "bone_mount": catalog["bone_mount"],
        "factory_modules": {slot: catalog["slots"][slot]["factory"] for slot in catalog["module_slots"]},
    }

report = {
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Requested third-person source-routing and saved-asset investigation; no game or visual acceptance",
    "player_body_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
    "body_mesh": config["body_mesh"],
    "body_loaded": bool(body),
    "body_skeleton": body_skeleton.get_path_name() if body_skeleton else None,
    "roles": roles,
    "assets": assets,
    "weapons": weapon_data,
    "gameplay_started": False,
    "assets_modified": False,
}
report["summary"] = {
    "role_count": len(roles),
    "unique_asset_count": len(assets),
    "missing_saved_files": [p for p, r in assets.items() if not r["saved_file_exists"]],
    "failed_loads": [p for p, r in assets.items() if not r["loaded"]],
    "incompatible_skeletons": [p for p, r in assets.items() if r.get("loaded") and not r["body_skeleton_matches"]],
}
(OUT / "asset-readback.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("RUNEBOUND_THIRD_PERSON_READ " + json.dumps(report["summary"]))
