"""Read-only asset/config/source inventory for the requested 2026-10-20 review."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/SkillBatchReview20261020"
skills = json.loads((ROOT / "Content/ColdSteelData/skills.json").read_text(encoding="utf-8-sig"))
rows = []


def record(name, ok, detail):
    rows.append(dict(case=name, passed=bool(ok), detail=detail))


for key in ("swordMastery", "bluntMastery", "lightningHaste"):
    definition = skills[key]
    icon = ROOT / "Content/ColdSteelData" / definition["icon"]
    record(f"{key} icon exists", icon.is_file(), str(icon.relative_to(ROOT)))
record("blunt damage uses percentage only",
       skills["bluntMastery"]["damagePercentPerLevel"] == .0125
       and skills["bluntMastery"]["flatDamagePerLevel"] == 0, "20 levels -> 25 percent")
record("sword identity retained", skills["swordMastery"]["name"] == "刀剑精通", "swordMastery")

receipts = [
    "Saved/BellowAudioCleanup20261013/asset-receipt.json",
    "SourceAssets/M16SuppressedAudio20261015/import-receipt.json",
    "SourceAssets/RifleSuppressedAudio20261015/import-receipt.json",
    "SourceAssets/ShotgunAudioSwap20261017/import-receipt.json",
    "SourceAssets/DungeonBGM20261017/import-receipt.json",
    "SourceAssets/HangingBellIdleGhostBreath20261018/import-receipt.json",
    "SourceAssets/DragonBreathAudio20261019/import-receipt.json",
    "SourceAssets/AdvancedMagicRange20261019/asset-receipt.json",
    "SourceAssets/LightningHaste20261019/asset-receipt.json",
    "SourceAssets/MeleeMasteries20261019/asset-receipt.json",
]
assets = set()
for name in receipts:
    path = ROOT / name
    record(f"saved receipt {name}", path.is_file(), name)
    if not path.is_file():
        continue
    receipt = path.read_text(encoding="utf-8-sig")
    for asset in re.findall(r'"/Game/([^"]+)"', receipt):
        package = asset.split(".")[0]
        assets.add("Content/" + package + ".uasset")
for path in sorted(assets):
    record(f"saved package {path}", (ROOT / path).is_file(), path)

# Inventory of the original cross-cutting change plus current query consumers.
# Presence of a call is code coverage evidence, never a gameplay pass.
before = json.loads((ROOT / "Saved/RangedFriendly20261013/source-changes.json").read_text(encoding="utf-8-sig"))
inventory = []
for name in before:
    path = ROOT / name
    source = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    inventory.append(dict(file=name, exists=path.is_file(),
                          friendly_query_calls=source.count("RangedAttackQuery::"),
                          shared_occlusion_calls=source.count("MagicOcclusion::")))
consumers = []
for path in (ROOT / "Source/FPSGAME").rglob("*.cpp"):
    source = path.read_text(encoding="utf-8-sig")
    if "RangedAttackQuery::" in source:
        consumers.append(str(path.relative_to(ROOT)).replace("\\", "/"))
result = dict(checks=len(rows), failures=sum(not row["passed"] for row in rows),
              checks_result=rows, original_ranged_files=inventory,
              current_ranged_consumers=sorted(consumers), loaded_assets=False,
              real_network_transport=False, auditioned=False)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "inventory-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: result[key] for key in ("checks", "failures")}))
for row in rows:
    if not row["passed"]:
        print("MISSING:", row["detail"])
print(f"Original ranged files: {len(inventory)}; current consumers: {len(consumers)}")
