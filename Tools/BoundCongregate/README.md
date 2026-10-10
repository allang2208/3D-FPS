# BoundCongregate / 缚群 M-88

当前为 V29 活体与 V25 衣物、认可的 V28 拍击、V33 撕咬判定、一次快速近战挣脱和 V34 无支撑死亡。V32 死亡运动被否定，但其独立尸体仍供 V34 使用；V34 已构建保存、未游戏测试。

当前状态、恢复顺序和公开边界见 [2026-10-10 发布记录](../../Docs/Monsters/bound-congregate-publication-20261010.md)。308 个新归档文件的原路径和 SHA-256 见 [本次清单](../../Docs/Monsters/bound-congregate-retirement-20261010.json)；早期 618 项归档仍见 [历史清单](../../Docs/Monsters/bound-congregate-retirement-20261008.json)。V20/V21/V23 衣物、V22/V26/V27 拍击工具已退役到 trash，不能从历史文档直接重跑覆盖当前配置。

`author_*` 在 Blender 或相应外部 Python 环境执行；`import_*` 依赖 UE Python 和已存在的模板资产。必要编辑器操作经过现有 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次互斥；不主动打开或关闭 UE。`finish_*.ps1` 为历史分阶段入口，有些包含当时明确要求的诊断，不作为默认一键恢复入口。

带 `audit`、`diagnose`、`inspect`、`profile`、`review`、`render` 的脚本仅在用户明确要求对应范围时执行。旧脚本中的已归档输入先按清单恢复；本次没有重跑这些工具。

原模型、PBR、Blend/FBX、密集权重及采样、UE 包、运行环境和日志仅保留本机。所用 Python 环境按脚本依赖准备，包括 Blender bpy、NumPy、SciPy、Pillow；甩鞭离线模拟历史采用 MuJoCo 3.15.0。公开仓库不是完整可运行内容包。
