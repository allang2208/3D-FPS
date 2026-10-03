"""Summarize saved production receipts; does not run the game or any tests."""
from pathlib import Path
import json

root = Path(globals().get('ANIMATION_SHARING_JOB_ROOT', Path(__file__).parent)).resolve()
receipt = json.loads((root / "install_receipt.json").read_text(encoding="utf-8"))
groups = {}
replaced, retained, bases = set(), set(), set()
for key, profile in receipt["profiles"].items():
    weapon = key.split("/")[0]
    group = groups.setdefault(weapon, dict(saved_profiles=0, pairs=0, delta_pairs=0,
                                          retained_pairs=0, bytes=0, keys=0))
    if not profile.get("saved"):
        continue
    group["saved_profiles"] += 1
    group["pairs"] += len(profile["pairs"])
    group["retained_pairs"] += len(profile["retained"])
    group["delta_pairs"] += len(profile["pairs"]) - len(profile["retained"])
    group["bytes"] += profile["bytes"]
    group["keys"] += profile["key_count"]
    replaced.update(profile["replaced"])
    retained.update(row["authored"] for row in profile["retained"])
    bases.update(row["base"] for row in profile["pairs"])

totals = {name: sum(group[name] for group in groups.values()) for name in
          ("saved_profiles", "pairs", "delta_pairs", "retained_pairs", "bytes", "keys")}
summary = dict(complete=receipt["complete"], tested=False, totals=totals, groups=groups,
               unique_converted_variants=len(replaced),
               unique_retained_variants=len(retained),
               unique_variants_without_full_clip_reference=len(replaced-retained-bases),
               source_animations_deleted=False)
(root / "production_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
