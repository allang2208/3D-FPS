"""Archive this task's superseded files per WORKFLOW.md section 4.

Moves the rejected/superseded scripts and the retired 2026-09-16 pavilion meshes into
trash/roman-pavilion-v2-20260917/, writes the committed record to
Docs/AssetArchives/roman-pavilion-v2-20260917.json (and a short .md companion), and leaves
everything else alone. Precise list, no globs over other sessions' files.
"""

import hashlib
import io
import json
import os
import shutil

ROOT = r"D:\FPS3D\FPSGAME"
TRASH = os.path.join(ROOT, "trash", "roman-pavilion-v2-20260917")
ARCHIVE_JSON = os.path.join(ROOT, "Docs", "AssetArchives", "roman-pavilion-v2-20260917.json")

SUPERSEDED_NOTE = ("One-off diagnostic from the walk-in investigation; the conclusion is kept in "
                   "SourceAssets/RomanColumn20260915/README.md (headless physics queries only answer "
                   "for actors spawned in the same process)")

FILES = [
    ("SourceAssets/RomanColumn20260915/place_pavilion2_20260917.py",
     "Scene placement helper. Superseded: build_pavilion2_20260917.py now performs the swap itself "
     "with EditorActorSubsystem, because spawn_static_mesh_actor spawns nothing in a commandlet",
     "SourceAssets/RomanColumn20260915/build_pavilion2_20260917.py"),
    ("SourceAssets/RomanColumn20260915/dump_pavilion_obj.py",
     "Dump of the old cone dome for the profile forensics. Superseded by dump_pavilion2_pieces.py",
     "SourceAssets/RomanColumn20260915/dump_pavilion2_pieces.py"),
    ("SourceAssets/RomanColumn20260915/dump_pavilion2_obj.py",
     "sed copy of dump_pavilion_obj.py made for a single dump. Superseded by dump_pavilion2_pieces.py",
     "SourceAssets/RomanColumn20260915/dump_pavilion2_pieces.py"),
    ("SourceAssets/RomanColumn20260915/probe_revolve_20260917.py",
     "Profile-order probe. Its finding (a well-formed profile keeps the arc; the collapse came from "
     "self_union) is recorded in the README, and probe_bisect_dome.py carries the root-cause evidence",
     "SourceAssets/RomanColumn20260915/probe_bisect_dome.py"),
    ("SourceAssets/RomanColumn20260915/live_probe_pavilion.py",
     "First in-editor probe: two API mistakes (Rotator ctor order, release_render_target2d arity). "
     "Superseded by live_probe_pavilion2.py",
     "SourceAssets/RomanColumn20260915/live_probe_pavilion2.py"),
    ("SourceAssets/RomanColumn20260915/swap_pavilion_columns_20260917.py",
     "In-editor swap of the pavilion columns to the round-plate variant. Superseded: "
     "build_pavilion2_20260917.py now places the round column directly",
     "SourceAssets/RomanColumn20260915/build_round_column_20260917.py"),
]
for name in ("entry", "entrytrust", "walkin", "nearby", "respawn", "identify", "bw_now",
             "ground", "groundmesh"):
    FILES.append(("SourceAssets/RomanColumn20260915/diagnose_pavilion2_%s.py" % name, SUPERSEDED_NOTE,
                  "diagnose_pavilion2_gap.py / diagnose_pavilion2_collisiondata.py / "
                  "diagnose_pavilion2_own_build.py / live_probe_overlap.py"))

ASSETS = [
    ("Content/Props/RomanColumn20260915/SM_PavilionStylobate_20.uasset",
     "2026-09-16 pavilion stylobate (32-cell plan). Replaced by the v2 set, itself superseded by the "
     "one-piece SM_RomanPavilionFull_20. Verified unreferenced by the palette (12 entries) and by "
     "DayNight_Lighting before moving",
     "Content/Props/RomanColumn20260915/SM_RomanPavilionFull_20.uasset"),
    ("Content/Props/RomanColumn20260915/SM_PavilionRing_20.uasset",
     "2026-09-16 pavilion entablature ring. Same reasoning as the stylobate",
     "Content/Props/RomanColumn20260915/SM_RomanPavilionFull_20.uasset"),
    ("Content/Props/RomanColumn20260915/SM_PavilionDome_20.uasset",
     "2026-09-16 pavilion dome, the straight cone (self_union bTrimFlaps ate the arc). Replaced by "
     "SM_RomanPavilionDome_20 and then folded into SM_RomanPavilionFull_20",
     "Content/Props/RomanColumn20260915/SM_RomanPavilionFull_20.uasset"),
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


os.makedirs(TRASH, exist_ok=True)
entries, moved, missing = [], 0, []
for rel, reason, replacement in FILES + ASSETS:
    src = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(src):
        missing.append(rel)
        continue
    size = os.path.getsize(src)
    digest = sha256(src)
    dst = os.path.join(TRASH, os.path.basename(rel))
    shutil.move(src, dst)
    # the matching log goes with its script, when one exists
    log_src = src[:-3] + ".log"
    if rel.endswith(".py") and os.path.exists(log_src):
        shutil.move(log_src, os.path.join(TRASH, os.path.basename(log_src)))
    entries.append({
        "Name": os.path.basename(rel),
        "OriginalPath": rel,
        "ArchivedTo": "trash/roman-pavilion-v2-20260917/" + os.path.basename(rel),
        "Bytes": size,
        "SHA256": digest,
        "Reason": reason,
        "Replacement": replacement,
    })
    moved += 1
    print("[arch] %-70s %8d B" % (os.path.basename(rel), size))

record = {
    "Task": "Roman pavilion v2 (roman-pavilion-v2-20260917)",
    "ArchivedOn": "2026-09-17",
    "Rule": "WORKFLOW.md section 4",
    "Count": len(entries),
    "Files": entries,
}
with io.open(ARCHIVE_JSON, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(record, handle, ensure_ascii=False, indent=4)

companion = os.path.join(ROOT, "Docs", "AssetArchives", "roman-pavilion-v2-20260917.md")
with io.open(companion, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("""# 罗马凉亭 v2 退役归档（2026-09-17）

安装 WORKFLOW.md 第 4 节：本任务期间被取代的脚本与资产移到 `trash/roman-pavilion-v2-20260917/`，
字段（原路径、目标、大小、SHA-256、原因、替代物）见同目录 `roman-pavilion-v2-20260917.json`。

## 归档内容（%d 项）

- **脚本**：一次性诊断／被取代的辅助脚本（占位摆放、旧穹顶导出、剖面探针、第一版实机探针、
  换柱脚本、九份 entry/collision 诊断）。可复用的部分保留在
  `diagnose_pavilion2_gap.py`（pivot 与拼装自检）、`diagnose_pavilion2_collisiondata.py`（碰撞形状计数）、
  `diagnose_pavilion2_own_build.py`（读用户建造世界）、`live_probe_overlap.py`（球体重叠点名）。
- **资产**：2026-09-16 版凉亭三件（`SM_PavilionStylobate_20` / `SM_PavilionRing_20` / `SM_PavilionDome_20`）。
  其穹顶是直圆锥（`self_union` 的 `bTrimFlaps` 把半球弧面塌成弦）；relocation 前已核对调色板 12 条与
  `DayNight_Lighting` 均不再引用，现役替代为 `SM_RomanPavilionFull_20`（整体件）与
  `SM_RomanPavilionDome_20`（关卡内穹顶）。

对应的现役文件与全部结论见 `SourceAssets/RomanColumn20260915/README.md`。
""" % len(entries))

print("[arch] record -> %s" % ARCHIVE_JSON)
print("[arch] moved=%d missing=%s" % (moved, missing if missing else "none"))
print("[arch] RESULT: " + ("PASS" if not missing else "CHECK"))
