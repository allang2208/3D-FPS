# 四足怪物通用动作模板 V1

2026-09-14。UE 5.8.2，狼为首个母版。交付阶段为本机可复用动画资源、播放接口和骨链；本次不开展游戏测试、动作渲染或人工验收。

2026-09-25 用户确认裸皮感染犬 GodotRunNaturalV3“基本成功，可以作为四足犬科的模板了”。后续犬科奔跑优先参考该已认可版本及其直接适配方法，入口见 [NaturalV3 制作与复用](../../SourceAssets/InfectedDogMeshy20260924/GodotRunNaturalV3/README.md)。它使用 MeshyV2 的 41 骨目标绑定；下文原 WolfV1 的 34 骨资产继续作为历史来源，不能直接互换动画。新的提前量、接触范围与狩猎 AI 属于后续独立升级，记录见 [感染犬狩猎配置](InfectedDogHunting20260925.md)，不借用此次奔跑认可作为攻击验收。

## 来源与适用范围

[ANIMAL VARIETY PACK / PROTOFACTOR INC](https://www.fab.com/listings/2dd7964c-a601-4264-a53d-465dcae1644c) 包含乌鸦、狐狸、鹿、猪、狼五类动物，其中鹿分公鹿和母鹿。本机源资产位于 `/Game/AnimalVarietyPack`，具有模型、独立 Skeleton、Physics Asset、材质、贴图和动画。源文件的帧数、时长、Skeleton、Notify 名称与骨骼父链记录在 [source_catalog.json](../../SourceAssets/QuadrupedTemplates/source_catalog.json)。商品页动画数量与本机版本/原地及 RM 变体计数分别记录，不混为同一口径。

狼适合作为犬形捕食者的动作来源，狐狸适合作为较轻巧犬形来源；猪与鹿分别保留粗壮、蹄类分支。这里的“通用”指动作语义、数据结构和调用接口通用，不表示不同骨架能直接共享动画。公母鹿、狼狐也不能仅凭骨数相同宣布兼容。乌鸦不进入四足模板。

| 本机模型 | UE 动画文件数（含 RM 变体） | UE 骨数 |
|---|---:|---:|
| Wolf | 29 | 34 |
| Fox | 28 | 34 |
| Pig | 26 | 35 |
| DeerStag | 24 | 31 |
| DeerDoe | 22 | 31 |
| Crow | 17 | 61 |

狼源 Idle/Walk/Run 分别为 2.0/1.0/约 0.5333 秒；Bite 约 0.6667 秒、JumpBite 约 0.8333 秒、Howl 约 2.8333 秒、Death 约 2.0667 秒。源采样约 30 FPS。帧数采用从 T0 起的间隔数，采样键数为间隔数加一。商品页狼/狐写 33 骨，本机 UE 为 34 骨，按本机父链制作。

模板保留源动作的骨骼关键帧和原始时长，仅在独立副本中统一命名、关闭 Root Motion 并锁定容器根。此阶段没有重编动作或依据文件名填写接触帧；动作观感、足底相位和新体型适配均未验收。新增扑击、喷吐、角击等招牌动作前，仍须先实际观看源动画/视频，记录起势、四肢支撑、腾空、接触和收势。

来源页在本次读取时显示 `Allows usage with AI: No`；本次只使用本地 UE 资源制作流程，不上传到生成服务。领取许可证仍以账户内该资产条款为准；原包和生成的二进制模板保留本机，不据此授予独立再分发权。

## UE 资源入口

- `/Game/Monsters/QuadrupedTemplates/WolfV1/BP_QP_Wolf_Template`：可放置的动画模板 Actor。
- `/Game/Monsters/QuadrupedTemplates/WolfV1/DA_QP_Wolf_AnimationSet`：动作映射、走跑标称速度、循环相位和动作过渡配置。
- `/Game/Monsters/QuadrupedTemplates/WolfV1/Animations/A_QP_Wolf_<Action>`：21 个标准动作槽的独立动画副本。
- `/Game/Monsters/QuadrupedTemplates/WolfV1/Rig/IK_QP_Wolf_Source`：以狼实际骨链创建的四足源 IK Rig。新角色需要自己的目标 IK Rig 与 Retargeter。
- [template_manifest.json](../../SourceAssets/QuadrupedTemplates/template_manifest.json)：源→模板的资产路径、原始时长、循环/保持、移动归属及制作记录。

该 Actor 使用原生 `UQuadrupedTemplateAnimInstance` 和数据集驱动姿态，不依赖空白 AnimBlueprint，也不在图内复制怪物 AI。它没有伤害、寻路、碰撞战斗、掉落或刷怪逻辑，尚未接入村庄怪物。

## 标准动作槽位

| 动作 ID | 狼源片段后缀 | 模板行为 |
|---|---|---|
| Idle | IdleBreathe | 待机循环；自动移动混合的静止端 |
| IdleAlert | IdleAggressive | 警戒循环 |
| LookAround | IdleLookAround | 单次观察后回移动 |
| Walk | Walk | 行走循环；自动移动混合 |
| WalkTurnLeft / WalkTurnRight | WalkTurnL / WalkTurnR | 行走转弯循环，由调用方选择并负责转向 |
| Run | Run | 奔跑循环；自动移动混合 |
| RunTurnLeft / RunTurnRight | RunTurnL / RunTurnR | 奔跑转弯循环，由调用方选择并负责转向 |
| AttackBite | Bite | 原地咬击；一次 |
| AttackRunBite | RunBite | 奔跑咬击；位移由移动组件负责 |
| AttackPounce | JumpBite | 扑咬；腾空与位移由技能/移动组件负责 |
| HitFront / HitLeft / HitRight | GetHitFront / GetHitLeft / GetHitRight | 三个源受击槽；方向语义待实际观看后按攻击来向映射 |
| Howl | Howl | 单次嚎叫，不自动产生伤害/召唤/声音 |
| RestEnter | GoToRest | 播放完接 RestLoop |
| RestLoop | Rest | 休息循环 |
| RestExit | RestToGoBackUp | 起身后回移动 |
| SleepLoop | Sleep | 睡眠循环；没有伪造专用入睡/起床过渡 |
| Death | Death | 单次播到末姿态并锁定；不自动开启布娃娃 |

倒退、侧移、独立原地转身、起跑/急停、独立跳起/落地、后腿踢击、长期眩晕循环、翻身起立、喷吐和尾击不是本次已提供的源动作。不得把 WalkTurn 当成原地转身，把 JumpBite 当成任意跳跃，或将短受击无限拉长充当完整眩晕。

## 播放与时钟接口

模板 Actor 的 `ManualSpeed` 为 cm/s，默认 0；`bUseOwnerVelocity=false` 时方便用户手动改变速度观察动作，`InitialAction` 可填上表任一 ID，在 BeginPlay 播放一次。未设置时使用 Idle/Walk/Run 混合。这些设置不移动 Actor，也不在编辑器里自动启动动画。

蓝图调用链：模板 Actor 引用 → `Play Template Action(ActionName, ExternalClock=false)` → 读取布尔返回值。成功时从当前可见姿态过渡到所选动作；不存在的动作或死亡锁定状态返回 false。需要中断时调用 `Resume Locomotion`；Death 不可取消。重新生成实例开始新生命。

接入实际怪物：Mesh 使用 `QuadrupedTemplateAnimInstance` → BeginPlay 获取该 AnimInstance → `Set Animation Set(角色自己的数据集)` → 使用 `bUseOwnerVelocity=true`。Mesh 与数据集必须采用同一个目标 Skeleton。运行时不再调用 `PlayAnimation` 切走该 AnimInstance。

战斗调用链：现有 Behavior Tree/执行组件选择攻击 → `Play Template Action(Action, ExternalClock=true)` → 用现有唯一战斗时钟驱动 `Set Action Time(源动画秒)` → 到收势末端调用 `Resume Locomotion`。外部时钟模式不自动完成/切换动作，不另乘数据集 PlayRate。普通自动播放模式才使用 PlayRate。命中去重、遮挡、打断、死亡取消伤害仍归当前战斗系统；动画模板不施加伤害、不发送源包 Notify。

所有接触起止默认 `-1`（未编排）。设定真实窗口后采用半开区间 `[start,end)`；离散接触在上一时刻到当前时刻跨越事件点时消费一次。伤害窗口不能由总时长的固定百分比猜测。模板的位移策略固定为原地表现；原始 `_RM` 资产保留在源包，并在清单中关联，启用 RM 须另行定义唯一移动责任方。

自动移动图采用 Idle 与走跑混合；Walk/Run 共享归一化相位，可分别配置 `WalkPhaseOffset` / `RunPhaseOffset`。默认相位未做足底接触标定。母版走/跑标称速度 140/450 cm/s 为最初设计值，正式狼自己的数据集采用源根位移测得的速度。2026-09-15 [奔跑 V2](QuadrupedLocomotionV2.md) 将走跑转换阈值与标称速度解耦：35%–65% 跑速区间完成过渡，之后保持完整 Run；按每周期步幅推进相位，左右转向槽按平滑转向速度自动混合并保持同相位。新目标仍需适配自己的步幅和转向片段。

## 四足骨链与后续角色适配

2026-09-15 已开展首个完整狼角色接入，入口 `/Game/Monsters/Wolf/BP_WolfMonster`，F6 显示“野狼”。数值、AI、战斗时钟和三向受击使用角色自己的数据集，详见 [野狼接入说明](WolfMonster.md)。母版继续只承担动作表现；角色制作不等同于母版动作已获用户验收。

按父链映射 `BodyRoot`、`Spine`、`Neck`、`Head`、`Jaw`、`ForeLeg_L/R`、`HindLeg_L/R`、`Tail`；肩胛单独保留，耳等附件可使用独立短链。容器 Root 与承重骨盆分别记录，源 rig 的实际骨名以制作清单为准。脚尖/蹄端是支撑点，不能把前腿当人手、后腿当直腿人形，不能套用人形自动映射。

每个新模型复制数据集，依次完成目标骨链、参考姿态、源→目标重定向、体型修正，再填入同一批动作 ID。分别保留源动作、重定向原始结果与体型修正结果。修正重点是前后躯负重、肩胛滑动、前腕/后跗屈曲、四足接触顺序、腹部离地、尾部平衡、攻击器官轨迹和死亡落地。额外肢体/翅膀及招牌动作使用专用链与片段。

## 重建与交付边界

作者脚本：[read_source_catalog.py](../../Tools/QuadrupedTemplates/read_source_catalog.py) 读取原包；[create_wolf_template.py](../../Tools/QuadrupedTemplates/create_wolf_template.py) 创建缺失的模板资源。脚本不会启动关卡或动画预览，也不覆盖已有模板副本和用户调好的数据集。后续制作第二版时使用新目录和新名称。

原生实现：[QuadrupedAnimationTemplate.h](../../Source/FPSGAME/Monsters/QuadrupedAnimationTemplate.h)、[QuadrupedAnimationTemplate.cpp](../../Source/FPSGAME/Monsters/QuadrupedAnimationTemplate.cpp)。数据资产持有序列引用；AnimInstance 生命周期随 Mesh，姿态图只在游戏线程采集数据，再由原生代理求值。本版为单机表现模板，不含联机动作同步。

执行必要 Editor 构建后，在 UE Python 中运行制作脚本，或使用 `UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<脚本绝对路径> -unattended -nop4 -nullrhi`。这是资源制作命令，不是测试命令。二进制依赖原包；发布遵循 [AssetSetup](../AssetSetup.md)。

本次未测试、未试玩、未渲染验收；由用户测试。必要构建和资源生成结果记录在制作清单中，不据此声明滑步、衔接、IK、扑击接地、布娃娃或战斗已通过。

本次必要 Editor 构建已完成，日志为 `Saved/BuildEditor/build-20260914-235030.log`。资源制作命令完成，日志为 `Saved/QuadrupedTemplateCreate.log`；保存时有源 FBX 导入数据依赖的压缩提示，未追加运行验收。源目录读取曾遇到 MCP 本地 8000 端口占用，目录 JSON 已写出；该启动问题不写成动作测试结果。
