"""Record the current player configuration as input for female-body authoring.

This only writes an authoring inventory. It does not validate assets, launch UE,
publish runtime configuration, or claim any female meshes have been produced.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "SourceAssets/FemalePlayer20261022/fit_scope.json"


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def asset_references(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from asset_references(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from asset_references(child, f"{path}/{index}")
    elif isinstance(value, str) and value.startswith("/Game/"):
        yield {"selector": path, "asset": value}


def main():
    body = read("Content/ColdSteelData/player_body.json")
    modular = read("Content/ColdSteelData/modular_outfits.json")
    catalog = read("Content/ColdSteelData/items.json")
    slots = {3: "gloves", 7: "tops", 13: "footwear", 15: "pants"}

    def recipes(entries, category=None):
        return [
            {
                "item_id": key,
                "name": catalog.get(key, {}).get("name", key),
                "category": category or slots.get(recipe.get("slot"), "other"),
                "female_status": "awaiting_selected_source_body",
                "registered_recipe": recipe,
                "asset_references": list(asset_references(recipe)),
            }
            for key, recipe in entries.items()
        ]

    clothing = recipes(modular["items"])
    backpacks = recipes(body["outfits"], "backpack")
    headwear = recipes(body["head_equipment"], "headwear")
    clips = [
        {"key": key, "source_asset": asset, "female_status": "awaiting_retarget_and_contact_fit"}
        for key, asset in body["clips"].items()
    ]
    scope = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "planning_only_no_female_assets_imported",
        "scope_note": "Registered configuration snapshot, not proof of live usage or asset compatibility. Refresh before authoring; parallel work can change these inputs.",
        "source_configs": ["Content/ColdSteelData/player_body.json", "Content/ColdSteelData/modular_outfits.json", "Content/ColdSteelData/items.json"],
        "selected_female_source": (
            read("SourceAssets/KaitlinPlayer20261023/source_receipt.json")
            if (ROOT / "SourceAssets/KaitlinPlayer20261023/source_receipt.json").exists() else None
        ),
        "male_body_baseline": {key: value for key, value in body.items() if key not in ("clips", "outfits", "head_equipment")},
        "registered_rig_profiles": modular["profiles"],
        "native_bare_hands_default": modular.get("native_bare_hands_default"),
        "clothing": clothing,
        "backpacks": backpacks,
        "headwear": headwear,
        "animation_clips": clips,
        "counts": {
            "clothing": len(clothing),
            "clothing_by_category": dict(Counter(row["category"] for row in clothing)),
            "backpacks": len(backpacks),
            "headwear": len(headwear),
            "animation_mappings": len(clips),
            "animation_groups": dict(Counter(row["key"].split(".")[0] for row in clips)),
            "registered_rig_families": len({row["rig_profile"] for row in modular["profiles"].values()}),
        },
    }
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(DESTINATION), "counts": scope["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
