"""Aggregate saved network audit receipts; does not launch UE or run checks."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out = root / "SourceAssets/MonsterNetworkHitAudit20261018"
previous = root / "SourceAssets/NonHumanoidHitAudit20261018"
read = lambda path: json.loads(path.read_bytes())
audit = read(out / "authority.json")
repair = read(previous / "repair.json")
expected = {r["physics_asset"]: r["query_hulls_added"] for r in repair["models"] if r.get("saved")}
asset_rows = []
for row in audit["models"]:
    asset = row.get("physics_asset")
    if asset in expected:
        asset_rows.append({"id": row["id"], "asset": asset, "saved_query_hulls": row["saved_repair_hulls"],
                           "receipt_query_hulls": expected[asset],
                           "matches_saved_receipt": row["saved_repair_hulls"] == expected[asset]})
result = {
    "authority_audit": audit,
    "asset_readback": asset_rows,
    "prior_asset_receipt_matches": len(asset_rows) == 16 and all(r["matches_saved_receipt"] for r in asset_rows),
    "builds": [read(out / "build-FPSGAMEEditor.json"), read(out / "build-FPSGAME.json")],
    "audit_exit": read(out / "authority_exit.json"),
    "source_fixes": [
        "M10 iris and M66 cleft contacts are classified against bounded authority pose history, then rebased for the existing damage classifier.",
        "HeQue validates the first collision against historical body hulls, retaining limb occlusion before granting heart critical damage.",
        "Bound Congregate validates deployed-part proximity against the contact-time pose; expired/recovering organs cannot redirect damage to body HP.",
        "Hanging Bell M09, M10 and Spiral Pillar M14 now replicate MaxHealth as well as Health.",
    ],
    "runtime_history_budget": {"models": 4, "maximum_poses": 32, "maximum_samples_per_second": 30,
                               "new_tick": False, "authority_only": True},
    "limits": [
        "Production ForwardHit and ServerReportHit execute in an isolated remote-authority fixture, not through two socket-connected game processes.",
        "Impact/origin vectors use the production NetSerialize path. Actor channel delivery and packet-loss behavior are not covered.",
        "Health and MaxHealth replication descriptors are checked; live observer UI and late-join delivery are not visually accepted.",
        "Moving-target probes include 200 ms pose separation and authored animation changes, not every frame or every attack-state transition.",
        "No GUI editor, gameplay map, dynamic cloth or full multiplayer combat acceptance was run.",
        "Night Warden remains excluded at the user's request.",
    ],
}
result["complete"] = (audit.get("complete", False) and audit.get("passed", False)
    and result["prior_asset_receipt_matches"] and result["audit_exit"]["exit_code"] == 0
    and all(b["exit_code"] == 0 for b in result["builds"]))
(out / "delivery.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"complete": result["complete"], "models": len(audit["models"]), "failures": audit["failures"],
    "asset_rows": len(asset_rows), "old_moving_weakpoints_lost": sum(r.get("old_moving_weakpoints_lost", 0) for r in audit["models"]),
    "moving_weakpoints_lost": sum(r.get("moving_weakpoints_lost", 0) for r in audit["models"])}, ensure_ascii=False))
