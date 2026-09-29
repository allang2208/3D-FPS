# 钢甲护手装备属性

针对现有 `ue_steel_gauntlets`，按用户要求增加：

- 装备防御力 20，加入现有物理防御结算；未增加魔法防御或强化成长。
- 换弹速度 -10%，使用已有 `bonusStats.reloadSpeed = -0.1`。普通、空仓、逐发装填及双持手枪沿用共同的换弹公式、动作采样和机械事件时钟。
- 拉弓速度 -10%，增加 `bonusStats.bowDrawSpeed = -0.1`，只作用于弓的拉弓耗时。取箭、搭箭、箭速与其他武器攻击间隔保持原数值。

两项速度系数均为 0.9，耗时按原耗时除以 0.9，约延长 11.1%。与现有技能、武器附魔、改造倍率沿原公式组合。穿戴时生效，脱下后由装备属性重新聚合移除。

## 接入

`Content/ColdSteelData/source-combat-items.json` 是这三项数值的来源。`CombatItemFormula::Read/ReadOnly` 为没有数值字段的既有物品实例补齐目录默认值，因此之前制作阶段生成的钢甲护手无需删掉重领。没有改写玩家存档。

`Source/FPSGAME/Weapons/WeaponStatEvaluation.cpp` 的弓分支读取装备拉弓速度；弓运行时、物品提示、改造面板共用该公式。`ColdSteelItemTooltipData.cpp`、`ColdSteelItemTooltipSummary.cpp` 增加拉弓速度百分比显示；防御和换弹速度沿用已有显示。

本次未修改模型、材质、贴图、装备图标、动画、`items.json` 外观描述或模型导入器，保留用户另一会话完成的金属材质。

## 构建状态

数值和代码已落盘。编辑器关闭后执行 `Tools/Build/Build-Editor.ps1`，2026-09-28 13:44 返回 `Result: Succeeded` / `Target is up to date`，未创建 Live Coding 补丁。构建日志：`Saved/BuildEditor/build-20260928-134401.log`，调用日志：`Saved/steel-gauntlet-stats-build-20260928.log`。装备数值目录由进程缓存，下次启动将读取更新后的数值。

本次不主动启动游戏、不运行测试或验收，交由用户测试。
