**全局用户规则（2026-09-12）：所有工作默认不主动进行检查、测试或验收，由用户自行测试；仅用户明确要求时执行。此规则覆盖本项目文档、SKILL 及引用文档中的默认验证要求。必要的开发、构建与接入照常完成，交付时如实说明未测试。**

# 当前开发方向

当前工程为根目录 `FPSGAME.uproject`（UE 5.8.2）。用户已指定后续全面转向 UE5；Godot 只作为归档参考。完整本机宿主为 `D:/FPS3D/FPSGAME`，Git main 的当前源码直接位于根目录，不再仅发布 `unreal/<topic>` 摘录。

- 开发和发布先读 [WORKFLOW.md](WORKFLOW.md)，仓库整理、归档与推送遵守第 8 节。
- 枪械读 [ue5-weapon-workflow](skills/ue5-weapon-workflow/SKILL.md)，手臂和 MAT 读 [ue5-fps-arms-animation](skills/ue5-fps-arms-animation/SKILL.md)。先参考现有动作，核对实际运行加载，再修改。
- 天气读 [ue5-weather-workflow](skills/ue5-weather-workflow/SKILL.md)，调试读 [ue5-debug-validation](skills/ue5-debug-validation/SKILL.md)。
- 新建或改造面板、页签、栏目、卡片与弹窗，先读 [面板与栏目工作流](UI-WORKFLOW.md) 和 [UE UI 技能](skills/ue5-ui-umg-slate/SKILL.md)，按 [规划模板](Docs/UI/panel-column-plan-template.md) 明确结构、响应布局、数据范围、状态和交互，再按授权阶段制作／接入。
- 冷钢 UI 以 [正式设计规则](Docs/UI/ui-cold-steel-design-system.md) 为准：黑灰低透明度玻璃、Noto Sans SC／JetBrains Mono、统一按钮；冲突的旧字体、配色和抽屉条款由该文替换。共享 `ColdSteelUIStyle`，不再复制近似主题。
- 非枪械物品（药水、材料、弹药包装、卷轴）的图标、三视图、5080 模型、材质与稀有度光效读 [ue5-item-asset-workflow](skills/ue5-item-asset-workflow/SKILL.md)。
- 保留动画时序、UI、库存、存档和并行修改。源码编译与真实运行验收分别报告。
- 唯一日常开发及 Git 工作目录为 `D:/FPS3D/FPSGAME`，直接从这里提交并推送 `origin/main`。本目录已有独立 `.git`，不依赖 E 盘仓库。E 盘旧仓库/发布副本已退出工作流；不要再建立常驻同步副本。并行修改精确暂存，保留未提交工作。
- 退役文件放 `trash/<task>/` 并记录散列。二进制资源及恢复边界见 [AssetSetup](Docs/AssetSetup.md)，未审核再分发许可的原始资源不公开提交。
