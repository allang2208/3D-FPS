# 苍龙待办、归档与源码发布

2026-10-05，当前能量条和爪击为**未达标、待返工**。入口：[待办](../../Backlog.md)、[整理说明](../../Combat/enchant-azure-dragon-publication-20261005.md)、[恢复配方](../../../SourceAssets/AzureDragon20261004/README.md)、[SKILL](../../../skills/ue5-weapon-workflow/references/azure-dragon-pending.md)。

- `archive-manifest.json`：实际 117 份文件归档，含 17 份旧 UE 包，共 14,079,388 字节；每条移动前后 SHA-256 相同，源路径、目标、原因和替代物完整保留。
- `archive-plan.json`：移动前冻结清单；`source-archive.json` 和 `asset-archive.json` 分别记录实际 100／17 份文件落盘。实体只在本机 `trash/azure-dragon-retired-20261005`。
- `retained-reference.json`：认可设计图完整迁移到 `SourceAssets/AzureDragon20261004/References`，没有放入废案。当前 V9 与授权原始输入继续保留，不代表效果已认可。
- `published-files.json`：本轮精确暂存路径与内容散列；排除清单自身和出版检查结果，避免互相依赖。
- `publication-checks.json`：仅记录推送规则要求的源码／元数据／索引检查；无游戏、渲染、PIE 或视觉验收。

Git 只发布原创源码、当前制作配方、HLSL、数据、文档、SKILL 与以上元数据。Fab／Epic 派生网格、PBR、参考图、密集骨架／姿态、Blend／FBX、UE 包和机器回执留本机。授权输入仍需自行取得，资产包不随公开仓库再分发。
