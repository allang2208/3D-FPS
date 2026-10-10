# 剑刃改造详情精简（2026-10-09）

用户授权调整通用延锋刃，并按 2026-10-08 配件详情规则同步精简其他剑刃改造。

- 延锋刃：物理通道 `physical_damage_mult=1.05`（基础与附加物理一起乘算，魔法附伤不变）、距离 `range_mult=1.15`、体力 `stamina_mult=1.05`；移除旧基础伤害字段及 `attack_speed_mult=0.9`。其他剑刃的数值不变。
- 范围：`blade_1` 全部剑刃选择共用精简显示规则。只列直接常驻属性，不重复展开总伤害、基础伤害带来的连击／重击伤害，或攻速带来的多项耗时。后续最终标准仅列直接属性，第三段等分段数值不再列出，详见 DirectAttributeDetails20261009。
- 延锋刃保留伤害、最大攻击距离、体力三张卡；重脊刃／阔锋重刃为伤害、攻速、硬直；轻羽刃为攻速、体力、格挡减伤；穿甲刃仅保留直接穿甲属性，不再展示第三段伤害／削韧。
- 竖劈、升龙及击飞规则进入目录 `special_effects`，绿色标题和正文；描述只保留外观。燕翎竖劈沿用实际矩形判定。
- 数据仍来自 `ColdSteelMelee::Evaluate` 对草稿／本槽原厂的比较；已安装／待应用、选择刷新、保存事务不变。未增加 Tick。
- 复用 UM4GunsmithWidget + Slate、ColdSteelUI／GunsmithUI 样式、原有右栏滚动和窄窗布局。整武器总览、底部操作、输入焦点与生命周期沿用现有实现。
- 正式目录：`Content/ColdSteelData/melee-gunsmith.json`；共享详情：`Source/FPSGAME/UI/M4GunsmithSelectedDetails.cpp`。阔锋、燕翎、腾云作者／重导入口同步描述和效果结构。
- 本次只做必要后台 Editor 构建；不启动编辑器或游戏，不进行测试、截图和验收，由用户测试。

- 物理倍率沿 MeleeGunsmith 解析、GunsmithSystem 聚合、WeaponDamagePanel 计算传递；近战面板与技能命中快照共用 DamageParts，无存档结构变更。

后台构建已完成：FPSGAMEEditor / Win64 Development，Result: Succeeded；日志 Saved/BuildEditor/build-20261009-095916.log。源码、正式配置及 Editor 二进制已落盘。未启动编辑器或游戏，未执行测试或验收。
