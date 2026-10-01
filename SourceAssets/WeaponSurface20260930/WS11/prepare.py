"""Produce offline WS1.1 handoff recipes from saved authoring records.

Writes only WS11/Prepared. No Unreal imports, package writes or tests.
Recorded values and inferred inheritance are labeled separately from live UE state.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
OUT = HERE / "Prepared"
INPUTS = {}


def read(relative):
    path = SOURCE / relative
    raw = path.read_bytes()
    INPUTS[relative] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode("utf-8-sig"))


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bindings(receipt):
    result = {}
    for mesh, rows in receipt.get("bindings", {}).items():
        for row in rows:
            result.setdefault(row["after"], []).append({"mesh": mesh, "slot": row["slot"]})
    return result


def canonical(values, prefix=""):
    return {key[len(prefix):] if prefix and key.startswith(prefix) else key: value
            for key, value in values.items()}


def recommendation(weapon, row, regional):
    if weapon == "SVD":
        return "preserve_refine03", "Retain saved Refine03 appearance; shared-function extraction is the next useful work."
    if regional:
        return "region_adapter_first", "Mixed ASH12 regions share grain controls. Keep current values until metal-only controls exist."
    if row.get("preset") in PROFILES["profiles"]["CleanMetalFine"]["eligible_presets"]:
        return "fine_metal_candidate", "Optional detail-only candidate; preserve base color, base roughness, normals and geometry."
    return "preserve_surface_family", "Keep polymer, rubber, interior and other authoring families unchanged."


def normal_form(weapon, source_file, row, uses, regional=False, plan_entry=None):
    prefix = "WS_" if weapon == "SVD" else ""
    override_scalars = canonical(row.get("scalars", {}), prefix)
    override_vectors = canonical(row.get("vectors", {}), prefix)
    preset = row.get("preset")
    # This is an authoring-data inference, never a read of a live material instance.
    base = CARD["presets"].get(preset, {})
    scalar_view = dict(CARD["master_defaults"]["scalars"]) if preset else {}
    scalar_view.update(base.get("scalars", {}))
    scalar_view.update(override_scalars)
    vector_view = dict(base.get("vectors", {}))
    vector_view.update(override_vectors)
    decision, reason = recommendation(weapon, row, regional)
    proposal = {}
    if decision == "fine_metal_candidate":
        for key, proposed in PROFILES["profiles"]["CleanMetalFine"]["scalars"].items():
            if scalar_view.get(key) != proposed:
                proposal[key] = {"recorded_or_inferred": scalar_view.get(key), "candidate": proposed}
    return {
        "material": row["path"], "bindings_from_saved_receipt": uses,
        "source_record": source_file, "recorded_parent": row.get("parent"),
        "preset": preset, "category": row.get("category"),
        "parameter_adapter": "SVD_Refine03" if weapon == "SVD" else weapon + "_WS1",
        "recorded_overrides": {"scalars": override_scalars, "vectors_linear": override_vectors},
        "authoring_value_view": {"scalars": scalar_view, "vectors_linear": vector_view,
                                 "basis": "current source card plus saved overrides" if preset else "saved Refine03 overrides only; other inherited values not inferred",
                                 "live_ue_state_read": False},
        "recorded_textures": row.get("textures", {}),
        "recorded_base_properties": {"two_sided": row.get("two_sided")},
        "region_mixed": regional, "slot_plan_details": plan_entry,
        "recorded_edge_normal": row.get("edge_normal"),
        "decision": decision, "reason": reason, "candidate_scalar_changes": proposal,
        "textures_to_convert_now": [], "graph_merge_authorized_by_this_recipe": False,
        "asset_write_performed": False,
        "next_asset_stage": "Read actual effective instance parameters and input semantics before applying a separate production revision. This file is not an installer."
    }


OUT.mkdir(exist_ok=True)
CARD = read("surface_card.json")
PROFILES = read("WS11/profiles.json")
read("WS11/slot_template.json")
read("WS11/shared_functions.json")
REPORT = {"standard": "WS1.1", "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
          "preparation_complete": True, "assets_installed": False, "tested": False,
          "basis": "saved recipes and receipts, not live UE asset inspection", "weapons": {}}

for weapon, files in {
    "A762": ["A762/install_receipt.json", "A762/accessory_receipt.json"],
    "ASH12": ["ASH12/install_receipt.json"],
    "SVD": []
}.items():
    records = []
    if weapon == "SVD":
        relative = "SVD/Refine03/apply_receipt.json"
        receipt = read(relative)
        recipe = read("SVD/Refine03/recipe.json")
        plan = read("SVD/slot_plan.json")
        targets = {target["material"]: target for target in recipe["targets"]}
        for path, saved in receipt["instances"].items():
            target = targets[path]
            row = dict(saved, path=path)
            owner = plan[target["mesh"]]
            uses = [{"mesh": owner["path"], "slot": target["slot"]}]
            detail = {"original_slot_plan": owner["slots"][target["slot"]],
                      "refine03_target": target}
            records.append(normal_form(weapon, relative, row, uses, plan_entry=detail))
    else:
        plan = read(weapon + "/slot_plan.json")
        indexed = {(group["path"].split(".")[0], slot): spec
                   for group in plan.values() if isinstance(group, dict) and "slots" in group
                   for slot, spec in group["slots"].items()} if weapon == "ASH12" else {}
        for relative in files:
            receipt = read(relative)
            lookup = bindings(receipt)
            for row in receipt["materials"].values():
                uses = lookup.get(row["path"], [])
                specs = [indexed.get((use["mesh"].split(".")[0], use["slot"]), {}) for use in uses]
                regional = any(spec.get("regional") for spec in specs)
                records.append(normal_form(weapon, relative, row, uses, regional,
                                           {"matched_slots": specs} if indexed else None))
    counts = dict(Counter(row["decision"] for row in records))
    wet = {"parameter": "WeaponWetness", "route": "master_identity" if weapon == "A762" else "existing_self_mapping_table"}
    output = {"standard": "WS1.1", "weapon": weapon, "status": "prepared_not_applied",
              "live_ue_state_read": False, "assets_installed": False, "tested": False,
              "record_count": len(records), "decisions": counts, "wetness": wet, "materials": records}
    write(weapon + ".json", output)
    REPORT["weapons"][weapon] = {"records": len(records), "decisions": counts, "file": weapon + ".json"}

REPORT["record_count"] = sum(row["records"] for row in REPORT["weapons"].values())
REPORT["inputs_sha256"] = INPUTS
write("preparation_receipt.json", REPORT)
print(json.dumps({key: value for key, value in REPORT.items() if key != "inputs_sha256"}, ensure_ascii=False, indent=2))
