# 715 整理与源码发布（2026-09-14）

当前交付入口和恢复边界：[715 资源恢复](../../Docs/Weapons/dan-wesson715-publication-20260914.md)。废案选择、保留项和散列说明：[两轮模型回退](../../Docs/Rejected/dan-wesson715-models-20260914.md)。

- `archive_rejected.ps1`：本轮已执行的六处精准归档，校验根目录和移动前后散列；不是日常清理命令，不要对已归档路径重复运行。
- `read_archive_references.py` / `archive-references.json`：仅读取两处废案的资源引用，目录之外引用为零。
- `archive-manifest.json` / `archive-summary.json`：379 文件、2,454,674,299 字节的移动清单及摘要。
- 发布前按显式文件/片段构造独立暂存索引，保留真实工作文件和其他任务暂存内容。共享技能/战斗公式/UI 等并行修改不进入该提交。
- 发布检查覆盖 60 个 Python 作者脚本语法、1 个 PowerShell 归档脚本语法、候选 JSON、项目头文件依赖、文本链接、文件大小/类型、敏感信息模式、四份 SKILL 镜像和 `git diff --cached --check`。检查中没有发现阻止发布的问题。

本轮没有游戏测试、PIE、渲染或试听，也没有重新声称历史构建或用户体验为本次验收。受许可约束的资产留在本机。临时索引和混合源码快照在完成发布后移入本机 `trash/dan-wesson715-publication-local-20260914`，不公开提交。
