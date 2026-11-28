# 挂载物品的城防设施联机同步（智能机枪塔案例）

**第一条（FPSGAME）　文件位置与引用路径。** 从[制作目录与功能索引](../../../Docs/Production/README.md)和[存储规则第 4.1 节](../../../WORKFLOW.md#41-存储分配与文件操作边界)查找功能入口，再确定制作源、正式资产与输出位置；游戏资产用 `/Game/...` 包名，交付时在同一功能条目登记位置和恢复版本。

适用：玩家把背包物品（枪械、工具、燃料）放进世界设施，由服务器驱动设施自动工作（机枪塔、弩炮、热油锅等）。参考实现：[VillageSmartTurret.cpp](../../../Source/FPSGAME/WorldGeneration/VillageSmartTurret.cpp)。

## 复制数据

1. **高频变化值不写进复制的物品结构体。** `FColdSteelItem` 含 `Data` 大字符串；每发子弹改 `MountedWeapon.Magazine` 会让整包重新复制，并触发客机 `OnRep` 重建骨骼枪模。余弹用独立 `int32 CurrentAmmo` 复制，只在存档 / 卸下 / 弹出的**副本**上写 `Magazine = CurrentAmmo`。为什么：每发都改结构体会占用带宽，客机还会因重建枪模而卡顿。
2. **`OnRep` 先比对外观指纹再重建。** 指纹取 `InstanceId|Definition|Data`，一致时只刷新状态灯和 Tick 频率。为什么：其他字段的复制也会触发 `OnRep`，不比对就会反复销毁、重组组件。
3. **倒计时只复制一次绝对结束时间。** 换弹复制 `ReloadEndServerTime` 和 `ReplicatedReloadDuration`，两端用 `GameState->GetServerWorldTimeSeconds()` 计算剩余时间和进度；不要每帧复制 `RemainingSec`。为什么：每帧复制浪费带宽，没有复制的时长基准还会让客机进度条比例出错。

## 物品归属与回收

4. 装上时在服务器记录 `MountedOwnerPawn` 和 `MountedOwnerState`（`AColdSteelPlayerState`）。退回顺序：显式指定的接收者 → 记录的 Pawn → `PlayerState->GetPawn()` → `GetShadowModel()`（适用于客机死亡或重生期间）→ `ColdSteelAuthority::Model` → 世界掉落。为什么：用 `GetFirstPlayerController()` 退回时，客机的枪会被寄到主机背包。
5. 三个弹出入口都要接：设施被打爆（`TakeDamage`）、手动拆除（`DismantlePrefab`）、承重坍塌（`AVoxelBuildPrefabActor::BeginFall`，必须在物理脱离前处理），并在 `EndPlay(Destroyed)` 加一层权威端兜底。为什么：坍塌后的落体件不在建筑记录里，只靠拆除路径会把枪吞掉。

## 表现与性能

6. `NetMulticast Unreliable` 的射击特效先检查空定义和专服，音效按 `Definition_Suppressed` 缓存。客机（`!HasAuthority()`）沿 `AimDir` 做一次本地可见性射线，再调用 `WeaponFX->OnTracerSegment` 画曳光；服务器端的 `Ballistics` 只在权威端生成曳光。为什么：不做这一步，客机只能看到枪口火光，看不到弹道。
7. 服务器每帧要用的数据都做缓存：`CachedVillageWorld`（替代 `TActorIterator`）、按"武器指纹 + 工坊等级"缓存武器数值、按目标缓存头部和躯干骨骼名（避免每帧 `FName::ToString().ToLower()`）。不在开火帧时，视线检测限频到 `0.10 s`，开火帧必须检测。空置且已归位时 `SetActorTickInterval(0.25)`，装枪、受击修复或开火后恢复 `0.016`。
8. 定制材质参数只在状态变化时写入（`LastAppliedOpticState`）。打开的 UI 抽屉逐项做脏检查，避免每帧格式化文本。

## 验证

联机行为要分开记录：编译、自动化测试、主机和客机实机结果。`FPSGAME.Village.Siege.SmartTurret` 覆盖挂载、弹出掉落、射击特效空指针回归，不覆盖双端带宽与客机曳光表现。
