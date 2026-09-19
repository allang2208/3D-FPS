# 当前开发方向（2026-09-10）

后续开发转向 UE5，当前本地工程 `D:/FPS3D/FPSGAME/FPSGAME.uproject`（UE 5.8.2）。先确认实际 `.uproject`，使用对应 UE5 技能；下方 Godot 专项规则用于维护旧原型或作为迁移参考，不代表新工作仍应写入 Godot。天气读 `skills/ue5-weather-workflow/SKILL.md`，运行诊断读 `skills/ue5-debug-validation/SKILL.md`。源码快照与完整工程的区别见 [unreal/README.md](unreal/README.md)。

本次或后续任务确认淘汰的文件移入 `trash/<task>/`，保留原路径、大小、SHA-256 清单；只整理任务范围内文件。推送继续执行 WORKFLOW 第 8 节。

# 当前 UI 指令（2026-09-07）

新建、审计或翻新UI先读 [冷钢玻璃标准](docs/apple-glass-ui-standard.md)、[面板流程](UI-WORKFLOW.md) 与对应项目技能。唯一当前方向：冷钢炭灰银白 + 玻璃外壳 + 宋体SimSun face0、embolden0.5、额外字距0；数字保留Consolas，图标字体独立。参数见 `ui/apple-glass-tokens.json`。

背包保留45%全高、15装备槽、18列×4行初始72格、长枪5×2与药水1×1。枪械改造全屏；公共主题和玩家功能面板已接入冷钢玻璃与加粗宋体；实际覆盖见全局审计报告。不得从历史快照恢复旧字体/蓝紫主色。原项目只读，保留并行修改，不把规则更新当全局运行换肤完成。

# 枪械与改造

枪械开发、枪匠配件、瞄具/ADS、枪口、弹匣、枪托和枪械材质工作，先读 [枪械技能](skills/godot-weapon-workflow/SKILL.md)。涉及改造时必须读取其 ADS 与改造案例；通用瞄具复用、闭锁校准、透明镜片、活动挂点、原件替换和实例保存按同一合同验证。提交及推送遵守 WORKFLOW.md 的仓库整理规则。

# 怪物制作与迁移

怪物建模、绑骨、动作优化、数值和游戏接入工作，先读取 [怪物标准工作流](skills/godot-monster-workflow/SKILL.md)。其他开发仍遵守 WORKFLOW.md 的职责边界。

用户于 2026-09-06 指定：制作每个动作前，先实际查看已有 2D 动画或源视频，并读取时长、循环、接触帧与状态配置；记录关键姿态、重心和左右差异后才制作 3D 动作。

普通僵尸已获得游戏接入及测试授权。后续怪物按各自授权阶段推进，不能把本次授权泛化成所有资产的接入批准。

# 冷钢 UI 与面板开发

开发或调整游戏UI、HUD、背包/仓库及字体时，必须先读 [冷钢UI技能](skills/godot-cold-steel-ui/SKILL.md)、[当前规则](docs/cold-steel-ui-standard.md) 与 [面板工作流](UI-WORKFLOW.md)。以当前冷钢玻璃标准为视觉基准；优先公共字体入口，不另造字体方案。原始参考快照保持不变。


枪械改造页面与配件说明改动，先读 [最终格式合同](skills/godot-weapon-workflow/references/gunsmith-ui.md)。该合同取代早期字体分工及重复对比/解释段落格式。

# 昼夜、天气与事件预报

添加或优化天气先读[天气技能](skills/godot-weather-workflow/SKILL.md)及[标准工作流](docs/weather-development-workflow.md)，事件进度栏保持当前用户确认格式；清理和推送按WORKFLOW第8节。

# 体素与建筑

玩家可建造体素先读 [体素标准](VOXEL-WORKFLOW.md) 和 [体素技能](skills/godot-voxel-workflow/SKILL.md)；基地、模组拼接及建造系统先读 [建筑工作流](BUILDING-WORKFLOW.md) 和 [建筑技能](skills/godot-building-workflow/SKILL.md)。面板继续使用冷钢UI规则，发布遵守WORKFLOW第8节。


2026-09-07 全局运行升级：公共Style及项目默认均为加粗宋体，玩家面板复用冷钢玻璃。覆盖与验证见 `docs/global-ui-audit-2026-09-07.md`；新增页面执行 `tests/test_global_ui.gd` 与 `tests/test_ui_tokens.gd`。运行截图/测试同时设置独立 INVENTORY_SAVE_PATH、GAME_SETTINGS_PATH，避免改变玩家设置。
