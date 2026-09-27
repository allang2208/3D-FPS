# 锻造成品浮窗说明

## 目的与结构

在现有冷白装备鉴定浮窗内说明锻造造成的差异。悬停摘要保留各武器原有核心参数，在其后加入「锻造品质」「锻造伤害修正」两项；点击固定后的「改造与附魔 → 锻造工艺」显示有效命中、工艺倍率、作用范围及品质说明。未锻造的物品不增加字段。

沿用 UMG 共享浮窗与 `ColdSteelUIStyle`，正修正绿色、负修正红色、零修正中性；锻造品质不冒充稀有度或强化等级。摘要两列／窄窗单列、纵向滚动、视口限位与固定关闭入口保持现有行为，不新增焦点或输入生命周期。

## 数据与计算范围

读取该物品实例保存的 `_forgeQuality.label / multiplier / hits / total`，不重新计算历史锻造结果或修改存档。倍率与运行伤害同样限制在 0.75–1.25。摘要与详情复用同一组字段，已有模型变化事件刷新，不加 Tick、资源读取或新缓存。

百分比标注为「锻造伤害修正」，作用于基础伤害公式；不能误写为所有物理分项或总伤害同幅增加。附加伤害按各自公式结算，按基础伤害比例派生的分项仍跟随其基数。现有伤害公式说明同步乘入实际工艺倍率，并明确面板伤害已经包含该修正，无需玩家二次相乘。

## 修改范围与交付

`ColdSteelWeaponText.h`、`ColdSteelItemTooltipData.cpp`、`ColdSteelItemTooltipFormula.cpp`。不改变锻造评分、伤害平衡、装备对比算法或领取／废弃流程。

源码已完成，通过现有编辑器的互斥 MCP 批次完成 Live Coding，返回 `Result: Success / Live coding succeeded`；回执为 `Saved/forge-tooltip-livecompile-20260927.txt`。随后在编辑器关闭后，随铸造台写实升级完成 `FPSGAMEEditor Win64 Development` 常规构建，基础 Editor DLL 已更新，日志为 `Saved/BuildEditor/casting-realism-20260927.log`，结果为 `Succeeded`。按用户规则未启动游戏、截图或测试，由用户体验浮窗。
