# BoundCongregate / 缚群

衣物于 2026-10-08 因用户反馈不合格而暂停。V18、V19 不是认可模板；保留脚本用于恢复制作现场，不能自动执行以覆盖用户配置。

当前状态、版本依赖、许可和本机输入见 [暂停与发布记录](../../Docs/Monsters/bound-congregate-paused-publication-20261008.md)。归档文件原路径和 SHA-256 见 [清单](../../Docs/Monsters/bound-congregate-retirement-20261008.json)。

`author_*` 在 Blender 或相应外部 Python 环境执行；`import_*` 依赖 UE Python 和已存在的模板资产。必要编辑器操作经过现有 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次互斥；不主动打开或关闭 UE。`finish_*.ps1` 为历史分阶段入口，有些包含当时明确要求的诊断，不作为默认一键恢复入口。

带 `audit`、`diagnose`、`inspect`、`profile`、`review`、`render` 的脚本仅在用户明确要求对应范围时执行。旧脚本中的已归档输入先按清单恢复；本次没有重跑这些工具。

原模型、PBR、Blend/FBX、密集权重及采样、UE 包、运行环境和日志仅保留本机。所用 Python 环境按脚本依赖准备，包括 Blender bpy、NumPy、SciPy、Pillow；甩鞭离线模拟历史采用 MuJoCo 3.15.0。公开仓库不是完整可运行内容包。
