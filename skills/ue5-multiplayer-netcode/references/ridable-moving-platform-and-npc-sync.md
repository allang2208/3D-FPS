# 可站立移动载具（马车/平台）与随车 NPC 联机零抖动规范

本页沉淀自 `LumberMillOps-R62`（`ALumberMillTimberWagon` 可乘载改造与双端审计），适用于任何允许房主与联机客机站立乘行的移动马车、渡船、升降台及随车 NPC。

## 1. 稳定子对象碰撞与无阻登车

1. **禁止把烘焙的粗包围盒静态网格当作乘载地板**：将外观 `UStaticMeshComponent` 降为 `QueryOnly`（仅留 `ECC_Visibility` 射线命中），改由挂在根组件下的**定名 `CreateDefaultSubobject<UBoxComponent>`** 承载 `ECC_Pawn`（均设 `ECC_Camera = ECR_Ignore` 防撞镜头）。定名默认子对象可满足 `MovementBaseUtility::UseRelativeLocation() == true`，双端自动走基座相对坐标复制。
2. **走上式阶梯与变载托升**：尾步辅助台阶相邻高度差全部 `<= MaxStepHeight`（本项目为 `40 cm`，例：`0 → 36 → 72 → 95 cm`），玩家既可步行登车也可起跳上车；货床在空载/满载间抬升时，先扫描已立足或位于货斗内的 `ACharacter` 并同步托升到新顶面，防止卡入货物；同时核验满载站人总高低于沿线城门/闸门净空。

## 2. 双端零抖动 Tick 顺序与 180° 掉头保护

1. **强制载具先于乘车角色 Tick**：`UCharacterMovementComponent::SetBase` 内置的 `AddTickPrerequisiteComponent(NewBase)` 只约束地板组件自身的 Tick，不约束驱动根位移的**载具 Actor Tick**。必须设载具 `PrimaryActorTick.TickGroup = TG_PrePhysics`，并遍历 `PlayerControllerIterator` 为当前 `Cast<UPrimitiveComponent>(CMC->GetMovementBaseObject())->GetOwner() == this` 的玩家动态调用 `CMC->AddTickPrerequisiteActor(this)`（离车与 `EndPlay` 及时移除），且统一使用 UE 5.8 无告警 API `GetMovementBaseObject()`。
2. **瞬间 180° 掉头保护**：载具原地 180° 翻转帧不能让 `UpdateBasedMovement` 直接对乘车玩家执行跨车体直线扫掠（易撞进驾驶座或侧栏）。在翻转前记录车上玩家的载具局部变换，翻转后直接以 `ETeleportType::TeleportPhysics` 还原至新姿态下的同一局部坐标并调用 `CMC->SaveBaseLocation()`。

## 3. 双端同步精度、随车 NPC 防互抢与热路径缓存

1. **消除 `FInterpTo` 稳态滞后与晚加入慢爬**：
   - 房主直随权威积分位置（`0 cm` 滞后）；
   - 客机在移动期采用**速度前馈积分 + 残差 PD 纠偏**（将稳态漂移从 `~60 cm` 压至 `< 1 cm`），首包到达（`!bHasInitialNetSync`）直接瞬时对齐；
   - 行驶期动态提频至 `12 Hz`，停靠落稳后降频至 `1 Hz` 并跳过每帧路径/地形采样。
2. **随车载具 NPC 禁止与 `ReplicatedMovement` 互抢**：当车夫由 `UpdateMountedSeatTransform()` 锁在客机本地 `DriverSeatAnchor` 时，必须覆写 `OnRep_ReplicatedMovement()` 在挂载期忽略服务器世界坐标快照，并把 NPC Tick 排在载具之后再刷新缰绳/道具；自由步行期用 `10 Hz` + 客机插值，静置期降为 `2 Hz`。
3. **热路径零每帧 `TActorIterator`**：联机客机端地图查询（`ResolveWagonActor`）、院落静态道具隐藏（`CachedCompoundActor`）、东门/酒馆门查找均须采用 `TWeakObjectPtr` + `0.5–1.0 s` 失效重扫冷却。

## 4. 参考实现

- `Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.{h,cpp}`
- `Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.{h,cpp}`
- `Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.{h,cpp}`
