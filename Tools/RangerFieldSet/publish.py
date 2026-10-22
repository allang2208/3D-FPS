"""Publish the ranger_field five-piece set values (scoped, idempotent).

Set: feather hat + ranger top + leather pants + leather boots + brown fingerless gloves.
Defense is authored in items.json (catalog authority); set identity and description
are added to source-combat-items.json. The thick leather gloves are left untouched.
"""
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path("D:/FPS3D/FPSGAME")
D = ROOT / "Content/ColdSteelData"
SRC = ROOT / "SourceAssets/RangerFieldSet20261022"
BEFORE = SRC / "Before"
SET_ID = "ranger_field"
SET_DESC = "野行套：轻甲五件，集齐五件额外获得防御 +5%、暴击率 +10%、暴击伤害 +25%。"

spec = importlib.util.spec_from_file_location("ranger_entries", str(ROOT / "Tools/BrownLeatherSet/json_entries.py"))
entries = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entries)

# base / perEnhance / bonusStats. Only the fields below are owned.
# Overlay entries carry stats that live in source-combat-items.json instead of
# items.json (the glove already had its real values there).
PIECES = {
    "ue_ranger_feather_hat": dict(
        defense={"base": 6, "perEnhance": 0.6},
        bonusStats={"crit": 10, "critDamageBonus": 0.25},
    ),
    "ue_field_sweater": dict(
        defense={"base": 8, "perEnhance": 1.2},
        bonusStats={"bowDrawSpeed": 0.10, "reloadSpeed": 0.10},
    ),
    "ue_leather_pants": dict(
        defense={"base": 20, "perEnhance": 1.6},
        bonusStats={"moveSpeedPercent": 0.05},
    ),
    "ue_leather_boots": dict(
        defense={"base": 12, "perEnhance": 1.0},
        bonusStats={"moveSpeedPercent": 0.05},
    ),
    "ue_field_gloves": dict(
        # items.json and the overlay carry the same numbers so an old instance
        # snapshot cannot produce a different result; the overlay stays the
        # documented source for this glove's +10% reload/bow.
        defense={"base": 2, "perEnhance": 0.5},
        bonusStats={},
        overlay={
            "defense": {"base": 2, "perEnhance": 0.5},
            "bonusStats": {"bowDrawSpeed": 0.10, "reloadSpeed": 0.10},
        },
    ),
}


def main():
    items_path = D / "items.json"
    combat_path = D / "source-combat-items.json"
    raw_items = items_path.read_bytes()
    raw_combat = combat_path.read_bytes()
    items_text = raw_items.decode("utf-8-sig")
    combat_text = raw_combat.decode("utf-8-sig")
    catalog = json.loads(items_text)
    combat = json.loads(combat_text)
    BEFORE.mkdir(parents=True, exist_ok=True)

    for key, update in PIECES.items():
        if key not in catalog:
            raise RuntimeError("missing item " + key)
        before = catalog[key]
        after = json.loads(json.dumps(before))
        after["defense"] = update["defense"]
        if update["bonusStats"]:
            after["bonusStats"] = update["bonusStats"]
        else:
            after.pop("bonusStats", None)
        items_text = entries.replace(items_text, [key], after)
        catalog[key] = after

    # The combat overlay is authoritative for the glove's defense/bonusStats, so
    # its entry is written fully. Other pieces only get set identity here so any
    # pre-existing overlay keys survive.
    for key in PIECES:
        after = dict(combat.get(key, {}))
        after["armorSet"] = SET_ID
        after["setBonusDesc"] = SET_DESC
        for field, value in PIECES[key].get("overlay", {}).items():
            after[field] = value
        if key in combat:
            combat_text = entries.replace(combat_text, [key], after)
        else:
            combat_text = entries.insert(combat_text, [], key, after)
        combat[key] = after

    if items_path.read_bytes() != raw_items or combat_path.read_bytes() != raw_combat:
        raise RuntimeError("catalog changed during preparation; no writes made")
    for name, raw in (("items.json", raw_items), ("source-combat-items.json", raw_combat)):
        backup = BEFORE / name
        if not backup.exists():
            backup.write_bytes(raw)
    prefix = b"\xef\xbb\xbf" if raw_items.startswith(b"\xef\xbb\xbf") else b""
    items_path.write_bytes(prefix + items_text.encode("utf-8"))
    prefix = b"\xef\xbb\xbf" if raw_combat.startswith(b"\xef\xbb\xbf") else b""
    combat_path.write_bytes(prefix + combat_text.encode("utf-8"))

    receipt = {
        "completed": True,
        "set": SET_ID,
        "set_description": SET_DESC,
        "pieces": {k: {"defense": v["defense"], "bonusStats": v["bonusStats"]} for k, v in PIECES.items()},
        "replaced_gloves": "ue_field_gloves",
        "untouched_gloves": "ue_original_gloves",
        "runtime_tested": False,
    }
    (SRC / "published.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RANGER_FIELD_SET_PUBLISHED", SET_ID, flush=True)


if __name__ == "__main__":
    main()
