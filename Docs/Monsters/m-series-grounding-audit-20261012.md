# M 系列活体接地排查（2026-10-12）

后续状态：用户要求全面处理后，已完成对应源码接入与 Editor / Game 后台构建，详见 [活体接地补齐记录](m-series-grounding-implementation-20261012.md)。以下保留修订前的排查证据；运行画面仍待用户测试。

范围：当前 `DevelopmentSpawnComponent.cpp:28–45` 正式刷怪目录中带 M 编号的 12 类角色。鼓囊 M-09 作为上一轮修正基线，其余 11 类为本次排查对象；其中 3 类为职员，8 类为其他异形。悬钟 M-09 和鼓囊 M-09 是不同角色。

本轮排查源码、动画图接入与正式资产配置，不运行游戏、关卡、动画预览或画面验收，不修改怪物行为。脚本 `Tools/Monsters/audit_m_series_grounding_20261012.py` 仅读取类默认对象、网格、骨名和动画资产，结果目录为 `Saved/MSeriesGroundingAudit20261012/`。

## 结论

**没有全部完成。** 当前源码中有 7 类缺少活体逐足地形适配，2 类已有适配但存在明确的覆盖缺口，2 类已有相应的地面或天花板接触系统。上述数量不含上一轮刚加入四足接地的鼓囊。

| 对象 | 已有工作 | 当前缺口 / 判定 | 优先级 |
|---|---|---|---|
| 涡电匣 M-25 | 胶囊跨阶、整体网格高度对齐、爬行动画分层 | 缺少逐足落点、脚底朝向和身体支撑面修正；大跨度脚位不能分别适应台阶 | 高 |
| 螺柱 M-14 | 胶囊跨阶、底部包围盒对齐、根足动画、死亡软体 | 缺少活体根足地形适配；死亡摊地不负责活体站立/爬行 | 高 |
| 盲祷者 M-07 | 动画过渡脚底高度保持、击倒起身接地 | 未持续采样左右脚下的场景地面；混合纠偏不能适应两脚高差 | 中 |
| 螳螂 M-27 | 扑击落地下肢姿势、静态高度对齐、起身纠偏 | 缺少站立/行走时的双足地形解算及骨盆补偿 | 中 |
| 接待员 M-04、安保员 M-03、研究员 M-05 | 共享移动组件与职员动画播放器 | 三类都缺少持续双足地形解算；可走楼梯不等于双脚贴合踏面 | 中 |
| 缚群 M-88 | 十足高度采样、腿链 IK、站立脚锁、触须避地 | 无按支撑面调整身体高度/倾斜的解算；足端达到伸展上限后不能继续够到低台阶；保留原脚掌旋转，未贴合地面法线 | 高，补齐已有系统 |
| 伏窥者 M-08 | 四接触点、身体偏移/俯仰、脚锁补步、攀墙支撑；气炮和扑击部分阶段接入 | 普通 `AttackBite` 不在接地启用条件内；有地面支撑时进入撕咬也会关闭该节点 | 高，补齐状态覆盖 |
| 沉匣 M-10 | 八足 IK、脚底几何与法线、身体支撑面、腹部避穿、脚锁及补步 | 已有完整主干。复杂楼梯与简化碰撞不一致时仍需关注采样面；本轮不能认定所有高差都不会悬空 | 保留现有系统 |
| 悬钟 M-09 | 双手天花板 IK、接触法线、顶面高度跟随、失去抓点后死亡下落 | 属于悬挂生物，无地面脚部接地要求；源码中已有对应天花板接触机制 | 保留现有系统 |
| 鼓囊 M-09（基线） | V15 四足独立场景采样、身体支撑与腹部保护、多骨段腿链解算 | 本轮确认代码分支仍在；上一轮制作尚不代表已获游戏画面验收 | 由用户体验 |

## 关键依据

### 1. 共享“楼梯接地”处理的是角色整体移动

`MonsterCharacterMovementComponent.cpp:33` 的 `ConfigureWideBodyStairs` 调整跨阶和导航规格；`:94` 的 Tick 通过 `ApplyMeshOffset` 平滑整体网格跨阶位移。它不查询每只脚的落点、不调整膝/肘弯曲，也不拟合身体支撑面。

2026-10-06 的 `m-series-ground-traversal-20261006.md` 已记录这类胶囊与导航修订。应保留该工作，但不能把“已能跨过 40 cm 台阶”当作“所有脚已适应台阶”。

### 2. M-25 / M-14 的活体图中没有地形解算

- `M25AnimInstance.cpp:10–53` 的图仅为 Idle/Crawl → Bite → Hit → Death 混合；`:95` 附近的 `IsMovingOnGround()` 只用于运动状态。`VortexCofferM25.cpp:79–90` 按网格包围盒底部做固定高度对齐。
- `SpiralPillarM14.cpp:60` 使用 `UFatZombieAnimInstance`；`:71–94` 的 `ApplyVisual` 计算根足攻击端点与固定底部高度。根足端点用于攻击判定，并非按场景落点变形。
- `FatZombieAnimInstance.cpp:93–145` 的图包含姿势混合、受击上身旋转和 `RecoveryGround`，没有持续的逐足地形节点。M-14 的软体接触属于死亡流程。

### 3. M-07 / M-27 / 三类职员不能用“Ground/Support”命名判断完成

- `BlindSupplicantAnimInstance.cpp:53–95` 的 `SupportHeight` 计算的是两份动画姿势的脚底蒙皮最低点；混合后只修正 root Z，没有场景地面查询，也没有左右脚独立目标。
- `MantisM27Monster.cpp:34–64` 只做固定网格对齐并使用 `UFatZombieAnimInstance`。共享播放器的 `FMonsterGroundedTransition` 让落地混合采用落地片段的下肢，不负责当前台阶形状。
- `NurseZombie.cpp:132–153` 对三类无面职员使用同一播放器；三个角色都要单独核对骨名与脚底厚度，不能直接套鼓囊的四足链。
- `MonsterRecoveryGroundNode.cpp:13` 仅在 `Knockdown->GetRecoverySupport` 有效时启用，用于起身整体防穿地，不能替代日常行走接地。

### 4. M-88 已有足端修正，缺的是身体与脚掌配合

`BoundCongregateAnimInstance.cpp:68–84` 每秒最多采样 15 次，十只脚只保存命中 Z。`:148–169` 附近将目标限制在腿链长度的 98%，求解后恢复原脚掌旋转。

所以跨多级台阶时，低处足端若超出腿长，目标会在接触地面之前被截断；需要由身体前后支撑补偿共同解决。`BoundCongregateWhipDrive.h` 的身体偏移是攻击驱动，`BoundCongregateTentacleGround.h` 的避地作用于触须，二者都不是十足行走的身体地形支撑。

### 5. M-08 的普通撕咬明确退出接地

`LurkerM08ContactNode.cpp:88–100` 仅接受：无动作的地面移动、气炮、扑击/跨越的指定时间段。`AttackBite` 不满足条件，直接清空身体修正并退出。

`WolfMonster.cpp:354` 的攻击播放选择普通撕咬 `AttackBite`；M-08 构造中也配置了普通撕咬范围和伤害。因此这是状态覆盖的代码缺口，不能用“行走已有四足 IK”概括为全部完成。应保留撕咬的身体发力和主动抬肢，只让承重肢体继续适应地面。

### 6. M-10 与悬钟保留已有机制

- `M10AnimInstance.cpp:35,68` 确实串接并更新 `FM10FootPlantNode`。`M10TerrainFeet.cpp:63–111` 以 20 Hz 采样八足和三个腹部点，拟合身体支撑面；`M10FootPlantNode.cpp:57–125` 包含身体变换、脚底朝向和脚锁。身体倾斜限制为 22°，高度补偿范围 -80～60 cm，这些是保护限值，不是任意高差均可贴合的保证。
- M-10、M-08、M-88 当前地形探测均使用 `bTraceComplex=false`。若场景楼梯简化碰撞是整块斜坡，足端会跟随该斜坡而非每级可见踏面。是否发生要看具体楼梯碰撞；本轮未读取场景全部楼梯碰撞，不将其列为已复现缺陷。
- `M09CeilingRoute.cpp:17–47` 使用复杂场景碰撞寻找天花板下表面并排除 Pawn；`HangingBellM09.cpp:305–396` 处理抓点法线、身体高度跟随与支撑失效；`M09AnimInstance.cpp:12–48` 对双手执行 IK。它与地面悬空缺陷应分开判定。

## 建议的后续制作顺序

1. **补齐 M-25、M-14。** M-25 采用多足支撑与身体高度/坡面配合；M-14 采用根足和底盘适配，控制主体倾斜，保留柱状轮廓。
2. **补齐 M-88、M-08 的已知缺口。** 前者增加身体承重补偿与脚掌方向；后者让普通撕咬等有支撑动作保留接地，区别承重肢与攻击肢。
3. **补齐 M-07、M-27 和三类职员。** 共用双足适配思路，分别配置骨链、脚底和弯曲方向，加骨盆高度补偿，保留扑击腾空及布娃娃的控制权。
4. **统一场景表面采样规则。** 只接触场景，不把角色/怪物当踏面；按脚底覆盖范围采样、选择可站立表面，并按距离降低查询频率。复用现有主线程限频采样、动画线程读缓存的方式。

以上是修复清单，本轮没有实施这些行为变更；也没有进行视觉、性能或网络运行验收。

## 正式资产读取状态

第二次后台 commandlet 已正常完成，退出码 0，12 类均完成读取，没有逐类读取异常。首次尝试因编辑器模块在后台构建期间暂不可用而退出；第二次曾等待引擎自带的 SDK 检查，随后自行完成。没有为本次排查修改模块、跳过 SDK 检查、启动 GUI 编辑器或保存游戏资产。

| 对象 | 正式动画播放器 | 实际引用网格 | 参考骨数 |
|---|---|---|---:|
| 接待员 M-04 | 类默认 AnimClass 空；职员状态播放时由原生代码设为 `FatZombieAnimInstance` | `SK_FacelessReceptionist_V05` | 161 |
| 安保员 M-03 | 同上 | `SK_FacelessSecurity_V13` | 161 |
| 研究员 M-05 | 同上 | `SK_FacelessResearcher_V05` | 161 |
| 盲祷者 M-07 | `BlindSupplicantAnimInstance` | `SK_M07_BodyMotionV18` | 83 |
| 螳螂 M-27 | `FatZombieAnimInstance` | `SK_MantisM27_BindingV2` | 38 |
| 伏窥者 M-08 | `LurkerM08AnimInstance` | `SK_LurkerM08_CanineV03` | 70 |
| 悬钟 M-09 | `M09AnimInstance` | `HangingBellM09/V04/SK_M09` | 114 |
| 涡电匣 M-25 | `M25AnimInstance` | `SK_M25_VortexCoffer_Game_V01` | 148 |
| 沉匣 M-10 | `M10AnimInstance` | `SK_M10_SurfaceRig_V5` | 62 |
| 螺柱 M-14 | `FatZombieAnimInstance` | `SK_M14_SupportSkin_v15` | 49 |
| 缚群 M-88 | `BoundCongregateAnimInstance` | `SK_BoundCongregate_TentacleReachV29` | 119 |
| 鼓囊 M-09 | `QuadrupedTemplateAnimInstance`，原生图按鼓囊类型接入专属节点 | `SK_BellowSacLobber` | 33 |

补充核对结果：

- 12 类所用网格均未设置后处理动画蓝图，没有一套在网格层补做接地的隐藏后处理图。
- M-08、M-10、M-88、悬钟和鼓囊的接触节点所需腿/手骨名均存在于实际引用网格参考骨架中；本轮没有发现这些节点因参考骨缺失而整体失效的情况。未评估游戏中的逐 LOD 活动骨裁剪。
- M-08 正式 AnimationSet 确实配置 `AttackBite`，指向 `A_M08_AttackBite_BoneheadV04`；普通撕咬未被接地条件覆盖并非仅存在于闲置代码。
- 悬钟和缚群的类默认 Mesh 组件尚未赋网格，但 `VisualMesh` 有正式资产；各自 `OnConstruction` / `BeginPlay` 调用 `AlignVisual` / `ApplyVisual` 完成赋值，不能把类默认组件空值误报为模型未接入。

原始完整路径、标签、动画条目与骨名：`Saved/MSeriesGroundingAudit20261012/asset-bindings.json`。压缩汇总与缺失骨集合：同目录 `binding-summary.json`。这次确认的是源码和磁盘正式资产绑定，不是现场楼梯画面的运行验收。
