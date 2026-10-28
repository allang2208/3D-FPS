# 弯刀握柄显示修复与柄尾数值接入

2026-10-27，按用户本轮确定的数值制作。未进行游戏测试、静态检查或验收。

## 已保存的改动

- `WarhammerGunsmith.cpp` 的共享近战目录读取器也承接弯刀目录，原先遗漏 `martial_damage_mult` 和 `heavy_toughness_mult`，导致棱纹胶柄武技伤害、层压木柄重击削韧未进入计算及详情。本次补齐这两个字段和柄尾所需的三个快速打击字段。
- 握柄沿用此前用户确定的数据：棱纹胶柄武技伤害 +20%、攻击体力消耗 +10%；缠革握柄攻速 +10%、攻击体力消耗 −10%；层压木柄重击蓄力速度 +20%、重击削韧 +20%。
- 详情仍使用同一评估器，比较只将选中槽恢复原厂的配置；补齐重击蓄力卡的直接百分比，快速打击伤害卡显示目录的直接加成，右侧保留组合实值和实际差值。
- 弯刀总览补充已改造的快速打击伤害、削韧、击退和武技冷却。重击削韧与武技伤害随加载器修复进入既有展示路径。
- 旋风武技冷却使用当前出招武器的 `MartialCooldownMultiplier()`，修复单手弯刀被双手近战专用入口漏掉的冷却改造。上挑继续使用对应出招武器的既有评估器；快速打击的动作占用时间不作为技能冷却缩短。

## 柄尾数据

| 部件 | 直接属性 |
| --- | --- |
| 包钢柄尾 | 快速打击伤害 +30%；快速打击削韧 +25%；快速打击击退距离 +50% |
| 棱面柄尾 | 攻击速度 +10%；攻击体力消耗 −10% |
| 环纹柄尾 | 武技冷却 −10%；攻击体力消耗 −5% |

对应字段：`quick_combat_damage_add=.30`、`quick_combat_toughness_mult=1.25`、`quick_combat_knockback_mult=1.50`；`attack_speed_mult=1.10`、`stamina_mult=.90`；`martial_cooldown_mult=.90`、`stamina_mult=.95`。

数据已写入正式 `Content/ColdSteelData/shared-knife-component-options.json` 和重导入作者源 `SourceAssets/KukriComponentVariants20261026/shared-knife-component-options.json`。`apply_catalog.py` 只更新三款柄尾的 stats/effects，保留其他部件与美术配置。

双持沿用按武器实例计算的路径：双刀快速打击使用实际出招主手刀；手枪加副手刀的快速打击使用副手刀。两把刀的改造不合并进一套全局倍率。

## 编译交付状态

当前状态：源码与目录已保存，后续 `KukriAttackTiming20261027` 的常规 Editor 构建已成功，将本批修复编入 `UnrealEditor-FPSGAME.dll`。日志位于 `SourceAssets/KukriAttackTiming20261027/build-editor.log`。未启动游戏测试。

常规后台构建等待时发现当前 `UnrealEditor.exe` 占用项目模块，已停止本任务的等待进程，未关闭编辑器。

随后通过现有 MCP 批次互斥向已运行编辑器提交一次 `LiveCoding.CompileSync`。该次在 19:13:14 被 `Live Coding Action Limit Reached` 中止；编译器日志还记录提示窗口创建失败、结果为 No。桥脚本返回成功仅表示命令执行返回，不能视为补丁编译或加载成功。没有更改编译动作上限，也没有重放该请求。

上述热编译尝试时编辑器处于游戏运行状态，因此保留用户现场。后续在编辑器不再占用模块时，通过 `KukriAttackTiming20261027/build_when_available.ps1` 完成常规 Editor 构建，没有打开编辑器或游戏。当前没有留下自动等待构建任务。

`Before/` 为本轮修改前的精确文件副本。编译命令结果与日志摘要保存在同目录；未宣称运行时通过。
