# 户外工作套装效果

2026-10-24 用户指定将工装裤、系带皮靴、厚皮革手套、野行奔尼帽、工装夹克组成「户外工作套装」。内部 ID 继续使用 `workwear`，五个实际装备槽 1、3、7、13、15 穿齐才启用。缺任一件时没有套装收益。

| 效果 | 计算 |
| --- | --- |
| 所有动作体力消耗 -15% | 原动作最终消耗 × 0.85 |
| 移动速度 +10% | 原移动倍率 × 1.10 |
| 饥饿下降速度 -25% | 原自然食物消耗速率 × 0.75 |
| 口渴下降速度 -25% | 原自然水分消耗速率 × 0.75 |

替换旧套装的防御 +5%、体力恢复 +10%、奔跑消耗 -10%，不叠加旧效果。单件防御、属性加成、价格、强化、外观、格子占用均不改动。例如厚皮革手套已有的近战节省继续保留，再乘本套装的 0.85；原本不耗体力的动作仍为零。

## 计算入口

`ColdSteelFormulaBonuses.cpp::SetEffect` 提供 `actionStaminaCost`、`speed`、`survivalConsumption`。使用现有只读物品缓存和实际装备状态，不新增每帧配置读取或持久化套装标志。

体力在各动作成本生成入口应用 `ActionStaminaMultiplier()` 一次，保持 `CanSpendStamina`、`SpendStamina` 和网络回执接受最终金额的约定：

| 消耗分支 | 接入位置 |
| --- | --- |
| 奔跑、持续重击蓄力 | `FPSStaminaModel.cpp`，本地与服务端影子档案共用 |
| 普通近战、单手刀、重击出手、空手／法杖拳击 | `MeleeWeaponStats.cpp`，武器执行器及面板使用相同套装倍率 |
| 普通格挡、蟠螭格挡 | `BlockStamina(Modifiers, Profile)`，先算成本再判断破防 |
| 采集、工具攻击、战锤轻重击 | `ProductionToolStats.cpp`，兼顾无物品回退；战锤分支从已折算的近战成本派生，不重复乘 |
| 闪避、快速近战 | `ColdSteelSkillModel.cpp` 的成本函数 |
| 升龙斩、旋风斩、冲刺攻击 | 各 `ColdSteel*Model.cpp` 的技能成本生成函数 |
| 弓箭 | `BowStats.cpp` 的服务端／面板值和 `BowWeaponComponent::LooseArrow` 的本地即时成本 |

格挡、战锤、升龙斩、射箭及快速近战的网络扣费／退费继续使用已经结算的数额，收到回执后不会按当时装备再折算。持续蓄力面板同步使用实际速率。

移动加速复用 `CombatMoveMultiplier()`，覆盖现有步行、奔跑、瞄准移动和蹲行入口。武技独立动作时钟、攻击速度不变。

食水在服务端 `FPSSurvivalComponent` 的现有 0.25 秒调度中读取对应玩家档案，将 0.75 放入原有分段消耗倍率。清泉赐福、营火、SAN 归零以及天气日长倍率继续相乘；耗尽时刻与饥渴损血的分段计算使用相同速率。SAN 自身衰减、食物恢复量与增益持续时间不变。

## 接入和交付

物品表和战斗覆盖表仅更新五件成员的 `armorSet`、`setName`、`setBonusDesc`，入口为 `Tools/WorkwearSet/publish_outdoor_effects.py`。原完整模型发布器同步使用新名称／效果。旧存档沿 `ColdSteelProfileRuntime.cpp` 已有的五件物品字段刷新读取当前名称和套装说明，不改写单件数值。

五件套元数据已实际写入，`SourceAssets/OutdoorWorkSet20261024/published.json` 为 `completed: true`；原始物品表保存在同目录 `Before/`，本次仅发布套装三个字段。

Editor 与 Game 两个后台构建均已完成，`build-FPSGAMEEditor.json`、`build-FPSGAME.json` 的 `exit_code` 均为 0；未启动编辑器或游戏。

构建与发布回执位于 `SourceAssets/OutdoorWorkSet20261024/`。本次完成开发和必要后台构建，不主动启动游戏、运行测试或联机验收；实际穿齐、拆件和动作效果由用户测试。
