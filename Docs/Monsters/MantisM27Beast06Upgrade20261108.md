# 螳螂 M27：Beast06 首批动作与飞扑升级计划

最新回退：用户反馈普通攻击仍别扭，已根据最初接入回执恢复正式普通攻击 **ClawV16**；正式飞扑保持 **PounceV11**。原 Beast06 与 ArmChainV15 对比角色的普攻也已恢复。后续调整直接基于旧 ClawV16，见 [回退与 ClawV17 局部候选](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27ClawRollbackAndV17_20261109.md)。以下新源重建与固定刀弧修订均为历史方案，不继续作为本轮普攻制作基底。

2026-11-09 更新：用户确认地面普攻与飞扑挥镰都僵硬，当前新增 [ArmChainV15 完整臂链候选](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27ArmChainV15_20261109.md)，分别连接两个普攻与三个飞扑片段，移除预设刀弧对肩部的强制朝向覆盖。正式角色仍保留回退后的引用。以下版本、诊断及八阶段方案是历史过程，不作为用户已经认可的动作模板。

2026-11-08。按用户本次要求进行了动作制作、离线模型检查和升级规划。首批是可供对比的候选版本；飞扑部分本次完成诊断与细分方案，尚未改动运行时飞扑。

后续更新：用户反馈攻击僵硬后，已制作并导入 [左攻击 Beast06V2](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27Beast06V2LeftAttack20261108.md)，现有对比蓝图的左攻击引用已更新。本文以下 GIF、测量和首批说明保留为 **V1 历史记录**，不代表 V2 的表现或验收。

最新反馈与回退：用户检查后认为 PounceV12 不如旧版。正式 F6 螳螂与原 Beast06 对比蓝图的三个飞扑引用均已恢复 **PounceV11** 并保存，左右攻击仍为 [Beast06V2](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27Beast06V2Pair20261108.md)。[PounceV12](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV12EightPhases20261108.md) 为用户否定的历史方案，不作为成功模板；回退记录见 `SourceAssets/MantisM27/PounceV12/rollback_to_v11_receipt.json`。新的 [PounceV13 局部节奏候选](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV13LocalTiming20261108.md) 从 V11 的密集原始姿态制作，正式角色保持 V11。

最新优化重点：用户补充 V12 的退步在于双镰挥击速度和力度，已据此制作 [PounceV14 下劈候选](D:/FPS3D/FPSGAME/Docs/Monsters/MantisM27PounceV14Strike20261108.md)，只重排 V11 空中下劈的蓄势、快速释放与制动节奏。V13 作为原局部节奏候选保留；正式角色仍为 V11。

## 已落盘的首批结果

来源为用户已接入的 [SciFi Beast06 Bull](https://www.fab.com/listings/126120a3-996e-4dc3-94f1-6550f0adac03)。使用现有 BindingV2 网格、骨架、蒙皮，先做 UE 原生 IK Rig / IK Retargeter 重定向，再按螳螂长刃与足部支撑进行适配。

| 候选 | 参考 | 时长 | 本次调整 |
|---|---|---:|---|
| LeftSlash | Attack1 | 0.65 秒 | 将参考的骨盆、脊柱、肩带、头部发力以 35% 权重融入 ClawV14；保留整条手臂、真实刃面与内弧方向 |
| RightSlash | Attack6 | 0.65 秒 | 独立使用 Attack6 的发力节奏，没有简单镜像左侧；保留 ClawV14 的右臂切削链 |
| HitF / HitB / HitL / HitR | GetHitF / B / L / R | 各 0.80 秒 | 适配到螳螂准备姿势，保留各自躯干反应，限制长刃碰地与双刃重叠，补回准备姿势 |
| Idle | Idle1 | 6.667 秒 | 提取呼吸、头颈和肩部细动，降低幅度并保持脚部支撑与循环闭合 |

攻击仍使用 0.25–0.30 秒接触窗。源动画与目标共用一条非线性时间映射；没有给肩、肘、腕分别设置不同播放速度。攻击原生重定向的第一版产生了过大的长刃修正，单帧最高约 125°，已淘汰，没有接入任何角色。最终攻击候选保留用户认可的 ClawV14 手臂结构，仅吸收适合螳螂的身体发力。

UE 资产目录：`/Game/Monsters/MantisM27/Beast06V1/Animations`。

另存的对比角色为 `/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1`，已连接左右攻击、待机、正面受击。可将该蓝图放入测试关卡与原螳螂对比。正式 `BP_MantisM27` 及 F6 登记仍沿用原版；四方向受击的自动选择尚未实现。

制作源：[Delivery](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Delivery)。保存记录：[ue_receipt.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/ue_receipt.json)。工具：[Beast06V1](D:/FPS3D/FPSGAME/Tools/MantisM27/Beast06V1)。

![左右攻击候选，循环间加入短暂停顿便于观察](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/AttackPair.gif)

[正面受击](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/HitF.gif) · [背面受击](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/HitB.gif) · [左侧受击](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/HitL.gif) · [右侧受击](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/HitR.gif) · [待机](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/Idle.gif)

## 本次检查结果

检查范围是源资产、实际制作网格的离线逐帧姿态、足部关节连续性、保守刃面包围点以及 UE 导入保存。预览使用实际 BindingV2 网格，左右刃分别标为绿、紫色；未启动 UE 编辑器、PIE 或游戏。

| 项目 | 结果与含义 |
|---|---|
| 最终攻击主刃最大单帧角度，60 fps | 左 25.47°，右 25.83°，峰值在 0.25–0.267 秒的切削阶段；ClawV14 参照为 25.92° / 25.83° |
| 最终攻击脊柱最大单帧角度 | 左 11.13°、右 11.41°；ClawV14 为约 19.56°。身体转动更平缓，切削速度仍保留 |
| 最终攻击刃面保守包围点最低高度 | 左候选 15.83 厘米，右候选 16.48 厘米；这是制作空间平地测量，不代表坡地或游戏内无穿模 |
| 7 段候选脚关节最大位置漂移 | 约 0.0021 厘米，属于离线固定支撑求解结果，不等于运行时地面验收 |
| 待机首尾姿态差 | 最大约 0.04°，呼吸循环闭合 |
| UE 导入 | 7 段 AnimSequence 与对比蓝图均已保存；骨架仍为 BindingV2 |

原生重定向 commandlet 在全部输入保存后，退出阶段曾触发 UE 动画压缩任务断言。后续独立 commandlet 已重新打开全部 10 个 Raw 输入，并成功导入最终候选、保存对比蓝图、以退出码 0 结束。日志保留在本版本源目录，未通过强制结束其他进程处理。

当前检查不包含身体各表面的完整碰撞审查、实战命中、声音同步、地形适应或联网验收。这些不能由离线渲染与导入成功代替。

## 飞扑发现：先修支撑与切段

当前 `PounceV11` 为蓄力 0.60 秒、飞行 0.65 秒、落地 0.80 秒，之后代码还有 0.25 秒恢复。代码使用 `LaunchCharacter` 控制真实位移；服务端 `Landed` 触发伤害、落地声音与效果，飞行动画时间则按预计飞行时长映射。

| 现状 | 本次实测 | 优先处理 |
|---|---|---|
| 起势突变 | 蓄力第 3 个采样间隔，左刃约 29.81°/帧，时刻约 0.05 秒 | 重做最初 0.12 秒的连续起势；整臂四元数同半球插值，保留刃面约束 |
| 蓄力转飞行 | 左/右脚位置差 26.84 / 46.30 厘米；右脚角度差 54.19° | 离地前脚仍支撑，第一帧腾空继承离地姿态，之后再收腿 |
| 飞行转落地 | 骨盆位置差 35.06 厘米；左/右脚差 72.33 / 44.55 厘米 | 飞行末尾提前伸腿，统一落地首帧骨盆和双脚位置，消除模型内高度跳变 |
| 刃口切段 | 离地时约 7–8°；落地时左 3.79°、右 10.07° | 连同肩肘腕和刃面一起匹配，不只对齐刀尖 |
| 动画混合 | 飞行入口 0.04 秒、落地入口 0.14 秒 | 不单纯延长混合掩盖脚位差；先让源姿势连续，再选择混合时长 |

这些距离是相邻动画端点在同一模型空间的原始差值，尚未叠加角色世界位移和动画混合，不应描述成游戏中必然瞬移同样距离。

![当前飞扑关键帧，第一行为正面，第二行为侧面](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/PounceV11/pounce_contact_sheet.jpg)

## 飞扑细分方案

先保留现有总时长与战斗平衡，在三个动画内部细分八段，不必新增八个网络状态。表中时间均为所属片段的局部时间，是下一版的制作起点。

| 段 | 局部时间 | 身体与刀刃处理 | 参考价值 |
|---|---|---|---|
| 1. 锁定、起势 | Windup 0.00–0.12 | 从当前准备姿势逐渐前倾，头部先锁定，肩带随后启动，消除早期急转 | 现有螳螂准备姿势；不照搬牛怪站姿 |
| 2. 下蹲蓄力 | Windup 0.12–0.42 | 髋膝共同压缩、足掌支撑、双刃逐渐举起；保留轻微左右差异 | JumpStart 源约 0.00–0.33 秒的压缩节奏 |
| 3. 蹬地离地 | Windup 0.42–0.60 | 髋膝踝逐级伸展，重心前移，最后一个地面帧再解除足锁 | JumpStart 源约 0.33–0.45 秒；不复制其后整段骨盆上升 |
| 4. 腾空收腿 | Flight 0.00–0.18 | 首帧与离地末帧连续，之后才收膝、脚向后折；刀刃保持上举 | JumpStart 源约 0.45–0.667 秒的关节相对姿态，去掉整体升高 |
| 5. 空中蓄势 | Flight 0.18–0.34 | 身体保持前向猎扑，头部稳定，收腿幅度轻微变化，避免悬空静止感 | JumpLoop 的短段；无需强行播完 0.667 秒 |
| 6. 下劈与伸腿 | Flight 0.34–0.65 | 肩带带动整臂非线性加速；内弧朝向切削速度；末段伸腿准备触地，收敛到落地起始姿势 | 保留 PounceV11 的螳螂整臂下劈；牛怪没有足够对应的长刃动作 |
| 7. 触地缓冲 | Land 0.00–0.16 | 触地帧脚、骨盆与飞行末帧匹配，膝髋吸收冲量，刀刃制动；伤害继续以实际 Landed 为准 | JumpEnd 源约 0.33–0.56 秒的压缩关系，剥离整体下降 |
| 8. 回弹收势 | Land 0.16–0.80 | 单次小回弹后衰减，双刃回防、重心回到可移动位置；接现有 0.25 秒恢复门控 | JumpEnd 源约 0.56–0.667 秒回弹 + 螳螂准备姿势 |

JumpStart 的骨盆从首帧到末帧上移约 131.8 厘米，JumpEnd 则下降约 131.8 厘米，且下降过程中包含更深的压缩。必须区分角色整体运动与关节相对运动，不能整段直接叠加到胶囊弹道上。参考源的左、右脚落地时间也不完全一致，要按螳螂支撑关系重新拟合。

不同高度或提前碰撞会改变真实触地时刻。下一版先保证标称 0.65 秒弹道的连续端点；随后处理提前落地时从当前实际姿态转入缓冲、延迟落地时保持可延长的空中段。伤害、音效与落地特效仍跟随服务端同一次真实接触，不因新增动画分段而重复或延后触发。

## 后续执行顺序

| 顺序 | 交付 | 涉及范围 | 完成判断 |
|---|---|---|---|
| 已完成 | Beast06V1 七段候选、对比蓝图、离线预览 | 本次独立版本目录 | 已导入保存；正式版本未切换，游戏内表现尚待用户测试 |
| 下一步 P1 | PounceV12 连续性修复 | 新 `SourceAssets/MantisM27/PounceV12` 与对应制作、导入工具 | 先交付起势、离地、落地衔接；明确原始端点与混合后表现，保留 PounceV11 回退 |
| P2 | 飞扑八段精修 | 同一 PounceV12 制作源；必要时限定修改 `MantisM27Pounce.cpp` 的表现时间映射 | 收腿、下劈、伸腿、压缩、回弹各有明确阶段；真实位移仍由移动组件负责 |
| P3 | 四方向受击运行时选择 | M27 受击入口及既有反应事件的数据传递 | 按实际来袭方向选择 F/B/L/R；方向与反应事件同步到客户端；保留招架、破韧和击倒优先级 |
| 后续 | 选定候选接入正式蓝图 | 仅 M27 动作引用 | 按选定动作替换，不顺带修改伤害、移动速度、隐身规则或其他怪物 |

当前 `MantisM27Monster.cpp::StartHitPresentation` 传入固定 `-GetActorForwardVector()`，而共享战斗组件仍提供单个 `HitClip`。当 `BeginHitReaction` 收到非空动作时会直接播放该动作，所以只替换方向向量或只导入四段素材都不能实现四方向选择。后续需要明确来源坐标与受力方向的正反关系，并与反应事件一致复制，不能只在服务端替换未复制的 `HitClip` 引用。

RunV4、隐身逻辑、伤害数值、刷怪登记和死亡/布娃娃保持当前基线。Death2 含明显位移，且 M27 当前死亡入口直接进入物理，优先级低于这次的攻击、受击和飞扑。

## 依据与复现入口

遵循 [ue5-monster-workflow](C:/Users/allan/.codex/skills/ue5-monster-workflow/SKILL.md)、[M27 专项规则](C:/Users/allan/.codex/skills/ue5-monster-workflow/references/mantis-m27.md) 与 [移动与足部支撑规则](C:/Users/allan/.codex/skills/ue5-monster-workflow/references/m-series-locomotion.md)：成熟动作优先、原生重定向后做形体适配、完整手臂关系、真实刃面和曲刃方向、非线性分段时序、来源/Raw/适配结果分层保存。

本次授权的检查记录为 [motion_inspection.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/motion_inspection.json)、[fit_metrics.json](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/fit_metrics.json) 和 [候选关键帧](D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1/Inspection/Candidates/candidate_contact_sheet.jpg)。预览、检查脚本仅在需要对应工作时执行；本次未进行游戏、联网或音画验收。
