# 双棱尖头锤：用户数值 V2

> 2026-10-15 整理：本文为制作阶段记录；Before 快照已带散列移入 trash。最终发布状态和恢复入口见[整理说明](../../../../Docs/Publication/WarhammerMods20261015/README.md)。

2026-10-15，按用户给定表格及“攻击时附带15%的物理防御穿透”更新。

| 属性 | 改造值 | 配置 |
| --- | --- | --- |
| 物理伤害 | +30% | `physical_damage_mult = 1.30` |
| 攻击速度 | +5% | `attack_speed_mult = 1.05` |
| 攻击体力消耗 | +15% | `stamina_mult = 1.15` |
| 韧性伤害 | −25% | `toughness_damage_mult = 0.75` |
| 物理防御穿透 | +15% | `physical_armor_penetration = 0.15` |

## 接入

`BuildV1/catalog.py` 和正式共享目录 `Content/ColdSteelData/common-hammer-heads.json` 的 `pointed_hammer` 同步更新。穿透作为直接常驻属性进入既有属性卡、总览和物品提示，按零基数百分比显示 15%，不使用伤害倍率的减一公式，也不在特效栏重复列出。

`WarhammerGunsmith.cpp` 补充读取现有 `FMeleeModifiers.PhysicalArmorPenetration` 字段；汇总沿用已有加法与 0–100% 上限。`ColdSteelSkills::Snapshot` 已在近战攻击快照中读取该值，战锤普攻、重击／冲刺砸地及旋风／升龙的出手路径沿用同一快照；地面冲击波复制该次出手快照。没有把该属性实现为额外物理伤害或概率触发。

`apply_balance.py` 只发布本选项的数值与属性文案，`Before/` 保存修改前的正式目录、作者数据及目录读取源码。`balance_receipt.json` 记录用户数值；V1 记录保留为历史。模型、图标和材质无需重导。

Game Development 构建成功：3 个动作、23.90 秒。现有编辑器在编译前已退出，因此完成了常规 Editor 构建：241 个动作、304.09 秒，`UnrealEditor-FPSGAME.dll` 已更新。构建回执分别为 `game-build-receipt.json` 和 `editor-build-receipt.json`；本轮也补齐此前陨星熔核冲击波范围改动的基础 Editor DLL 构建。

没有主动启动或关闭编辑器，未进行游戏、联机或视觉测试。下次进入游戏时读取更新后的目录数值。
