# 建筑系统代码与性能审计（2026-09-23）

只读审计，未修改任何源码、未启动引擎、未运行测试。范围：`Source/FPSGAME/Building/` 全部 50 个文件（约 350 KB）。三份分项报告：

- [UI 与图标侧](audit-ui-icons-20260923.md)（子代理，行号实读核对）
- 世界侧（承重/倒塌/伤害/存档/网格）——本文 §②
- 逻辑构件与每帧路径（门/窗/火把/喷泉/残骸/瞄准幽灵）——本文 §③

## ① 执行摘要

### 总体判断

这套系统的**稳态每帧成本是健康的**：求解在后台线程、有节点上限与帧预算；地形采样 20 Hz、校验 10 Hz；图标队列空时不 Tick；喷泉用 0.25 s TickInterval + 距离分级 + 飞沫预算 ≤4；火把白天关光关焰。**没有发现"极大且不合理"的常驻开销**。

真正的问题集中在三类：**事件触发的尖峰**（一次拆除/爆炸可以同步做几千次射线）、**低频但每次都很贵的全量重建**（加载一座城堡）、以及**几个确认的正确性 bug**。下面按严重度排序。

### 问题总表（按严重度）

| ID | 严重度 | 类别 | 一句话结论 | 证据 |
| --- | --- | --- | --- | --- |
| **W1** | **高** | 性能尖峰 | `IsGroundAnchor` 每次调用 = 1 次全 Pawn 遍历构造查询参数 + 5 条射线；它在**放置提交路径**和**拆除重锚路径**上被逐格调用，拆一面 25 格的墙可触发上千次射线 | `VoxelBuildGrounding.cpp:97-102`、`VoxelBuildWorld.cpp:447`、`VoxelBuildWorldPrefab.cpp:120,316` |
| **W2** | **高** | 性能尖峰 | `RefreshSupportGraph`（载入/初始化）对**每个节点**调一次 `IsGroundAnchor` → N×5 条射线 + N 次全 Actor 遍历；2 万格城堡载入 = 10 万条同步射线卡在游戏线程 | `VoxelBuildWorld.cpp:306-317` |
| **W3** | **中高** | 正确性 | `VerifyPrefabSupport` 里 `Drop.Contains` 与脱落循环用**线性扫描 × 全 Prefabs 遍历**，凉亭级大构件（8.7 万占格）+ 多件同批脱落时 O(n²)；更实际的风险：`PrefabActors.FindRef(Anchor)` 拿不到 Actor 时**静默跳过销毁但仍从记录移除**——构件变"隐形占格"，玩家既看不见也删不掉 | `VoxelBuildWorldPrefab.cpp:201-231` |
| **W4** | **中** | 正确性 | 自由体积整体拆除时 `FreeVolumes.Remove` 后，该体积内残留的 `CellDamage`/`BrokenBonds` 条目**永久泄漏**在存档里（键含已失效 Volume，任何路径都不会再清） | `VoxelBuildComponent.cpp:1192`、`VoxelBuildWorld.cpp:161` |
| **W5** | **中** | 正确性 | `Undo()` 部分失败语义：批次里部分格已被破坏时只撤剩余格并返回 true，**提示语仍是"已拆除最近一批建造"**，玩家以为全撤了 | `VoxelBuildWorld.cpp:497-509` |
| **W6** | **中** | 正确性 | 撤销链丢回收：`Commit(Reverse,false)` 会 `FreshCells.Reset()` 清掉上一批的保护窗口；连续快速放置→撤销→放置时，前一批尚未结算的新件失去保护，可能被后续解算当既有结构压塌 | `VoxelBuildWorld.cpp:471-473` + `464` |
| **W7** | **中低** | 性能 | `EndPlay` 里 `while(!DamageQueue.IsEmpty())TickDamage()` —— 若某条伤害处理又入队新伤害（fragment 替换链），退出关卡时会**自旋拖长关闭时间**；已有 `.0015s` 预算但 `bClosing` 下 `LoadSampleAt` 早退，队列消费本身无上限 | `VoxelBuildWorld.cpp:524` |
| **W8** | **中低** | 性能 | 过载渐进损伤期间每 0.5 s 一次完整 gather+solve：单次受 MaxSolveNodes=4096 保护没问题，但 `DirtySupport.Append(Result.Evaluated)` 在未收敛翻倍迭代路径上可能让种子集持续膨胀 | `VoxelBuildWorldStructure.cpp:90-91,105` |
| **C1** | **中** | 正确性 | `AColdSteelDoor::ApplyAngle` 静止分支 `return` 前**不落最后一段转角**（窗版本落了）：门关/开到位后铰链停在距目标 ≤0.05° 处，且与窗行为不一致 | `ColdSteelDoor.cpp:255-264` vs `ColdSteelWindow.cpp:319-331` |
| **C2** | **中低** | 性能 | 门/窗/火把 Actor **无 TickInterval、空闲永不关 Tick**：每扇关着的门每帧跑 `UpdateLeafPawnCollision`+若干浮点比较。喷泉自己用了 0.25 s 间隔——同一系统内标准不一致。50 件 ≈ 0.05–0.1 ms/帧，不算灾难但属白给 | `ColdSteelDoor.cpp:29,243`、`BronzeTorch.cpp:33-34,189` |
| **C3** | **低** | 正确性 | `BronzeTorch::BeginPlay` 的"迁移旧默认值"会**覆盖刻意设成 600 lm / 900 cm 的用户自定义**（注释自认权衡）；存档里的火把只要数值恰好等于旧默认就会被改写 | `BronzeTorch.cpp:90-95` |
| **U1** | **中** | 性能 | 组件侧每帧无条件构造状态字符串（4–8 次 Printf/堆分配），消费端签名守卫随后丢弃；**面板收起的建造态照跑** | `VoxelBuildComponent.cpp:1234-1255` |
| **U2** | **中** | 性能 | 打开抽屉首帧 `LoadSynchronous` 同步加载图标资产（0.5–20 ms/件） | `VoxelBuildIcons.cpp:196-197` |
| **U3** | **中低** | 正确性 | `DrawerKeyFrame` 文件级 static：PIE 双开互相吞键 | `VoxelBuildComponent.cpp:96` |
| **U4** | **低** | 文档偏差 | 超限播报重新武装点是 1.0 而非文档所称 80%（warn 通道正确） | `VoxelBuildComponent.cpp:1269` |

## ② 世界侧：性能开销审计

### W1/W2：地面锚定射线风暴（本次最大发现）

`IsGroundAnchor` 的实现（`VoxelBuildGrounding.cpp:97-102`）：

```cpp
bool AVoxelBuildWorld::IsGroundAnchor(FVector Min) const
{
    VoxelGrounding::FFootprint Ground;
    return VoxelGrounding::Sample(GetWorld(),Min,Min.Z+VoxelGrounding::AnchorProbeRiseCm,
        Min.Z-VoxelGrounding::ContactToleranceCm,VoxelGrounding::Query(GetWorld(),this),Ground);
}
```

两个乘数叠在一起：

1. `VoxelGrounding::Query`（`:15-20`）**每次调用**做一次 `TActorIterator<APawn>` 全表遍历 + `IgnoreActors` 数组分配；
2. `Sample`（`:30-48`)对 5 个采样点各打一条 `LineTraceSingleByChannel`。

项目已经意识到这个模式并在两处做了缓存（`CanPlaceAt:329`、`CanCommit:403` 把 Params 提到格循环外，注释写明"5×5 刷子就是 25 次全 Actor 表遍历"）——**但 `IsGroundAnchor` 这条路径完全没吃到这个优化**，它自己内部又构造一次 Query。

调用点与放大倍数：

| 调用点 | 频率 | 单次格数 | 射线数 |
| --- | --- | --- | --- |
| `ApplyChanges:447`（每次放置/摧毁/拆除一格都走） | 每格 | 1 | 5 + 1 次全 Actor 遍历 |
| `ReanchorVoxelsAround`→`:120` | 拆除/脱落事件的邻格环 | 外壳一圈 | ×5 |
| `VerifyPrefabSupport`→`IsPrefabOnGround:154` | 每件候选构件 | 5 探测点 | ×5 |
| `RefreshSupportGraph:316` | **载入时每节点一次** | N | **N×5** |

**最坏场景量化**：右键拆一整面 5×5×20 的墙（500 格）。`EditVolumeCells` 一批提交 → `ApplyChanges` 500 格 × (5 射线 + 1 全 Actor 遍历)，外加 `ReanchorVoxelsAround` 的外壳重锚再来一轮。粗估 **2500–5000 条同步射线 + 数百次全 Actor 遍历，一帧内完成**。当前规模（几百格建筑）实测可能只有几毫秒，但这是随建筑尺寸**线性恶化**的最大单点。

**修法方向**（不在本次实施）：`IsGroundAnchor` 增加带 `const FCollisionQueryParams*` 重载，调用方（`ApplyChanges`/`ReanchorVoxelsAround`/`RefreshSupportGraph`）在批循环外构造一次传入——与 P3 已有的处理完全同构。`RefreshSupportGraph` 更进一步：它对**内部格**本来就跳过（`Covered` 判定），可以把候选底部格先做 `(X,Y)` 列去重再采样。

### W2：载入全量重建

`Initialize`（`VoxelBuildWorld.cpp:242-246`）：`RefreshSupportGraph`（O(N) 节点 × 5 射线，见上）+ `RebuildAffected(Loaded)` 把**所有格**标脏 → `TickMeshes` 以 2 worker/帧预算消化。网格部分是异步的、设计良好；痛的就是锚定射线那一遍。2 万格存档首次载入预计 **百毫秒到秒级卡顿**（未实测，纸面推算）。

### W7：EndPlay 自旋风险

```cpp
while(!Runtime->DamageQueue.IsEmpty())TickDamage();   // :524
```

`TickDamage` 的 fragment 替换路径（`VoxelBuildWorldDamage.cpp:146-147`）会 `EnqueueFragment`，而 `QueueCollapseImpact`/`TakeDamage` 在物理回调里继续向队列追加。正常退出时队列应当收敛，但**没有任何迭代上限**——一条病态连锁（大量残骸同时落地）可以把关卡切换卡在这行。建议加计数上限（如 10000 轮）+ 溢出记日志。

### 确认健康的路径（复核过，不必动）

- 求解调度：活跃子图裁剪 + `MaxSolveNodes` + 1 ms 收集帧预算 + 结果过期检查（`JobEpoch`/`Stale`）都在位（`VoxelBuildWorldStructure.cpp:220-251`）；
- 伤害队列：P19 游标修复后预算在循环顶部，四处 `continue` 不再绕开计数（`VoxelBuildWorldDamage.cpp:75-79`）；
- 残骸：几何合成在 worker、生成 8/帧 + 1.5 ms 预算、激活有 Bodies/Shapes 双预算、MeshBarrier 等网格落地才碰撞（`VoxelBuildWorldCollapse.cpp:52-184`）；
- 存档：快照 game thread、序列化与写盘在 worker、2 s 合并节流、失败重试 5 s（`VoxelBuildWorldSave.cpp`）；
- `Near()` 热路径已用 `thread_local` 复用缓冲（`VoxelBuildWorld.cpp:37-41`、`ResolveHit:96`）。

## ③ 正确性 bug 详述

### W3：构件脱落的 O(n²) 与"隐形占格"

`VerifyPrefabSupport`（`VoxelBuildWorldPrefab.cpp:201-228`）三处线性查找叠加：

```cpp
for(const FVoxelBuildPrefabInstance& Instance:Prefabs)
    if(Candidates.Contains(Instance.Cell)&&!IsPrefabSupported(Instance))   // 每件都跑 IsPrefabOnGround 射线
        Drop.Add(Instance.Cell);
...
const FVoxelBuildPrefabInstance* Instance=Prefabs.FindByPredicate(...);    // 每件脱落再线性找一遍
...
Prefabs.RemoveAll([&Drop](...){return Drop.Contains(Entry.Cell);});         // Drop 是 TArray，Contains 线性
```

功能正确，规模上去难看。**更要紧的是这一行**：

```cpp
AActor* Piece=PrefabActors.FindRef(Anchor).Get();          // :215 —— 拿不到就是 nullptr
auto* Placed=Piece?Cast<AVoxelBuildPrefabActor>(Piece):nullptr;
const bool bFalling=Placed&&Placed->BeginFall(...);
if(Piece&&!bFalling)Piece->Destroy();                      // Piece 为 null 时整段跳过
PrefabActors.Remove(Anchor);                               // 但记录照样删
```

`PrefabActors` 的值是 `TWeakObjectPtr`。若 Actor 因任何原因先没了（外部销毁、GC 边界、地图重载时序），这里**不会有任何日志**，但 `Prefabs.RemoveAll` 照删、占格表照刷新——体素侧格子还占着（`RefreshPrefabOccupancy` 依据 `Prefabs` 重建，所以占格其实会释放；真正的后果是**该构件从世界里无声消失**，玩家存档里它没了却不知道为什么）。属于低概率高困惑度问题，值得补一行 `UE_LOG(LogTemp,Warning,"PREFAB_DROP missing actor")`。

### W4：自由体积残留

`UVoxelBuildComponent` 右键拆除整批自由体积格成功后（`VoxelBuildComponent.cpp:1192`），`SetCell` 把 `FreeVolumes[Volume].Cells` 清空，但 `PlaceFree` 的失败回滚路径（`VoxelBuildWorld.cpp:395`）只 `FreeVolumes.Remove(Volume.Id)`——此时 `ApplyChanges` 可能已经给这些格写过 `CellDamage`/`BrokenBonds`/`NodeEpoch` 条目，体积 Id 一失效就**再没人清理**，随存档无限累积。量小（每次失败几个键），但属于确定性的单向增长。

### W5/W6：撤销语义的两个边角

- W5：`Undo` 里 `Existing.IsNone()` 的格被 `continue` 静默吞掉（`:500-501`），部分撤销成功时消息不变。至少应在 Message 里带上"其中 X 格已不存在"。
- W6：撤销走的也是 `Commit(...,false)`，开头无条件 `Runtime->FreshCells.Reset()`（`:471`）。设计意图是"新批次接管保护窗口"，但撤销批次的 `bRemember=false` 意味着**没有任何格进入新窗口**——上一批还在沉降期（3 s 内）的格子保护被一次撤销凭空解除。复现路径：放一批悬挑→立刻 Ctrl+Z 撤另一批→前一批在无保护状态下被下一次解算判负。需要实测确认是否真能触发（取决于两批是否连通），列为"疑似需验证"。

### C1：门的最后 0.05°

对照两个版本的 `ApplyAngle`：

```cpp
// ColdSteelDoor.cpp:257-260 —— 静止时直接 return，不写旋转
if(FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.05f)){CurrentAngle=TargetAngle;return;}
// ColdSteelWindow.cpp:321-326 —— 静止时先把 CurrentAngle 落进铰链再 return
if(FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.05f))
{CurrentAngle=TargetAngle;HingeLeft->SetRelativeRotation(...);HingeRight->SetRelativeRotation(...);return;}
```

门停在离目标 ≤0.05° 的位置。视觉几乎不可见，但它是**状态与表示不一致**：`CurrentAngle==TargetAngle` 而铰链不是。任何未来读铰链角度的逻辑都会踩坑。修法：门补上那两行 `SetRelativeRotation`（或统一抽基类）。

## ④ 与文档声称行为的偏差

| 文档（voxel-build-workflow.md） | 代码事实 | 判定 |
| --- | --- | --- |
| "回落到 80% 重新武装" | warn 通道 0.80 ✔；break 通道 1.0 边沿即重新武装 ✘ | U4，改码或改文档二选一 |
| "失败重试 MaxBuildAttempts=3（文件级计数）" | 上限一致；计数是 subsystem 成员非文件级 | 表述不符，行为等价 |
| 第 38 行"过载期间每 0.5 s 重新解算一次" | `OverloadTickCVar=.5` ✔，且经 `StructureAt` 节流 ✔ | 一致 |
| 第 47 行"金色贴边高亮收进组件成员" | `AimEdgeComponent/AimEdgeMaterial/AimEdgeCell/AimEdgeSignature/AimEdgeCount/LastCursorPoint` 均为成员 ✔ | 一致 |
| 第 48 行"僵尸字段 MaxCantileverCm 已删除" | grep 全树无引用 ✔ | 一致 |
| 第 51 行"AnchorCache 已移除（无任何读取）" | 头文件注释在案，grep 无残留 ✔ | 一致 |
| 第 59 行状态行格式 `求解 3.2 ms · 480 节点（局部 + 96 边界）` | `SolverSummary` 三分支文案一致 ✔ | 一致 |

## ⑤ 不确定项（如实声明）

1. **所有量级估计都是纸面推算**，本次未运行引擎、未 profile。W1/W2 的"千次射线"是从调用图数出来的，真实耗时取决于地形碰撞复杂度。
2. W6（撤销解除保护窗口）能否造成可见倒塌，取决于两批体素的连通性与解算时序，静态分析无法定论。
3. `UCanvasPanelSlot::SetPosition/SetSize` 在 UE 5.8 是否有相等短路（影响 U 系列一处估计），子代理标注未验证。
4. 门/窗占位的 `BlockAll` 碰撞是否用了复杂网格作简单碰撞，需要看 `SM_SingleDoorLeaf_D40` 等资产的碰撞设置，代码层看不到。
5. 喷泉 `WaterMesh` 的 WPO 水面在大型水体上的 GPU 成本、火把 `NS_TorchFlame` 的粒子数，属美术资产侧，未审。

## ⑥ 如果要动手，优先级建议

| 序 | 项 | 理由 |
| --- | --- | --- |
| 1 | W1+W2：`IsGroundAnchor` 吃 Params 缓存 + `RefreshSupportGraph` 列去重 | 同一修法的两个受益点，消掉系统里唯一随规模线性恶化的同步射线源 |
| 2 | W3 的 missing-actor 日志 + U3 的 `DrawerKeyFrame` 成员化 | 一行改动，消除两类高困惑度现场 |
| 3 | C1 门静止落角 | 与窗对齐，防未来回归 |
| 4 | U1/U2（状态串生产端守卫、图标预热） | UI 子代理报告附了具体补丁形态 |
| 5 | W5/W6/W7/W4 | 语义修正，改动小但要连带回归说明 |
