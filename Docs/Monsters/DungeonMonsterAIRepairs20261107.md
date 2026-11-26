# 随机地牢怪物 AI 修复（2026-11-07）

承接 [同日检查记录](DungeonMonsterAIReview20261107.md) 的 A1、A2、A3。当前修改仅涉及原生源码和构建入口，保留怪物攻击数值、动画资产、地牢布局及螳螂已有的受困反击。

## 通用追击与堵塞反馈

`MonsterPursuitNavigation.cpp` 接续原 `MonsterAIController.cpp` 的 NavigateTo：

- 停步半径扣除目标投射到导航网格的水平偏移，防止偏移量叠加成额外攻击距离。
- AlreadyAtGoal 仍对照真实目标距离和楼层高度；不再仅凭导航返回值认定已经接近。
- 投影点不可用、路径失败或刚被堵住时，在真实目标停步范围内选择其他接近点。候选必须在同一楼层高度窗口、具备胶囊空间，MoveTo 拒绝部分路径。
- 保留每只怪物 0.65 秒的请求间隔。备用选点最多每帧两批，每批最多八个候选投影、两次路径请求；常规行进中的有效请求继续复用，没有新增 Tick、定时器或世界 Actor 扫描。
- 通过请求 ID 接收通用追击的完成结果，记录 Blocked、OffPath、Invalid；攻击、受控、替换请求产生的 Aborted 不记为堵塞。
- 失败目标保留两秒。大厅职员缓存及候选过滤按失败请求的目标位置回避，不再只看一个没有移动完成反馈的布尔值。控制器重新接管 Pawn 时重置该记录。
- 专用螳螂/兽类追击、隐身撤离、M08 表面移动与 M09 顶棚路径继续使用各自逻辑。

## M14 联机攻击表现

`SpiralPillarM14.h/.cpp` 使用 FM14PlaybackState 复制状态、服务端开始时间和动作序号；现有公开 State 保留为蓝图和 C++ 读取视图。

- 服务端独占状态切换和伤害结算。客户端 OnRep 恢复当前状态，并按 GameState 的服务端时钟计算进度；资源初始化前收到的状态在 BeginPlay 后呈现。
- 同类动作再次发生时由序号区分；中途进入相关范围不再从零播放完整前摇。
- 攻击动画在接收状态时立即采样当前进度，后续 Tick 继续跟随服务端时钟。
- 状态音效从当前进度接续，已结束的声音不重播。吐液释放使用单次标记，避免时钟校正重复触发；接收时已越过释放点的动作不补播释放声。
- 每个复制字段独立反射。本次改变原生复制布局，需要常规基础 DLL 构建；不使用 Live Coding 作为交付。

## 落盘范围

- `Source/FPSGAME/Monsters/MonsterAIController.h/.cpp`
- `Source/FPSGAME/Monsters/MonsterPursuitNavigation.cpp`
- `Source/FPSGAME/Dungeons/FacilityHallTraffic.cpp`
- `Source/FPSGAME/Monsters/SpiralPillarM14.h/.cpp`
- `Source/FPSGAME/Monsters/SpiralPillarM14Attacks.cpp`
- `Tools/Dungeons/build_monster_ai_repairs_20261107.ps1`

构建入口沿用现有 UE 批次命名互斥与外部 UBT 等待方式，默认只构建 FPSGAMEEditor，不打开或关闭编辑器。日志和构建回执放在 `SourceAssets/DungeonMonsterAIRepairs20261107/`。

## 交付状态

源码已落盘，`FPSGAMEEditor Win64 Development` 后台构建已成功。最终回执 `SourceAssets/DungeonMonsterAIRepairs20261107/build-FPSGAMEEditor.json` 为 `exit_code=0`；日志 `build-FPSGAMEEditor-20261107-004928.log` 为 `Result: Succeeded`，12.62 秒。共享工作区此前已完成依赖编译，本次最终 UBT 确认 `Target is up to date`，执行 0 个新增构建动作；不将其描述为本轮又重编译了一遍所有模块。

初轮日志 `build-FPSGAMEEditor-20261107-004146.log` 记录了两个局部变量重名错误。后续共享工作区已分别使用 `PawnCharacter` 和 `CrossSection` 消除冲突，本轮保留这些修正，没有改动火焰护甲玩法。

没有启动 UE、游戏、自动化测试、性能采样或双端联机，也未构建独立 Game/Server 或打包目标；实际表现交由用户测试，不将 Editor 构建成功等同于体验验收。

检查记录中的多人目标优先级、旧目标死亡后的转火、M08 弱网跳跃表现和运行时品阶元数据属于另列的风险/行为调整项，本批未改变这些行为。
