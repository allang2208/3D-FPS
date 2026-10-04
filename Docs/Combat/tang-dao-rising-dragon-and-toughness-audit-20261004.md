# 唐刀游龙刀身：升龙接入与韧性审计

日期：2026-10-04。项目：`D:/FPS3D/FPSGAME`。

后续更新：用户已批准精英以上的三阶段韧性条及按物种调参，见 [怪物分档韧性条](monster-toughness-phases-20261004.md)。该轮源码同时修复下方第 4–7 项（倒地与显式眩晕时钟、客户端眩晕期限、权威韧性条同步）；第 1–3 项仍保留。以下结算规则和构建状态是升龙这一轮的历史快照，后续状态以新文档为准，未进行运行验收。

本次按用户要求修改游龙刀身，并对韧性、破韧、击倒、眩晕及联机结算做源码与配置审计。没有启动编辑器、PIE、游戏、渲染或自动化测试；本文的审计结论来自代码路径，不代表运行时验收结果。

## 已实施的游龙效果

- 对象：唐刀 `ue_tang_dao` 的 `blade_1 / tengyun_dragon`，显示名“腾云游龙刀身”。
- 攻击速度乘以 **1.10**。
- 普攻第三段替换为 **升龙**，复用当前 `Uppercut` 动作、上挑轨迹、镜头和刀光；保留普通三连击的段数、体力扣除和攻击队列。
- 准备动作时长乘以 **0.50**，通过时间映射连续播放全部准备姿态，不跳帧到出刀。出刀与收招仍按普通攻击速度播放。
- 伤害为 **原普通第三段公式 ×1.30**；其他配件的第三段倍率继续叠乘。不调用上挑技能伤害公式，不扣上挑技能体力、不触发其冷却或修炼。
- 升龙命中存活敌人后强制击飞，不要求打满韧性；绕过普通击退／击倒免疫标签，保留场景碰撞。人形与手怪复用其击倒恢复系统，其他角色使用受击中断及胶囊体发射。悬吊类零重力角色的冲量限时结束并恢复此前移动模式，避免持续漂移；实际位移仍会被天花板阻挡。
- 击飞在统一权威伤害入口处理。远端命中由服务端按装备刀身和第三段语义重建效果，不上传“强制击飞”布尔值。致死命中交给原有死亡表现。
- 枪匠比较、选件详情、背包说明同步显示升龙、第三段伤害及动作耗时。

当前上挑源动画准备为 1.00 秒、全长 2.05 秒。升龙准备为 `0.50 / 普攻速率` 秒，全长为 `1.55 / 普攻速率` 秒。例如仅应用游龙的 1.10 攻速时，分别约 0.455 秒、1.409 秒。这是公式说明，没有运行计时测试。

核心入口：

- [改造数值](../../Content/ColdSteelData/melee-gunsmith.json)、[第三段类型](../../Content/ColdSteelData/tang-dao-modules.json)。
- [普通连击快照](../../Source/FPSGAME/Weapons/RuneSwordComponent.cpp)、[准备时间映射](../../Source/FPSGAME/Weapons/RuneSwordRisingDragon.h)、[动作推进](../../Source/FPSGAME/Weapons/RuneSwordUppercut.cpp)。
- [统一命中入口](../../Source/FPSGAME/Skills/ColdSteelSkillModel.cpp)、[强制击飞](../../Source/FPSGAME/Monsters/MonsterMeleeKnockback.cpp)。

## 韧性目前如何结算

`削韧 = 实际扣血量 × 攻击形式系数 × (1 − 对应抗性) × 攻击削韧倍率 × 目标易削韧倍率`

形式系数：锐器 1.00、钝器 1.60、冲击 1.25。抗性在公式中钳制为 0～90%。减伤后的实际伤害进入削韧，因此暴击、目标防御和伤害易伤都会间接影响破韧速度。

`Toughness` 保存的是“累计削韧量”，从 0 开始；达到阈值后破韧，清零并增加破韧次数。一次超过阈值的余量不结转。连续超过恢复时间未被有效削韧命中后全部清空，并非逐秒恢复。

普通阶级基线（[定义](../../Source/FPSGAME/Monsters/MonsterCoreStats.cpp)）：

| 类别 | 阈值 | 破韧硬直 | 锐／钝／冲抗性 | 恢复时间 |
| --- | ---: | ---: | --- | ---: |
| 轻装 | 60 | 1.2 秒 | 15%／0%／10% | 2 秒 |
| 重装 | 110 | 1.4 秒 | 0%／20%／25% | 2.5 秒 |
| 施法 | 80 | 1.2 秒 | 10%／0%／25% | 2 秒 |
| 犬科 | 50 | 1.1 秒 | 0%／10%／5% | 1.5 秒 |
| 巨物 | 150 | 0.9 秒 | 10%／5%／20% | 2 秒 |

杂鱼／普通／精英／领主／首领的阈值倍率为 0.7／1／1.3／1.6／2，硬直时长倍率为 0.85／1／1.15／1.3／1.5。高阶怪物更难破韧，但破韧后的窗口也更长；这属于当前数值设计。

虎啸路径已接通：快速近战本次伤害结算后施加 6 秒状态，期间三种韧性抗性按 0 处理，削韧再乘 1.25；重复命中刷新时长，不叠成多层。以其他倍率均为 1、实际扣血 100 为例，虎啸中的锐／钝／冲削韧分别为 125／200／156.25。附加状态本身仍经过状态免疫门槛。

## 本轮修复的关联问题

**联机第三段、重击／上挑缺少动作专属削韧倍率。** 原服务端只重建武器的通用 `ToughnessDamage`，遗漏客户端追加的 `ComboThirdToughness`、`HeavyToughness`。本次在[服务端命中快照](../../Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp)补齐，使升龙沿用第三段削韧合同；普通第三段和重击也得到相同修正。

**普通击倒接口不等同于强制击飞。** 原接口只给人形与手怪执行物理击倒，M09 返回成功但只有受击中断，其他类型可能直接返回失败。本次为升龙新增专用接口，保留旧重击接口的既有行为；强制路径不会清除之前的显式眩晕期限。

## 仍存在的审计问题

下列为现存问题记录，本轮没有扩大为整个控制／联机系统重构。

1. **P1：服务端没有验证真实三连击进程。** [ValidateHitReport](../../Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp)校验装备、令牌桶、距离、遮挡和时间戳，但未维护第一／第二／第三段顺序，也未校验攻击形式枚举与武器动作的对应关系。持有游龙刀身的修改客户端可以直接申报第三段，绕过前两刀触发升龙；其他形式／动作上报也有同类信任问题。应由服务端动作记录确认段数、释放时刻与命中形式。当前正常客户端仍按三连击运行。

2. **P2：联机快速近战与弹反强化仍有削韧倍率遗漏。** [快速近战](../../Source/FPSGAME/Weapons/RuneSwordComponent.cpp)将削韧倍率设为通用倍率乘快速近战倍率；[弹反强化](../../Source/FPSGAME/Weapons/RuneSwordClovenGuard.cpp)额外乘 `ClovenToughness`。服务端现有路径不重建这两项。本次补齐的是普通第三段和重击／上挑，不代表所有攻击已完成单机／联机一致性修复。弹反强化还需要可信的弹反令牌，不能仅凭装上护手就对所有重击追加倍率。

3. **P2：联机破韧硬直时长遗漏配件倍率。** 本地剑命中外层通过 `ApplyHitWithReactionScale(SwingHitReactionMultiplier, ...)` 传入 `hit_reaction_mult`；[服务端直接结算](../../Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp)没有重建这一层。通用削韧数值可正确，硬直时长仍可能不同。应按服务端装备和对应动作恢复该倍率，不能接受客户端任意传值。

4. **P2：旧击倒路径会清掉已有显式眩晕。** [ReceiveKnockdown](../../Source/FPSGAME/Monsters/MonsterMeleeKnockback.cpp)成功后清零 `ExplicitStunUntil`。人形的击倒调用还没有按已有眩晕剩余时间延长控制，因此长眩晕可能被较短击倒截断。升龙的新接口已避开这处；旧重击接口尚保留原行为。

5. **P2：已倒地人形接收眩晕时漏登记眩晕状态。** [ReceiveStun](../../Source/FPSGAME/Monsters/MonsterMeleeKnockback.cpp)中，手怪分支调用 `RegisterExplicitStun` 后延长倒地；护士及其人形派生分支只延长倒地就返回。两类怪物受到相同眩晕时，显式眩晕标记和计时口径不一致。

6. **P2：远端旧眩晕时长可能在普通受击时重新应用。** [RegisterExplicitStun](../../Source/FPSGAME/Monsters/MonsterStunPresentation.cpp)把 `NetStunSeconds` 保留为历史较大值；[OnRep_HitReactions](../../Source/FPSGAME/Monsters/MonsterCombatComponent.cpp)在每次反应计数变化时按“当前时间＋该旧时长”更新显式眩晕。普通破韧也会增加反应计数，因而远端可能出现错误的眩晕剩余时间或表现。应复制服务端到期时间／独立眩晕版本，避免将受击事件当作眩晕刷新事件。

7. **P2：远端韧性条没有权威数值来源。** [命中反馈](../../Source/FPSGAME/FPSGAMECharacterCombatFeedback.cpp)直接读取怪物组件的 `Toughness` 和 `ToughnessThreshold`，[准星信息卡](../../Source/FPSGAME/UI/ColdSteelCrosshair.cpp)据此绘制。组件只复制反应／眩晕状态，没有复制累计韧性，客户端 `ReceiveHit` 又直接返回；命中回执也不携带韧性数据。因此主机可能正常削韧，而远端韧性条仍显示 0 或过期数据。应同步累计韧性与实际阈值，或让命中回执携带权威快照并明确恢复更新规则。

## 容易误判为故障的现有规则

- 枪械默认 `hit_stagger=false` 时，既不硬直，也不累积削韧、不刷新削韧恢复时钟。给目标施加虎啸不会绕过这道门槛。见[枪械门槛](../../Source/FPSGAME/Skills/ColdSteelSkillModel.cpp)和[受击入口](../../Source/FPSGAME/Monsters/MonsterCombatComponent.cpp)。
- 倒地期间 `ReceiveHit` 直接返回，不继续积累韧性；升龙的强制击飞在伤害之后独立执行，不依赖该入口是否积累削韧。
- 常规状态跳伤通过反应倍率 0 结算，避免持续毒／灼烧每跳都打断；这也使这些跳伤不积累削韧。
- 已注册怪物在 `BeginPlay` 用“类别×阶级”表覆盖韧性编辑属性，直接修改实例阈值／三抗可能在开局被覆盖。

## 交付状态

配置、C++ 和说明已落盘，沿用已有上挑动画资产，无新增待导入资产。

- **Game Development 最终构建成功**，包含本轮全部源码修改。产物：`Binaries/Win64/FPSGAME.exe`；日志：game-build-final.log（本机构建记录：`Saved/Diagnostics/RisingDragon20261004/game-build-final.log`）。第一次 Game 构建遇到并行写入的门交互函数声明／实现不一致；待声明补齐后重新构建成功，没有修改门交互文件。
- **Editor Development 首轮构建成功**，升龙主体已写入 `Binaries/Win64/UnrealEditor-FPSGAME.dll`；日志：editor-build.log（本机构建记录：`Saved/Diagnostics/RisingDragon20261004/editor-build.log`）。随后追加的 `HumanoidKnockdownComponent.cpp` 一处修正（强制重新击飞已倒地目标、物理预算不足时，先准备动画胶囊体的碰撞空间）已进入 Game 产物，**尚未进入基础 Editor DLL**。
- 收尾时已有 `UnrealEditor.exe` 会话占用该项目，按用户 AGENTS 规则保留现场，没有关闭、重启或对该会话执行热补丁。编辑器正常退出后仍需一次常规 `FPSGAMEEditor Win64 Development` 增量构建，以更新上述最后一处修正。当前编辑器内存状态未验证。
- 未运行游戏或自动化测试，实际动作、不同怪物的击飞与联机表现由用户测试。

构建日志目录：`Saved/Diagnostics/RisingDragon20261004/`。
