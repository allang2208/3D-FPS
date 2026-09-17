# 罗马凉亭 v2 退役归档（2026-09-17）

安装 WORKFLOW.md 第 4 节：本任务期间被取代的脚本与资产移到 `trash/roman-pavilion-v2-20260917/`，
字段（原路径、目标、大小、SHA-256、原因、替代物）见同目录 `roman-pavilion-v2-20260917.json`。

## 归档内容（18 项）

- **脚本**：一次性诊断／被取代的辅助脚本（占位摆放、旧穹顶导出、剖面探针、第一版实机探针、
  换柱脚本、九份 entry/collision 诊断）。可复用的部分保留在
  `diagnose_pavilion2_gap.py`（pivot 与拼装自检）、`diagnose_pavilion2_collisiondata.py`（碰撞形状计数）、
  `diagnose_pavilion2_own_build.py`（读用户建造世界）、`live_probe_overlap.py`（球体重叠点名）。
- **资产**：2026-09-16 版凉亭三件（`SM_PavilionStylobate_20` / `SM_PavilionRing_20` / `SM_PavilionDome_20`）。
  其穹顶是直圆锥（`self_union` 的 `bTrimFlaps` 把半球弧面塌成弦）；relocation 前已核对调色板 12 条与
  `DayNight_Lighting` 均不再引用，现役替代为 `SM_RomanPavilionFull_20`（整体件）与
  `SM_RomanPavilionDome_20`（关卡内穹顶）。

对应的现役文件与全部结论见 `SourceAssets/RomanColumn20260915/README.md`。
