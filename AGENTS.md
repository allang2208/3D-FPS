# 枪械与改造

枪械开发、枪匠配件、瞄具/ADS、枪口、弹匣、枪托和枪械材质工作，先读 [枪械技能](skills/godot-weapon-workflow/SKILL.md)。涉及改造时必须读取其 ADS 与改造案例；通用瞄具复用、闭锁校准、透明镜片、活动挂点、原件替换和实例保存按同一合同验证。提交及推送遵守 WORKFLOW.md 的仓库整理规则。

# 怪物制作与迁移

怪物建模、绑骨、动作优化、数值和游戏接入工作，先读取 [怪物标准工作流](skills/godot-monster-workflow/SKILL.md)。其他开发仍遵守 WORKFLOW.md 的职责边界。

用户于 2026-09-06 指定：制作每个动作前，先实际查看已有 2D 动画或源视频，并读取时长、循环、接触帧与状态配置；记录关键姿态、重心和左右差异后才制作 3D 动作。

普通僵尸已获得游戏接入及测试授权。后续怪物按各自授权阶段推进，不能把本次授权泛化成所有资产的接入批准。

# 冷钢 UI 与面板开发

开发或调整游戏UI、HUD、背包/仓库及字体时，必须先读 [冷钢UI技能](skills/godot-cold-steel-ui/SKILL.md)、[当前规则](docs/cold-steel-ui-standard.md) 与 [面板工作流](UI-WORKFLOW.md)。用户认可的枪械改造字体是所有新面板基准；优先公共字体入口，不另造字重或字号方案。原始参考快照保持不变。

枪械改造页面与配件说明改动，先读 [最终格式合同](skills/godot-weapon-workflow/references/gunsmith-ui.md)。该合同取代早期字体分工及重复对比/解释段落格式。

# 昼夜、天气与事件预报

当前 UE5 迁移项目添加或优化昼夜、天气、雨雪、积水、闪电与雷声时，先读
[UE5 天气技能](skills/ue5-weather-workflow/SKILL.md)。维护旧 Godot 实现时仍读
[Godot 天气技能](skills/godot-weather-workflow/SKILL.md)及
[旧标准工作流](docs/weather-development-workflow.md)。事件进度栏保持当前用户确认格式；清理和推送按 WORKFLOW 第 8 节。

# 体素与建筑

玩家可建造体素先读 [体素标准](VOXEL-WORKFLOW.md) 和 [体素技能](skills/godot-voxel-workflow/SKILL.md)；基地、模组拼接及建造系统先读 [建筑工作流](BUILDING-WORKFLOW.md) 和 [建筑技能](skills/godot-building-workflow/SKILL.md)。面板继续使用冷钢UI规则，发布遵守WORKFLOW第8节。
