# 当前开发方向

当前工程为根目录 `FPSGAME.uproject`（UE 5.8.2）。用户已指定后续全面转向 UE5；Godot 只作为归档参考。完整本机宿主为 `D:/FPS3D/FPSGAME`，Git main 的当前源码直接位于根目录，不再仅发布 `unreal/<topic>` 摘录。

- 开发和发布先读 [WORKFLOW.md](WORKFLOW.md)，仓库整理、归档与推送遵守第 8 节。
- 枪械读 [ue5-weapon-workflow](skills/ue5-weapon-workflow/SKILL.md)，手臂和 MAT 读 [ue5-fps-arms-animation](skills/ue5-fps-arms-animation/SKILL.md)。先参考现有动作，核对实际运行加载，再修改。
- 天气读 [ue5-weather-workflow](skills/ue5-weather-workflow/SKILL.md)，调试读 [ue5-debug-validation](skills/ue5-debug-validation/SKILL.md)。
- 保留动画时序、UI、库存、存档和并行修改。源码编译与真实运行验收分别报告。
- 唯一日常开发及 Git 工作目录为 `D:/FPS3D/FPSGAME`，直接从这里提交并推送 `origin/main`。本目录已有独立 `.git`，不依赖 E 盘仓库。E 盘旧仓库/发布副本已退出工作流；不要再建立常驻同步副本。并行修改精确暂存，保留未提交工作。
- 退役文件放 `trash/<task>/` 并记录散列。二进制资源及恢复边界见 [AssetSetup](Docs/AssetSetup.md)，未审核再分发许可的原始资源不公开提交。
