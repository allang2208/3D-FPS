"""Summarize the saved isolated probes without launching Unreal or running tests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/NonHumanoidHitAudit20261018"


def read(name):
    return json.loads((OUT / name).read_bytes())


before = read("baseline-full.json")
after = read("after-repair.json")
repair = read("repair.json")
old = {row["id"]: row for row in before["monsters"]}
rows = []
for row in after["monsters"]:
    poses = row.get("poses", [])
    previous = old.get(row["id"], {}).get("poses", [])
    errors = [p["error"] for p in poses if "error" in p]
    errors += [row[k] for k in ("error", "damage_error") if k in row]
    damage = row.get("damage", [])
    eyes = row.get("eye_contacts", [])
    parts = row.get("part_damage", [])
    rows.append({
        "id": row["id"], "name": row["name"], "physics_asset": row.get("physics_asset"),
        "sampled_poses": len(poses),
        "surface_rays": sum(p.get("surface_rays", 0) for p in poses),
        "complex_misses_before": sum(p.get("complex_miss", 0) for p in previous),
        "complex_misses_after": sum(p.get("complex_miss", 0) for p in poses),
        "simple_misses_after": sum(p.get("simple_miss", 0) for p in poses),
        "sweep_misses_after": sum(p.get("sweep_miss", 0) for p in poses),
        "remote_contacts_rejected": sum(p.get("root_remote_rejected", 0) for p in poses),
        "remote_weakpoints_lost": sum(p.get("network_critical_lost_same_pose", 0) for p in poses),
        "filtered_gun_reaches_actor": row.get("filtered_gun_reaches_actor", False),
        "filtered_as_player_ally": row.get("filtered_as_player_ally", False),
        "damage_transactions": damage,
        "damage_paths_reduce_health": len(damage) == 4 and all(d["health_delta"] > 0 and d["returned_damage"] > 0 for d in damage),
        "eye_contacts": eyes, "errors": errors,
        "eye_network_parity": row["id"] != "M10Mawcrawler" or (bool(eyes) and
            any(e["local_weakpoint"] for e in eyes) and
            all(e["actual_contact"] and e["local_weakpoint"] == e["reported_weakpoint"] for e in eyes)),
        "explicit_friendly_still_protected": row.get("explicit_friendly_still_protected"),
        "part_damage": parts,
        "part_damage_routing_pass": row["id"] != "BoundCongregate" or
            (len(parts) == 4 and all(p["expected_pool_damaged"] for p in parts)),
    })

result = {
    "scope": "18 remaining F6 monsters, including every nonhumanoid class referenced by abandoned-facility encounters",
    "models": rows,
    "complete": before.get("complete", False) and after.get("complete", False) and repair.get("complete", False) and len(rows) == 18,
    "all_sampled_contacts_pass": all(not r["errors"] and r["surface_rays"] > 0 and r["sampled_poses"] == 4 and
        r["complex_misses_after"] == r["simple_misses_after"] == r["sweep_misses_after"] == r["remote_contacts_rejected"] == r["remote_weakpoints_lost"] == 0 and
        r["filtered_gun_reaches_actor"] and not r["filtered_as_player_ally"] and r["damage_paths_reduce_health"] and
        r["eye_network_parity"] and r["part_damage_routing_pass"] and
        (r["id"] != "FleshHandMinion" or r["explicit_friendly_still_protected"]) for r in rows),
    "source_fixes": [
        "Enemy summons no longer use the Summoned reward tag as player allegiance.",
        "M10 eye contacts accept component-less network receipts while keeping anatomical/facing checks.",
        "Flesh-hand authority refreshes living skeletal collision offscreen.",
        "Root Crown remote validation tries actual hulls before padded latency fallback.",
        "Bound Congregate folded tissue/attached roots damage the body; deployed restraints retain their separate pool and stale-report guard.",
    ],
    "asset_receipt": "repair.json",
    "query_shape_budget_per_asset": 384,
    "max_added_query_hulls": max(r.get("query_hulls_added", 0) for r in repair["models"]),
    "backups": "Before/",
    "builds": [read("build-FPSGAMEEditor.json"), read("build-FPSGAME.json")],
    "limits": [
        "Isolated commandlet world; no map BeginPlay, game session, GUI editor launch or visual acceptance.",
        "Imported LOD0 evaluated skeletal surfaces; dynamic cloth, morphs and procedural attack modifiers are not simulated.",
        "Network contact reconstruction is checked at matching poses, not a two-client latency session.",
        "Four authored animation samples per model are sampled, not every frame of every state.",
        "Night Warden development gameplay remains outside this pass.",
    ],
}
(OUT / "delivery.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"models": len(rows), "complete": result["complete"],
    "all_sampled_contacts_pass": result["all_sampled_contacts_pass"],
    "surface_rays": sum(r["surface_rays"] for r in rows),
    "misses_before": sum(r["complex_misses_before"] for r in rows),
    "misses_after": sum(r["complex_misses_after"] for r in rows)}, ensure_ascii=False))
