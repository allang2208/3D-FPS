# 人形击飞、倒地与起身制作源

本机源动作来自 `SourceAssets/FatZombieMeshy20260913/sources/` 的 Mesh2Motion CC0 动作包；本目录保留来源清单、CC0 许可、目标重定向中间 FBX、拟合 Blend/FBX 与导入收据。目标角色的蒙皮/网格不因此获得 CC0 许可。

作者链：`Tools/HumanoidKnockdown/export_sources.py` → `import_animations.py` → `read_retarget_poses.py` → `fit_recovery.py` → `author_prone_recovery.py` → `import_fitted.py`。按阶段在 Blender 或 UE 执行，不把普通 Python 当作引擎 API 环境；制作记录及参数见 [击飞接入](../../Docs/Monsters/humanoid-knockdown-20260926.md)。

自动 Blend 备份已入本机 trash，正式可编辑源保留。源码恢复缺口、许可证边界和本机资源顺序见 [发布说明](../../Docs/Monsters/monster-hands-publication-20260927.md)。本次发布不重新制作或验收。
