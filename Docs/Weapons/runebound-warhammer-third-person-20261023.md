# 符文战锤第三人称动作排查

2026-10-23。用户确认第一人称可见，本次只排查符文战锤是否继承锻钢战锤现有的第三人称表现。不启动游戏、PIE、截图或渲染。

## 结论

当前源码和正式配置中，两款武器都使用 `Tool / warhammer`，没有符文战锤专属的动作分流遗漏。`player_body.json` 内的 39 个战锤角色映射引用 21 份独立动画包，所引用的 `.uasset` 文件均存在。两者共享下面列出的原有动作、握持和同步逻辑。本次没有修改第一人称、战斗参数、动画包或共享身体配置，无需重新编译。

“共享原有动作”不代表所有操作都有独立第三人称素材；装备和检视的具体边界见表。源码与资产排查也不等同于实机姿态、穿模或联机观感验收。

## 逐项对照

| 操作 | 当前第三人称接入 | 符文战锤与锻钢战锤 |
| --- | --- | --- |
| 站立持握 | `Warhammer.Idle` / `FullBody.Carry`，SourceGripV16 | 同一资源与分支 |
| 八方向步行、跑动 | `Warhammer.Walk.*` / `Jog.*`，SourceGripV16；方向混合、步态相位和实际移动速度驱动 | 同一资源与分支 |
| 冲刺与就绪 | 共用跑动步态；SprintReady 表现标记；`FullBody.SprintCarry` 与 Carry 共用待机，不独立复制第一人称拖锤 | 相同 |
| 普通三连击 | Slash1/2 为 NaturalComboV17，Slash3 为 Slash3AlignmentV18 | 同一资源与分支 |
| 普攻命中回收、连段、收势 | ToolRecover 保留对应 Slash 素材；共享实际命中、连段进度及连续握持过渡；移动时腿部继续走实际步态 | 相同 |
| 蓄力、取消、重砸 | `FullBody.Charge` / `Slam`；共享 RefinementV8 第三段动作的蓄势及释放时间段 | 相同 |
| 冲刺举锤、冲刺砸击 | `FullBody.SprintLift` / `SprintSlam`；举锤保留移动腿部，释放继续同一素材 | 相同 |
| 上挑 | `FullBody.Uppercut`；RefinementV8 第一段素材，读取真实技能接触/冲刺阶段及受阻状态 | 相同 |
| 旋风 | `FullBody.Whirlwind.Start/Loop/End`，AnatomicalGripV7；整体武器与身体一起转动，读取技能旋转及停顿时钟 | 相同 |
| 格挡起手、保持、放下 | `FullBody.GuardEnter/Hold/Exit`；Exit 反向读取 Enter，取消起手也读取返回进度 | 相同；Exit 不是独立动画包 |
| 格挡受击、破防 | `FullBody.GuardHit/GuardBreak`；两者引用同一 GuardHit 包，使用各自动作进度 | 相同；破防不是独立动画包 |
| 快速近战 | `GunBash / WarhammerHeadThrust` → `FullBody.QuickMelee`，RefinementV8 | 相同 |
| 装备 | 状态发布 Equip；通用工具的实际手部采样与握持接管，没有 `Warhammer.FullBody.Equip` 专用全身动作 | 相同的既有实现 |
| 检视、行走检视 | 第三人称保持原生持锤及步态；冻结世界武器、握持和模块，第一人称检视轨迹不覆盖全身姿态 | 相同的既有实现；没有独立全身检视 |
| 左手施法、回握 | 读取实际魔法手势阶段；战锤持握保留在右手，左手施法后归位 | 相同的战锤家族分支 |
| 蹲伏、跳跃、下落、落地、闪避、滑铲、翻越、攀爬、死亡 | 通用身体/移动状态层；翻越、攀爬会让出持锤手部控制 | 相同的公共层，未新增战锤专用素材 |

## 实际执行链

- `Content/ColdSteelData/items.json`：两者 `tool_kind=warhammer`、双手标记、手臂网格、动画前缀和比例相同。
- `ProductionToolComponent.cpp`：按 Kind 加载战锤动作、握持资料及模块；并非只允许 `ue_steel_warhammer`。两者都隐藏手模内的原锤分区，以当前模块替代。
- `FPSPlayerBodyActions.cpp`：本地与远端权威状态都发布 `Tool / warhammer`。攻击、命中回收、蓄力、格挡、武技及快速近战读取真实执行器状态和时钟。
- `FPSPlayerBodyComponent.cpp`：从当前 `player_body.json` 加载映射到同一身体动画实例，没有为两款锤子分别复制旧配置。
- `FPSBodyWarhammerMotion.h` → `FPSPlayerBodyAnimInstance.cpp`：选择全身动画、读取接触/释放标记，保留连续握持、普通攻击腰胯衔接及移动腿部。V17/V18 普攻是当前正式映射。
- `FPSPlayerBodyMotion.cpp`：原生全身动作和持握使用冻结装备姿态，避免第一人称锤体再转一次；装备等通用状态读取实际手部姿态。
- `FPSPlayerBodyEquipment.cpp`：捕获当前模块、材质、局部变换及 WPN_root 挂点；世界副本只隐藏原手臂/被替换的原锤分区，复制当前锤体。`WarhammerModule` 不继承第一人称载体的临时隐藏状态。
- `FPSPlayerBodyNetwork.cpp` / `SampleRemoteAuthorityState`：共享装备实例、动作变体、进度及进度速率；两者使用同一武器家族身份匹配。此处只排查同步接线，没有运行联机测试。

## 模型与握持

`warhammer-modules.json` 与 `runebound-warhammer-modules.json` 使用相同的手臂网格、`drive_bone=WPN_root` 及 `bone_mount`（约 0.01，抵消导入骨骼的 100 倍比例）。原装握柄中心同为 Z=40.5 cm，柄尾同为 Z=-8.5 cm；符文锤头按自身模型放在 Z=91.6 cm，而锻钢锤头为 92.5 cm。使用现有手模建立双手握持，不按新模型包围盒重新缩放整套人物动作。

当前改造选项由符文战锤自己的模块表提供，第三人称捕获已经组装的真实组件，保留各零件变换和材质；不会在世界副本中重新套用锻钢锤头尺寸。

## 证据与剩余边界

证据目录：`SourceAssets/RuneboundWarhammer20261022/ThirdPersonRouting20261023/`。`source-snapshot.json` 记录本次读取的配置、源码摘要及动画文件存在性；`read_assets.py` 只用于通过既有互斥桥读取资产骨架、时长和动作标记，不启动或改变游戏，不保存 UE 资产。

UE 资产内部读回本次未完成：首次桥调用等待互斥窗口超时，未发送请求；第二次调用未发现可连接的编辑器 Python 节点，脚本未执行。因此没有 `asset-readback.json`，也不将骨架兼容性、动作标记或压缩后的姿态记为已确认。没有为此打开或重启编辑器。已完成的结论限于实际源码执行链、当前正式配置及所引用动画包的文件存在性。

本次排查未发现需修正的符文战锤专属第三人称接线缺口。游戏内双手贴合、锤头与身体穿模、各阶段过渡及远端玩家观感仍由用户体验确认。
