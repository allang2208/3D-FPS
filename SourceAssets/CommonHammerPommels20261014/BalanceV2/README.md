# 柄尾配重用户最终数值与武技冷却

> 2026-10-15 整理：本文为制作阶段记录；Before 快照已带散列移入 trash。最终发布状态和恢复入口见[整理说明](../../../Docs/Publication/WarhammerMods20261015/README.md)。

| 柄尾配重 | 物理伤害 | 攻击速度 | 攻击体力消耗 | 韧性伤害 | 武技冷却时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 八棱镇击配重 | +5% | -5% | +5% | +10% | — |
| 镂笼灵巧配重 | -5% | +10% | -10% | — | — |
| 双盘平衡配重 | — | — | -20% | -10% | -20% |

正式目录与 `BuildV1/catalog.py` 已同步；`apply_balance.py` 写入三款属性及相同来源的能力说明。`Before/` 保留改动前数据与本次修改文件快照，不能整体还原这些快照覆盖并行修改。

## 武技冷却实现

新增 `FMeleeModifiers.MartialCooldown`，默认 1，目录字段为 `martial_cooldown_mult`。战锤及近战目录加载该字段，改造汇总按部件相乘。`MartialCooldownMultiplier()` 返回 `SkillCooldown * MartialCooldown`。

大旋风 `WhirlwindStats` 与上挑 `SwordUppercutCooldownSeconds` 消费该乘积，包括战锤作为当前生产工具装备时的分支。原有释放资格、服务端冷却提交、冷却总时长快照、Profile 同步与技能／快捷栏读数继续使用这两个共用入口。

双盘单独装备：武技冷却 ×0.8。与共鸣符文搭配：×0.8×0.85=×0.68，冷却缩短 32%。法术保留原 `SkillCooldown * MagicCooldown` 口径，不消费 `MartialCooldown`。普通攻击间隔、蓄力和武技动作播放速度不因新字段改变；没有独立冷却的动作不新增计时器。

改造详情、总览、物品浮窗和摘要显示“武技冷却倍率”，与“所有技能冷却倍率”分别表达其直接修饰范围。配置能力说明为“武技冷却时间 -20%”。无模型、图标和资产重导入。

## 构建与测试边界

本次新增 C++ 字段及消费点，需完成相应原生目标构建。Game 目标已后台构建成功（107 项构建动作，215.54 秒，`FPSGAME.exe` 已更新）。Editor 目标因正在运行的 UE 后台资源进程持续占用而未启动构建；已结束本任务自己的等待进程，未停止、关闭或重启占用者。Editor DLL 尚未更新，待占用释放后仍需构建 `FPSGAMEEditor`。实际边界记录在本目录 `delivery.json` 和构建回执中。

后续状态更新：同日的战锤符文柄面调整已完成当前 Editor 目标构建，返回 `Succeeded`／`Target is up to date`，上述待构建事项已解除。最终回执见 `SourceAssets/WarhammerCommonRunes20261014/ShaftWrapV2/editor-build-receipt.json`；本目录的原始 `editor-build-receipt.json` 仍保留当时占用记录。

未运行检查、自动测试、游戏、联机或验收渲染；最终效果由用户测试。
