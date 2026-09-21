# 体素建造系统审计与性能优化建议（2026-09-21）

审计范围：`Source/FPSGAME/Building/` 全部 50 个源文件（约 7 000 行 C++），
重点覆盖放置交互热路径、承重求解器、表面网格与碰撞、构件占格、持久化、面板 UI、图标子系统。

本文是**只读审计**：审计阶段没有改动任何代码。所有结论都给出 `文件:行号` 与原文引用。
未经验证的推断一律标注「未验证」。字节/规模数字由字段宽度推导（推算式已写出），
凡属引擎内部行为（容器框架、序列化细节、Slate 无效化）无法从仓库确认的，均标注「未验证」。

> **2026-09-21 实测更正（P4）**：修复已实施并量测，本文原先对 P4 收益的推断**偏大**。
> 面板跨度量测（3 材质 × 2 口径 × 25 格扫，取 3 次平均）：
> **旧实现 44.64 ms → 新实现 36.08 ms**，即那 2 MB 的 `std::fill` 只占约 **8.5 ms（19%）**，
> 不是全部。剩余约 36 ms 是**求解器本身**（每次 `Ratio()` 跑一次 256 迭代 CGNR）。
> 因此"一次性 0.2–0.5 s"的说法也不成立——实测面板构建约 **36 ms**（一次性，非每帧）。
> 真正的大头是求解次数：`PushPanelContent` 每个材质扫 2 个口径 × 25 格，
> 每格一次完整求解。要再降一个数量级得做**结果缓存**（按材质签名+载荷缓存 `MaxSpanMeters`）
> 或把面板计算移入后台线程，而不是继续优化清零。
> 数值正确性已用硬判据确认：新旧探针输出**逐项完全相同**
> （wood 8.80/6.80、stone·marble 7.80/7.40，以及 2.00 m 行的 0.050/0.231 与 0.062/0.115）。

配套文档：[体素建造工作流](voxel-build-workflow.md)（现行契约）、
[承重与倒塌设计](structural-collapse-20260913.md)、
[建筑系统验收](voxel-build-audit-20260916.md)。

---

## 0. 结论摘要

系统整体架构是合理的：编辑/持久化归 `AVoxelBuildWorld`，输入/表现归 `UVoxelBuildComponent`，
承重求解丢线程池，网格生成丢线程池，物理回调只入队。前几轮优化（活跃子图裁剪、
每帧开销分级节流、实例缓冲签名缓存、帧预算）方向正确且已见效。
面板侧也已经有正确的守卫：`SetContent` 深比较、`SetSelection` 早退、
`RefreshLayout` 视口/缩放早退、`RebuildCards` 只在脏标记时执行 ——
**面板树不是每帧重建的**，这一点比预期好。

但审计发现 **23 项性能问题与 14 项正确性缺陷**。最需要先处理的：

| # | 位置 | 复杂度 | 触发条件 | 预估影响 |
| --- | --- | --- | --- | --- |
| **P1** | `VoxelSupportGraph.cpp:192` | **O(过载格²)** | 大面积过载 | 万级格时**秒级**卡死 |
| **P2** | `VoxelBuildWorldMesh.cpp:55` | **O(脏块 × 在飞作业)** | 大建筑连续编辑 | 每帧数千次比较 |
| **P3** | `VoxelBuildGrounding.cpp:15,65,101,125` | 每格 1 次 `TActorIterator` | 每次准星跨格 | 每帧 200+ 射线 + 25 次分配 |
| **P4** | `VoxelJointStrength.h:86` | 每次调用 2 MB `std::fill` | 面板初始化 | 一次性 0.2–0.5 s 卡顿 |
| **P5** | `VoxelBuildWorldPrefab.cpp:30-40` | 重建全部构件占格 | 放/拆大构件 | 凉亭一件 8.7 万格 |
| **P6** | `VoxelSupportGraph.h:36` | 每次调用返回 `TArray` | 全系统高频 | 每帧数十次堆分配 |
| **P13** | `VoxelBuildWorldSave.cpp:9-37` | 每 0.75 s 全量快照 | 持续编辑 | game thread 拷约 450 KB + UObject |
| **P18** | `VoxelBuildWorldCollapse.cpp:121-133` | 每帧 O(碎片×格) 重试 | 背包/地面物品满 | 每帧数千次 `FName::ToString` |
| **P19** | `VoxelBuildWorldDamage.cpp:129` | `continue` 跳过预算 | 一批碎片被替换 | 单帧 pop 完整个队列 |
| **P20** | `VoxelCollapseFragment.cpp:51` | —（功能性） | 倒塌碎片 >128 件 | **碎块凭空消失** |
| **P23** | `VoxelBuildIcons.cpp:19,308,371` | 768 KiB/图标，软上限 | 开抽屉 | 显存可达数十 MB 且无上限 |

需要一并修的还有：**1 个数据竞争**（`VoxelJointStrength.h:86` 的 `static` 共享缓冲，C1）、
**1 个死上限**（`VoxelBuildWorldStructure.cpp:237` 使 `MaxSolveNodes` 永不生效，C2）、
**1 个可用性缺陷**（存档 CRC 失败会让整个建造功能不可用且报错原因错误，C6）、
以及 **P20 那类"不报错但玩法错"** 的缺陷（等预算的残骸被静默回收 —— 碎块凭空消失）。

> **关于委派审计的两处更正**：本轮综合了两个并行子审计。
> 其中「`DamageQueue` 的 `continue` 会绕过帧预算」经复核**部分错误** ——
> 正常路径确实受 4 条/帧限制（见 P18 的更正框），
> 只有 P19 列出的四条 `continue` 会跳过计数，那才是真问题。
> 另有一条「按位置合并伤害请求」的建议**未采纳**：它会改变
> `Replaces` 替换流程的先后语义，风险高于收益（见 C14）。

---

## 1. 架构与数据流（现状）

```
UVoxelBuildComponent (PlayerController 组件, TG_PostUpdateWork)
  ├─ TickComponent ──> UpdateTarget()          每帧：射线 + 格解析 + 方案
  │                    ValidatePlacement()      ≤10 Hz 兜底 / 方案变即重算
  │                    UpdateWidget()           每帧构造字符串
  └─ HandleInput ────> EditVolumeCells/PlaceFree
                          │
AVoxelBuildWorld (AActor, TG_PrePhysics)
  ├─ Cells: TMap<FIntVector,FName>              世界格
  ├─ FreeVolumes: TMap<FGuid,FVoxelFreeVolume>  自由放置体积
  ├─ SupportGraph: TSharedPtr<FVoxelSupportGraph>  承重图（键含 FGuid）
  ├─ Runtime: TUniquePtr<FVoxelBuildRuntime>    脏集/作业/队列
  ├─ Tick: SampleVelocity → TickDamage → TickMeshes
  │        → TickFragments → TickStructure → TickPersistence
  └─ Commit → ApplyChanges → RebuildAffected + VerifyPrefabSupport + MarkSaveDirty
                   │              │
                   │              └─> Async 线程池: VoxelGeometry::Batch
                   └─> Async 线程池: VoxelStress::Solve
```

关键设计点（正确、保留）：编辑全程 game thread；求解与网格在 `EAsyncExecution::ThreadPool`；
物理命中回调只入 `DamageQueue`；`Runtime->MeshJobs` 用 Revision 做陈旧结果丢弃。

---

## 2. 性能问题（按预期收益排序）

### P1 — 过载表线性查找造成 O(n²) 【严重】

`Source/FPSGAME/Building/VoxelSupportGraph.cpp:192`

```cpp
if(FVoxelOverloadCell* Existing=Result.Overload.FindByPredicate([&](const FVoxelOverloadCell& E){return E.Key==Key;}))
```

这段在**每条过载接缝 × 2 个端点**上做一次全表线性扫描。`Result.Overload` 的规模
与过载格数同阶，所以整体是 **O(过载格²)**。

触发路径：`VoxelStress::Solve` → `Result.Overload` → `VoxelBuildWorldStructure.cpp:101`
`ApplyOverloadDamage(Result.Overload, ...)`。大面积过载（一面墙整体超限、或
`fps.Building.OverloadGraceSeconds` 调小后的大结构）就会命中。

规模估算：5 000 个过载格 → 约 5 000 × 2 × 5 000/2 = **2.5×10⁷ 次 `FVoxelBuildKey` 比较**，
每次比较含 `FGuid`（16 字节）+ `FIntVector`。万级格直接进入秒级区间。
注意这与文档第 2 节「过载期间每 0.5 s 重新解算一次」叠加，会变成**周期性卡死**。

**修法**（低风险，纯局部）：用索引表替换线性扫描。

```cpp
TMap<FVoxelBuildKey,int32> OverloadIndex;   // Solve 开头建立，与 Result.Overload 同步
...
if(int32* Slot=OverloadIndex.Find(Key))
{
    FVoxelOverloadCell& Existing=Result.Overload[*Slot];
    if(Rate>Existing.RatePerSecond){Existing.RatePerSecond=Rate;Existing.Ratio=Ratio;}
}
else {OverloadIndex.Add(Key,Result.Overload.Num());Result.Overload.Add({Key,Rate,Ratio});}
```

风险：无。`Result.Overload` 的顺序会变（原本按发现顺序，改后仍按首次发现顺序，行为一致）。

---

### P2 — 网格调度每帧 O(脏块 × 在飞作业) 【严重】

`Source/FPSGAME/Building/VoxelBuildWorldMesh.cpp:50-58`

```cpp
while(Runtime->MeshJobs.Num()<FMath::Clamp(MeshWorkers.GetValueOnGameThread(),1,4)&&!Runtime->DirtyChunks.IsEmpty())
{
    FVoxelBuildKey Key;double Best=TNumericLimits<double>::Max();bool Found=false;
    for(const auto& Candidate:Runtime->DirtyChunks)
    {
        if(Runtime->MeshJobs.ContainsByPredicate([&](const auto& Job){return Job.Key==Candidate;}))continue;
        const double Distance=FVector::DistSquared(View,VolumeOrigin(Candidate.Volume)+CellMin(Candidate.Cell*16)+FVector(160));
        if(Distance<Best){Best=Distance;Key=Candidate;Found=true;}
    }
    ...
}
```

三层代价叠加：

1. 外层 `while` 最多 4 次（`MeshWorkers` 上限 4）；
2. 内层遍历**全部** `DirtyChunks`（`TSet`，无顺序）；
3. 每个候选还要 `ContainsByPredicate` 扫一遍在飞作业（≤4），并且对**每个**候选都算一次距离。

所以是 `4 × |DirtyChunks| × (4 + 距离计算)`。`VolumeOrigin()` 是 `TMap::Find`，
`CellMin()` 是向量构造 —— 都发生在最内层。

触发场景：一次 5×5×1 放置 → `RebuildAffected`（`VoxelBuildWorldMesh.cpp:20-32`）对每个编辑格
扩 3×3×3 = 27 个 chunk key，25 格即最多 **675 个脏块**（去重后仍可达几十）。
连续建造时 `DirtyChunks` 会累积到数百，此时单帧就是数千次比较 + 数百次 map 查找。
这正好解释了「建造时帧率抖动」。

**修法**（三步，可只做第 1 步）：

1. **维护 `TSet<FVoxelBuildKey> InFlightKeys`**，与 `MeshJobs` 同步增删，把
   `ContainsByPredicate` 换成 O(1) 查表。这一步就能砍掉一个乘数。
2. **每帧只排序一次**：把 `DirtyChunks` 拷进数组按距离排序（`Sort` 一次 O(n log n)），
   然后从头取未在飞的。替换 4 次全扫。
3. 更彻底：`RebuildAffected` 直接按距离插入有序容器（`TArray` + 二分），
   让调度退化成 O(1) 取头。

风险：低。改动集中在 `TickMeshes` 与 `RebuildAffected`，不触碰求解语义。
注意第 1 步要在**所有**增删 `MeshJobs` 的地方同步（`TickMeshes:46`、`:90`）。

---

### P3 — 地面锚定每格重建一次碰撞查询参数 【高】

`Source/FPSGAME/Building/VoxelBuildGrounding.cpp:15-20`

```cpp
FCollisionQueryParams VoxelGrounding::Query(UWorld* World,const AActor* Ignore)
{
    FCollisionQueryParams Params(SCENE_QUERY_STAT(VoxelGrounding),true,Ignore);
    for(TActorIterator<APawn> It(World);It;++It)Params.AddIgnoredActor(*It);
    return Params;
}
```

`FCollisionQueryParams` 每次构造都会分配 `IgnoreActors` 数组，而 **`TActorIterator<APawn>`
每次都是一次全 Actor 表遍历**。这个函数被按「每个格子」调用：

- `VoxelBuildGrounding.cpp:101` — `IsGroundAnchor()` 每次 1 次
- `VoxelBuildGrounding.cpp:125` — `ScenePlacementAllowed()` 每次 1 次
- `VoxelBuildGrounding.cpp:65` — `ResolveGroundPlacement()` 每次 1 次
- `VoxelBuildWorldPrefab.cpp:142` — `IsPrefabOnGround()` 每次 1 次

而 `ScenePlacementAllowed` 由 `CanPlaceAt` **逐格**调用
（`VoxelBuildWorld.cpp:243`，在 `for(const auto& Cell:Positions)` 循环内）。所以一个
5×5 地块的预览校验就是 **25 次 `TActorIterator` + 25 次数组分配**。

再叠加射线数量：`Sample()`（`VoxelBuildGrounding.cpp:30-48`）每格 **5 条** LineTrace，
`ScenePlacementAllowed` 另有 3 条轴向障碍探针（`:133-152`）。仅 `CanPlaceAt` 一条路径：

```
25 格 × (1 次 Query + 5 次地面探针 + 3 次障碍探针) = 25 次 Query + 200 条射线
```

**这个校验以「准星跨格」为频率触发。**`VoxelBuildComponent.cpp:1036-1037` 的
`Changed` 判定包含 `CheckedCells!=Placement` 与 `CheckedOrigin!=PlacementOrigin`：

```cpp
const bool Changed=CheckedRevision!=BuildWorld->StructureRevision()||CheckedMaterial!=PlacementMaterial||
    bCheckedSnap!=bPlacementSnap||CheckedVolume!=PlacementVolume||CheckedOrigin!=PlacementOrigin||CheckedCells!=Placement;
if(Changed||Now>=PlacementCheckAt)
```

`PlacementCheckAt=Now+.1`（`:1051`）是「**没变时**最多每 100 ms 一次」的兜底下限，
**不是**上限。只要准星跨过一个 20 cm 格边界，`Placement`/`PlacementOrigin` 就变，
`Changed` 立刻为真 → 该帧重算。玩家持续瞄准移动时这可以接近每帧一次，
即**每帧 200+ 条射线 + 25 次 `TActorIterator`**。

补充：`ResolveGroundPlacement` 自己还有一层采样（`VoxelBuildGrounding.cpp:69-76`，
`Size.X*Size.Y` 个足迹 × 5 探针 = 5×5 时 125 条射线），
而 `ResolveGroundPlacement` 受 `GroundSampleAt` 20 Hz 节流（`VoxelBuildComponent.cpp:640`）。
所以贴地分支是 125 条 @20 Hz + 200 条 @每次跨格，两者叠加。
自由放置（F）分支不受 `GroundSampleAt` 节流，注释明说「F 模式永不节流」（`:638-639`）。

**修法**：

1. **把 `Query()` 提到循环外**：`ResolveGroundPlacement`（`:65`）已经是循环外构造，
   但 `ScenePlacementAllowed` 是每格一次。改成 `CanPlaceAt` 构造一次 `FCollisionQueryParams`
   并沿参数传递。这一条改完就把 25 次 `TActorIterator` 降成 1 次。
2. **缓存 Pawn 忽略表**：Pawn 集合很少变，缓存到 world/组件上，失效时机为
   `OnActorSpawned`/`OnActorDestroyed` 或每 N 秒重建。
3. **给校验加真正的上限**：`ValidatePlacement` 增加一条「最早于上次校验后 X ms 才允许重算」
   的硬节流（例如 50 ms），把「方案变即重算」从无上限改成有上限。手感影响需要用户确认
   （当前承诺是「颜色随格子即时更新」，见工作流 3.2）。备选：把
   `CheckedOrigin` 的比较改成比较**取整后的格**而不是连续原点，这样微小抖动不再触发重算。

风险：第 1、2 条无行为变化，纯性能；第 3 条改手感，需用户拍板。

---

### P3b — 足迹采样的 `TInlineAllocator<5>` 会溢出 【中】

`Source/FPSGAME/Building/VoxelBuildGrounding.h:22`

```cpp
TArray<TWeakObjectPtr<UPrimitiveComponent>,TInlineAllocator<5>> Surfaces;
```

`Sample()`（`VoxelBuildGrounding.cpp:30-48`）对每个足迹跑 **5 条**竖直探针
（`:34` 的 `Samples[]` 正好 5 项），每条命中都 `Out.Surfaces.AddUnique(Ground.GetComponent())`
（`:45`）。5 条探针命中 **5 个不同组件**时，数组容量 5 刚好用尽；
只要出现第 6 个不同表面（地形分块边界、探针打到墙与地两个 actor 等），
`TInlineAllocator<5>` 就溢出并**回退到堆分配**。

调用点规模：`ResolveGroundPlacement`（`:66`）构造
`TArray<FFootprint,TInlineAllocator<25>> Samples`，5×5 地块即 **25 个 `FFootprint`**，
每个各含一个可能溢出的 `Surfaces`。所以一次贴地判定潜在 **最多 25 次堆分配**，
而且是 20 Hz 持续发生（`VoxelBuildComponent.cpp:640`）。

**修法**：把 `TInlineAllocator<5>` 提到 `<8>`（或 `AddUnique` 前去重判据改成
「只记最上面的那个组件」，因为 `Surfaces::Contains` 的唯一用途是
`ScenePlacementAllowed:137` 判断障碍命中是否属于地面——多于 2–3 个表面时
语义上已经不需要继续收集）。改动两行，风险低。

`ScenePlacementAllowed:125-130` 另有一次 `Sample(...)` 调用（每格一次，
探针带 `Min.Z+40.5` → `Min.Z-20.5`），这是 P3 已计的部分。

---

### P4 — 面板初始化的 2 MB `std::fill` 【高，一次性】

`Source/FPSGAME/Building/VoxelJointStrength.h:86-87`

```cpp
static long long Lookup[64 * 64 * 64];
std::fill(Lookup, Lookup + 64 * 64 * 64, -1);
```

`Lookup` 是 64³ × 8 字节 = **2 MB**（`long long`），每次 `Ratio()` 调用整个清零。
`MaxSpanMeters`（`:174-183`）从 1 扫到 `MaxSpanCells`，每次迭代调一次 `Ratio()`：

```
每材质 2 个口径 × 最多 25 格 = 50 次 Ratio()
（其中「跨中站人」通常在更小跨度就 break，所以实际约 40–50 次）
3 种材质 × 2 口径 = 约 150 次 Ratio()
150 × 2 MB = 约 300 MB 的内存写入 + 150 次约 2 MB 清零```

这就是工作流 3.3 记录的「一次性 0.2–0.5 s」的真正来源。它在
`TryInitializeWorld`（`VoxelBuildComponent.cpp:214` `PushPanelContent()`）里**同步**执行，
即进世界瞬间的一次卡顿。而且 `MaxSpanMeters` 的循环是 `Ratio(Span)` 单调递增的，
一旦失败就 `break`，所以**前几次迭代的解算结果全部丢弃**，只为了找到断点。

另外每次 `Ratio()` 还构造 `std::vector<FCell>`、`Nodes`、`Links`、`Raw`、`Forces`
共 5 个动态容器（`:96,113,138,146`）。

**修法**：

1. **把 `Lookup` 降维/缩小**：`Room()`（`:64-76`）的坐标范围是
   `X∈[0,5)`、`Y∈[0,SpanCells+1]`、`Z∈[0,6)`，最大 SpanCells=25 时
   `X<5, Y<27, Z<6`。用 `int32 Lookup[6*28*7]`（约 4.7 KB）配偏移即可，
   清零成本降 **400 倍以上**。`Key()`（`:55`）同步改。
2. **只清零用到的那部分**：或改用「代际标记」（`uint32 Stamp[]` + `CurrentStamp`），
   彻底免清零。
3. **缓存结果**：`MaxSpanMeters` 的输入只有 `FMaterial` + `ExtraLoadKg`，
   材质只有 3 种、载荷只有 2 档。按 `(材质签名, 载荷)` 做静态缓存，
   面板重建（`PushPanelContent` 不只在初始化时调）就不再重复计算。
4. 长期：按文档 3.3 的既有建议移到后台线程（求解器是纯 CPU、不碰 UObject）。

风险：1、2 是纯数值等价改写，需跑
`Tools/Building/run_voxel_stress_probe.ps1` 复核跨度表仍为
wood 8.80/6.80 m、stone·marble 7.80/7.40 m（工作流第 2 节）。3 需要材质改动时失效缓存。

---

### P5 — 构件占格表全量重建 【中高】

`Source/FPSGAME/Building/VoxelBuildWorldPrefab.cpp:30-40`

```cpp
void AVoxelBuildWorld::RefreshPrefabOccupancy()
{
    PrefabCells.Reset();
    PrefabCellOwner.Reset();
    TArray<FIntVector> Occupied;
    for(const FVoxelBuildPrefabInstance& Entry:Prefabs)
    {
        FillPrefabCells(Entry.Cell,Entry.Footprint,Occupied);
        for(const FIntVector& Cell:Occupied){PrefabCells.Add(Cell);PrefabCellOwner.Add(Cell,Entry.Cell);}
    }
}
```

每次调用**清空并重建全部构件的全部占格**，对每个格做一次 `TSet::Add` + 一次 `TMap::Add`。
调用点：`Initialize:146`、`PlacePrefab:330`、`RemovePrefab:362`、`VerifyPrefabSupport:229`。

规模问题在代码自己的注释里就写了（`VoxelBuildWorldPrefab.cpp:26`）：
「超大构件（凉亭 48×48×38 ≈ 8.7 万格）」。所以：

- 放/拆一件凉亭 → 重建 (8.7 万 + 其他) × 2 次容器插入
- `VerifyPrefabSupport` 每次体素编辑批次后都可能触发 → 又一轮全量重建

这是**游戏线程**上的，会直接表现为一帧或几帧的长卡顿。

`Prefabs.FindByPredicate`（`:91`、`:208`、`:345`）也是线性扫描 `Prefabs`，
在 `VerifyPrefabSupport:208` 里被放在 `Drop` 循环内，构成小规模 O(n²)。

**修法**：

1. **增量维护**：`PlacePrefab` 只插这一件的占格；`RemovePrefab`/脱落只删这一件的占格
   （删除前先 `FillPrefabCells` 取出它的格，代码里已经在做这件事，见 `:344-347`）。
2. **加 `TMap<FIntVector,int32> PrefabByAnchor`**（锚格 → `Prefabs` 下标）替换
   `FindByPredicate`。注意 `Prefabs` 用 `RemoveAll` 会打乱下标，需在重建时刷新，
   或直接改用 `TMap<FIntVector,FVoxelBuildPrefabInstance>` 作为主存储。
3. 若短期不想改结构：至少给 `RefreshPrefabOccupancy` 加 `Reserve`
   （`PrefabCells.Reserve`/`PrefabCellOwner.Reserve`），能省掉多轮 rehash。

风险：中。占格表是放置判定的唯一权威（`IsPrefabCell` 被
`CanPlaceInVolume`/`CanCommit`/`ScenePlacementAllowed` 调用），增量维护的增删必须与
`Prefabs` 数组完全一致。建议加一条 `check()` 或审计日志在
`RefreshPrefabOccupancy` 里比对增量结果与全量结果，验收后再删。

---

### P6 — `Near()` 每次调用都堆分配 【中高】

`Source/FPSGAME/Building/VoxelSupportGraph.h:36`

```cpp
TArray<FVoxelBuildKey> Near(const FVector& Min) const;
```

`Source/FPSGAME/Building/VoxelSupportGraph.cpp:10-16`

```cpp
TArray<FVoxelBuildKey> FVoxelSupportGraph::Near(const FVector& Min) const
{
    TArray<FVoxelBuildKey> Result;const FIntVector C=Bucket(Min);
    for(int32 Z=-2;Z<=2;++Z)for(int32 Y=-2;Y<=2;++Y)for(int32 X=-2;X<=2;++X)
        if(const auto* List=Buckets.Find(C+FIntVector(X,Y,Z)))for(const auto& Key:*List)Result.Add(Key);
    return Result;
}
```

返回 `TArray` **按值**，调用方无法复用缓冲。调用点全部在高频路径上：

| 调用点 | 上下文 | 频率 |
| --- | --- | --- |
| `VoxelSupportGraph.cpp:51` | `Add()` 建图时每节点一次 | 每次解算 × 节点数 |
| `VoxelSupportGraph.cpp:92` | `Overlaps()` | 每次放置判定 × 格数 |
| `VoxelBuildWorld.cpp:81` | `ResolveHit()` | 每帧瞄准 |
| `VoxelBuildWorld.cpp:247` | `CanPlaceAt()` | 每次校验 × 格数 |
| `VoxelBuildWorld.cpp:263` | `CanPlaceAt()` 失败诊断分支 | 拒绝时 |
| `VoxelBuildWorldDamage.cpp:160` | `SetAppliedLoad()` | 每 0.25 s × 载荷数 |
| `VoxelBuildWorldPrefab.cpp:114` | `ReanchorVoxelsAround()` | 拆构件后 |

只算每帧瞄准这一条：`ResolveHit` → `Near` 一次分配；`UpdateTarget` 里 `ResolveHit`
最多对每个命中调用一次，再加 `TrySnapAssist` 的 16 条辅助射线。仅瞄准路径每帧就是
**十几次堆分配**。`CanPlaceAt` 在 5×5 地块上再加 25 次。
`Add()` 在 2 万节点解算时是 **2 万次分配**（虽然在线程池上，但每次解算都重建整张图）。

**修法**（两档）：

1. **最小改动**：改成出参 + 调用方复用缓冲。

   ```cpp
   void Near(const FVector& Min,TArray<FVoxelBuildKey>& Out) const;   // Out.Reset() 内部做
   ```

   调用方持有 `TArray<FVoxelBuildKey> Scratch` 成员/文件级缓冲（本文件已有这种先例，
   见 `VoxelBuildComponent.cpp:33-35` 的 `AimScratch`/`ProbeScratch`）。

2. **更彻底**：`Near` 的结果天然有界（5×5×5=125 个桶，实际命中数远小于此），
   改用 `TArray<FVoxelBuildKey,TInlineAllocator<32>>` 返回，常见情形零分配，
   签名不用改。**推荐先做这一条**，改动最小、风险最低。

3. 长期（见 P7）：`Add()` 建图时不该用 `Near()`，应直接由调用方传入邻居。

风险：低。`Near` 是纯查询，无副作用。

---

### P7 — 求解器每次解算重建整张图 + 哈希键布局差 【中，架构级】

`Source/FPSGAME/Building/VoxelSupportGraph.cpp:97-102`

```cpp
FVoxelStressResult VoxelStress::Solve(FVoxelStressInput Input)
{
    FVoxelStressResult Result;Result.Revision=Input.Revision;Result.Iterations=Input.Iterations;
    FVoxelSupportGraph Graph;Graph.Broken=MoveTemp(Input.Broken);
    for(const auto& Node:Input.Nodes){Graph.Add(Node);Result.Evaluated.Add(Node.Key);}
```

问题：

1. **每节点一次 `Near()`**（125 个桶探测）+ `Contact()`（最多 3 轴）+ 双向 `TSet::Add`。
   2 万节点、每节点约 6 条边 → 约 **250 万次桶探测** + 约 **12 万次 `TSet` 插入**。
   而 `AVoxelBuildWorld` **已经**维护着一份 `SupportGraph`（含 `Edges`），
   数据被复制过去又重新推导一遍边。这是白付出的最大单笔开销。
2. **键是 `FVoxelBuildKey{ FGuid(16B) + FIntVector(12B) }` = 28 字节**，每次哈希和比较都碰 28 字节。
   `Graph.Nodes`/`Edges`/`Supported`/`Broken`/`Seen`/`Indices`/`Result.Evaluated`/
   `Result.Supported` 全是基于它的 `TMap`/`TSet`。缓存局部性很差。
3. `Input` **按值传**（`FVoxelStressInput Input`），加上 `VoxelBuildWorldStructure.cpp:254`
   的 `Async(...,[Input=MoveTemp(Runtime->Gather)]` 捕获，`Nodes` 数组、`Broken`、`Boundary`
   各被搬运一次。
4. `Result.Evaluated`/`Result.Supported` 是 `TSet<FVoxelBuildKey>`，跨线程回传后
   `VoxelBuildWorldStructure.cpp:81-85` 又逐键写入 `SupportGraph`。

工作流第 2 节记录的基线是「约 4.8 µs/节点/次」（200 格 1.2 ms、2 000 格 11.0 ms、
20 000 格 95.8 ms）。**这个每节点成本里，图重建与哈希查找占比很高。**

**修法**（按性价比排序）：

1. **把边表传进去，不要重新推导**：`FVoxelStressInput` 增加
   `const FVoxelSupportGraph* Source`（或传入预展开的邻接数组），
   `Solve` 里跳过 `Graph.Add()` 的 `Near()` 部分，直接复制 `Edges`。
   预计能砍掉解算时间的一大块，且**完全不影响数值**（同样的边集）。
   验收口径：同一建筑的 `LastSolveNodes`/`LastSolveSeconds` 与求解结果（`WorstBond`、
   `Crushed`、`Broken`、`Detached`）逐项一致。
2. **密集编号 + 数组邻接**：进入 `Solve` 时给节点编号 `0..N-1`，
   用 `TArray<FVoxelSupportNode>` + CSR 邻接（`TArray<int32> Offsets, Neighbors`）。
   这一步同时消灭问题 1、2、4。`Links`/`Indices` 已经是这个思路，只是建得晚。
3. `Solve(FVoxelStressInput Input)` 的按值传参可保留（`MoveTemp` 传入后 `Input` 就地消费），
   但 `Result.Evaluated` 建议改成 `TArray` 并复用。

风险：中高。这是数值核心，必须用 `run_voxel_stress_probe.ps1` +
[建筑系统验收](voxel-build-audit-20260916.md) 的口径逐项回归。
建议先做第 1 步（等价且收益大），第 2 步作为后续独立一轮。

---

### P8 — `TickMeshes` 的逐块 `TMap` 查找与 `MaterialSlots` 查找 【中】

`Source/FPSGAME/Building/VoxelBuildWorldMesh.cpp:60-86`

```cpp
for(const auto& Source:Runtime->MeshGroups.FindChecked(Key))
{
    FVoxelChunkSnapshot Input;Input.Origin=Source.Cell*16;
    Input.Offset=VolumeOrigin(Source.Volume)+CellMin(Input.Origin)-CellMin(Key.Cell*16);
    const auto* Free=FreeVolumes.Find(Source.Volume);const auto* Data=Source.Volume.IsValid()?(Free?&Free->Cells:nullptr):&Cells;
    ...
        if(const auto* Slot=MaterialSlots.Find(Material)){...}
```

- `VolumeOrigin(Source.Volume)`（`VoxelBuildWorld.cpp:68-71`）是一次 `TMap<FGuid,...>` 查找，
  在内层循环每次调用。
- `MaterialSlots.Find(Material)`（`TMap<FName,int32>`）**对每个格**查一次。
  16³ 满块 = 4 096 次 `FName` 哈希查找，每块一次。
- `VoxelBuildWorldMesh.cpp:79-83` 的分支：
  - 小 volume（`<5832` 格）稀疏遍历 `Data`（正确选择）；
  - 大 volume 走 `17³ = 4 913` 次 `Data->Find(Cell)` 全扫描。

**修法**：

1. `MaterialSlots` 的 `FName` → 小整数 slot 缓存到节点上，或在
   `FVoxelSupportNode`/`Cells` 旁维护 `TMap<FName,int32>` 的**直接引用**避免重复哈希。
   更简单：把内层 `MaterialSlots.Find` 提到能复用的地方，或改用
   `TMap<FName,int32>` 换成 `FName` 的比较数更少的结构。
2. `VolumeOrigin` 在 `RebuildAffected`/调度阶段预算一次，随 `MeshGroups` 一起缓存。
3. 大 volume 的 `Data->Find` 扫描阈值（5832）建议按**实际占用格数**而不是容器格数判断，
   或改用 `TMap` 的范围迭代（`Data` 是 `TMap<FIntVector,FName>`，
   可直接 `for(const auto& C:*Data) if(在halo内) Add(...)`，与稀疏分支合并）。
   当前大 volume 的 halo 扫描固定 4 913 次查找，而自由放置的大体积通常是**稀疏**的。

风险：低（第 3 条需确认 halo 语义：稀疏遍历必须仍覆盖 18³ halo 内的邻居，
即 `-1..16` 的绝对范围 —— 稀疏遍历天然满足，因为它在遍历**数据**而不是格子）。

---

### P9 — 解算相关的逐帧/逐结果开销 【中低】

`Source/FPSGAME/Building/VoxelBuildWorldStructure.cpp:73`

```cpp
for(const auto& E:Runtime->JobEpoch)if(Runtime->NodeEpoch.FindRef(E.Key)!=E.Value){Stale=true;break;}
```

`JobEpoch` 与 `NodeEpoch` 都是 `TMap<FVoxelBuildKey,uint64>`，
每个解算结果比对一次，规模 = 上轮解算节点数。2 万节点时是一次
2 万次 `FindRef` 的遍历（早退能缓解，但「不陈旧」时必然走满）。这是每轮解算一次，
不是每帧，可接受；但可以改成比较**一个整体 revision 计数器**（`NodeEpochRevision`），
O(1) 判定是否可能陈旧，只有可疑时再做逐键校验。

`Source/FPSGAME/Building/VoxelBuildWorldStructure.cpp:237`

```cpp
if(++Count>=NodeCap)
```

**死上限缺陷**：`Count` 只在**成功收进节点**时递增，但 `NodeCap` 默认 4096 而
`MaxSolveNodesCVar` 的下限是 64。当 `NodeCap` 判定触发时 `Runtime->GatherRead=Runtime->GatherQueue.Num()`
并 `break` —— 这是对的。但注意 `Count` 的递增在 `continue` 分支之前
（`:222` 的 `if(!Node||PendingCells.Contains)continue;` 会跳过），
所以 `Count` 实际是「本次收集到的节点数」。当**单帧**因为 `:245` 的
`Count>=512 && 耗时>.001` 提前 break 时，下一帧继续（`GatherRead` 保留），
`Count` 从 0 重新计 —— 这意味着 **`NodeCap` 永远无法跨帧生效**，
只有单帧内收满 `NodeCap` 才触发。因为 `:245` 的 512 格/1 ms 预算先到，
所以 `MaxSolveNodes`（默认 4096）实际上**永远不会被触发**，
`Gather.Boundary` 也就永远不会因为节点上限而被填充。

影响：工作流第 2 节承诺的「一次解算最多收集 `fps.Building.MaxSolveNodes` 个连通节点」
在默认配置下不成立。超大建筑会**逐帧无限收集**直到整个连通块收完
（只在 `SolveRegionHops` 裁剪下才受控）。这是一个**真实的性能与语义缺陷**：

```cpp
if(++Count>=NodeCap)   // Count 每帧从 0 开始
```

**修法**：把计数拆成「跨帧累计」与「本帧预算」两个变量，例如
`int32 Gathered=Runtime->Gather.Nodes.Num();` 用累计值判 `NodeCap`，
`Count` 只用于本帧预算。

风险：低。这是明显的实现疏漏；修完要复核「超大建筑的面板最弱接缝是局部读数」
这一既有承诺仍然成立。

---

### P10 — `ApplyChanges` 与 `VerifyPrefabSupport` 的线性扫描 【中低】

`Source/FPSGAME/Building/VoxelBuildWorld.cpp:339-340`

```cpp
if(const auto* Existing=SupportGraph->Nodes.Find(Key);Existing&&Existing->AddedMassKg>0)
    for(auto It=Runtime->Loads.CreateIterator();It;++It)if(It.Value().Key==Key)It.RemoveCurrent();
```

对**每个编辑格**遍历**全部载荷**。载荷数量通常是个位数（玩家 + 道具），
所以常见情形代价很小 —— 但它是 O(编辑格 × 载荷)。若「物理道具落在建筑上」的场景变多
（文档提到残骸不计载荷，但道具照算），这里会放大。
建议加 `TMap<FVoxelBuildKey,FName> LoadsByCell` 反查。

`Source/FPSGAME/Building/VoxelBuildWorldPrefab.cpp:206-209`

```cpp
for(const FIntVector& Anchor:Drop)
{
    const FVoxelBuildPrefabInstance* Instance=Prefabs.FindByPredicate(
        [Anchor](const FVoxelBuildPrefabInstance& Entry){return Entry.Cell==Anchor;});
```

`Drop` 循环内线性扫 `Prefabs` → O(脱落件 × 构件总数)。见 P5 第 2 条修法。

---

### P11 — 每帧字符串构造与 Slate 无效化 【低】

`Source/FPSGAME/Building/VoxelBuildComponent.cpp:1218-1252`（`UpdateWidget`，每帧调用）

每帧构造的临时 `FString` 数量：

- `:1231` `ClipNote` + `Message`：`Feedback/.../TargetMessage` 拷贝 +
  `ClipNote` 拼接 + `TEXT("\n")` + **`BuildWorld->StructureStatus()`**
- `StructureStatus()`（`VoxelBuildWorld.cpp:478-491`）内部再拼
  `JointSummary`（`:440-450`，含 1 次 `Printf`）+ `SolverSummary`（`:493-501`，1 次 `Printf`）
- `:1235` 1 次 `Printf`（构件分支）/ `:1248` 1 次 `Printf`（体素分支）
- `:1247` `Where` 1 次 `Printf`
- `WeakestJointSummary()` 在 `:1227`/`:1238`/`:1251` 各构造一次

即**每帧约 6–8 次 `FString` 堆分配**（多数走 SSO，长串会真分配）。

好消息：`UVoxelBuildWidget::ShowState`（`VoxelBuildWidget.cpp:886-887`）已经有
`Signature!=LastState` 守卫，`SetSelection`（`:410`）也有早退，
`RefreshLayout`（`:802`）有视口/缩放守卫 —— 这些地方**没有**每帧刷 Slate。
所以这条是**低收益**，但零风险。

**修法**：`UpdateWidget` 加同样的「签名不变则跳过」守卫
（把 `Headline`/`Brush`/`Message` 的输入先拼成轻量签名，或缓存上次的
`BlockCount/PrefabCount/WeakestJointRatio/StructureStatus` 关键状态），
非建造状态（`!bActive`）时完全不调 `UpdateWidget`（`TickComponent:1341-1348` 已经早退，
所以只在建造态有效）。

`UpdateStructureWarning`（`:1254-1270`）每次调
`World.WeakestJointSummary()` 构造字符串 —— 只在 `Risk>=.85f` 时才需要。
把 `Summary` 的构造移到阈值判定之后（`:1263`）即可省掉常态下的每帧一次构造。

风险：无。

---

### P12 — 网格与碰撞的固有成本 【架构，需权衡】

`Source/FPSGAME/Building/VoxelBuildWorldMesh.cpp:101-121`

- 每个 chunk 一个 `UDynamicMeshComponent`（16³ 格 = 3.2 m 边长）。
  一个 20 000 格的建筑散布开来可达**上百个组件**，即上百次 draw call + 上百个物理体。
- `Component->SetSimpleCollisionShapes(Geometry->Collision,true)`（`:121`）
  会重建整个 chunk 的物理体；`SetMesh`（`:120`）重建渲染缓冲。
  两者都在**游戏线程**，靠 `MeshAppliesPerFrame=1` + 1.5 ms 预算节流
  （`:47`），所以不会一次卡死，但会**持续占用预算**。
- `VoxelSurfaceMesher.cpp:113` 的 `Values.SetNumUninitialized(Nodes*Nodes*Nodes)`
  是 81³ = **531 441 个 float ≈ 2.1 MB**，**每次块重建都分配**（即使只改了 1 格）。
  `:106` 的 `Coordinates`/`Blends` 同样按整块步数分配（各约 81–163 项，较小）。
  这是线程池上的分配，但有峰值内存与分配器压力。
- `VoxelSurfaceMesher.cpp:145` 的 `FlatMasks` 是 `TMap<FIntVector,TArray<int32>>`，
  每个 mask `Init(0, Steps*Steps)` = 80² = 6 400 个 int32 ≈ 25 KB，最多 6 个方向。

**修法**（按性价比）：

1. **`Values` 复用缓冲**：把 `Values` 做成线程局部/作业持有的可复用 `TArray<float>`，
   只 `SetNum` 不重新分配。单块从「每帧 2.1 MB 分配」变成「一次分配、反复使用」。
   **这条最划算且零风险。**
2. **chunk 尺寸**：`ChunkSide=16`（3.2 m）。改成 32 能让组件数降 8 倍，
   但单块重建成本与 `Values` 内存（162³ 无法接受）会爆炸 —— 所以当前 16 是合理折中。
   若要动，正确方向是**两级 LOD / 合并块**，不是简单调大。
3. 长期：`SetMesh` + `SetSimpleCollisionShapes` 的合并（一次 `SetMesh` 带 collision）
   或复用 `FDynamicMeshComponent` 的 deferred collision（代码已开
   `SetDeferredCollisionUpdatesEnabled(true,false)`，`:111`，可再确认合并时机）。

风险：1 低；2、3 中高，建议单独立项。

---

### P13 — 存档管线：每 0.75 s 在游戏线程全量快照 【中高】

`Source/FPSGAME/Building/VoxelBuildWorldSave.cpp:9-10`

```cpp
if(!Runtime->bSaveDirty)Runtime->SaveAt=GetWorld()->GetTimeSeconds()+.75;
Runtime->bSaveDirty=true;
```

截止时间只由**第一次**置脏决定，所以持续编辑时**每 0.75 s 就产生一次完整快照**
（`VoxelBuildWorldCollapse.cpp:156` 的残骸运动状态再叠加每 3 s 一次）。
而快照的**构造**全在游戏线程（`VoxelBuildWorldSave.cpp:56`），只有序列化+CRC+写盘在线程池（`:57-58`）：

```cpp
auto Payload=VoxelPersistence::Take(MakeSnapshot());Runtime->bSaveDirty=false;
Runtime->SaveJob=Async(EAsyncExecution::ThreadPool,[...]{return VoxelPersistence::Write(...);});
```

`MakeSnapshot()`（`:19-38`）每次都要：

- `NewObject<UVoxelBuildSave>()`（一个 **GC 跟踪的 UObject**，每次存档一个）
- 逐格拷贝 `Cells`（`:21-22`，20 000 格）
- `CellDamage`/`LegacyProtected`/`Prefabs` 的**完整 map 拷贝**（`:25`，含一次 rehash）
- 断键过滤，每个键 2 次 `VolumeMaterialAt` 查找（`:26-27`）
- `Data->Fragments.Add(E.Value->Snapshot())`（`:36`）—— **`Snapshot()` 按值返回，`Add` 再拷一次**，即残骸格被复制两遍

序列化规模（按字段宽度推导，`FVoxelBuildKey` = `FGuid` 16 + `FIntVector` 12 = 28 B）：

| 记录 | 单条字节 | 20 000 格建筑 |
| --- | ---: | ---: |
| `FVoxelSavedCell` | 12 + (4+len+1)，`"wood"` → **21** | **约 410–420 KB** |
| `Damage` 键值 | 28 + 4 = 32 | 每 1 000 格 +32 KB |
| `FVoxelBrokenBond` | 2×28 = 56 | 每 1 000 断键 +56 KB |
| `FVoxelDebrisCell` | 28+24+约9+4 = 65 | 每 1 000 残骸格 +65 KB |

典型 **450–500 KB**，最坏（全格带损伤 + 10 000 残骸格）**约 1.6–1.8 MB**。
每 0.75 s 在游戏线程拷 450 KB + 一次 UObject 分配 + 一次 damage map rehash。

**修法**（低风险部分优先）：

1. `Data->Fragments.Emplace(E.Value->Snapshot())` —— 去掉双拷贝，两行改动。
2. **直接填 `FVoxelDiskSnapshot`，删掉中间 `UVoxelBuildSave`**：该 UObject 的唯一用途
   就是被 `Take()` 立刻掏空（`VoxelBuildPersistence.cpp:36-42`）。注意 `Take()` 用
   `MoveTemp` 偷走成员（`:38`），删掉它同时消除「同一个对象 `Take` 两次得到空数据」的陷阱。
3. **存档合并到 ≥2 s 或「编辑停止后」**：`MarkSaveDirty` 里对「已经在等」的情况不重置
   截止时间（当前行为正确），但可加一条最小间隔，避免连续建造时每 0.75 s 一次。
4. 长期：**增量存档**（记录脏格，只更新快照对应槽位），需要压缩/版本路径，风险中。

风险：1、2 低；3 低（但崩溃丢失窗口变大，需用户确认）；4 中。

---

### P14 — 运行时容器只增不减（内存单调增长）【中】

审计确认以下容器**没有删除路径**（在 `Source/FPSGAME/Building/` 全目录 grep
无对应 `Remove`）：

| 容器 | 声明 | 写入点 | 后果 |
| --- | --- | --- | --- |
| `Runtime->NodeEpoch` | `VoxelBuildRuntime.h:59` | `World.cpp:338,342,356`、`Structure.cpp:52,122`、`Damage.cpp:99` | 被拆掉的格的键**整个会话不释放** |
| `Runtime->MeshGroups` / `MeshRevisions` / `AppliedRevisions` | `VoxelBuildRuntime.h:68-69` | `Mesh.cpp:29,31,44` | 外层每个「碰过的 chunk」永久留一条 |
| `Runtime->DamageQueue` | `VoxelBuildRuntime.h:73` | `Damage.cpp:59` 用 `EAllowShrinking::No` 移除 | 容量按峰值永久保留 |
| `UVoxelBuildIcons::Attempts` / `FailedKeys` | `VoxelBuildIcons.h:77-78` | `Icons.cpp:351,355` | 只在 `Deinitialize` 清 |

`FVoxelSupportGraph` 本身是每次 `RefreshSupportGraph` 重建的，所以不在此列；
但它的**单节点成本**很高（见 P7 第 2 条）：`Edges` 是「每节点一个 `TSet`」，
20 000 节点时约 **5.8 MB**（每个 `TSet` 容量取 2 的幂 = 8 槽 × 28 B + 哈希槽），
`Buckets` 又是全部键的第三份拷贝（`VoxelSupportGraph.cpp:7` 用格子坐标本身做桶键），
`Nodes` 约 2.5 MB（`FVoxelSupportNode` ≈ 104 B）。合计 **20 000 格约 8–10 MB**。

**修法**：给 `NodeEpoch`/`MeshGroups` 等在格被永久删除（进入残骸或回收）时补删除；
或改用「按 revision 分代的槽位」（`TArray<uint64>` 按稠密编号索引）自然回收。
`Edges` 改 CSR（P7 第 2 条）一次性解决 5.8 MB 与第三份键拷贝。

风险：中。`NodeEpoch` 是陈旧判定（`Structure.cpp:73`）的依据，删除必须保证
「已删除的键不会再被查询」。建议先加一个只在 `WITH_EDITOR` 下跑的容量断言/日志，
观察真实峰值再动。

---

### P15 — 图标子系统的显存与每帧重扫 【中】

`Source/FPSGAME/Building/VoxelBuildIcons.cpp`

- **每个缩略图 768 KiB 渲染目标**：两个 256×256 的 RT 每次新建
  （RGBA16F = 512 KiB + RGBA8 = 256 KiB），`IconSize=256`（`:19`）却只服务
  104 px 的卡片槽（`VoxelBuildWidget.cpp:48` `GridIconPixels=104.f`）。
  `MaxCachedIcons=32`（`:28`）≈ **24 MiB** 上限。
- **上限是软上限**：淘汰循环在「没有可淘汰项」时直接 `break`
  （`:371-381`），而 `VisibleKeys` 里的键不可淘汰 —— 抽屉里同时可见的条目超过 32 个时
  （展开多个材质行）缓存**无上限增长**。
- **每个图标 2 次 `CaptureScene()`**（`:315`），每帧最多 1 个作业
  （`VoxelBuildIcons.h:45` `IsTickable`），所以开抽屉时约 40 个卡片需要
  ≥40 帧（60 fps 下约 0.7 s）才能填满，期间每帧 2 次场景捕获。
- **`Find()` 每帧改写 LRU**：`VoxelBuildIcons.cpp:67`
  `if(const auto* Found=Materials.Find(Key))if(*Found){Uses.Add(Key,++Serial);return *Found;}`
  —— 被 `VoxelBuildWidget.cpp:497-517` 每帧对每张卡片调用，即每帧每卡片一次哈希写入。
- **占位文本每帧重建**：`VoxelBuildWidget.cpp:514`
  `Placeholder->SetText(FText::FromString(Icons->HasFailed(...)?TEXT("暂无预览"):TEXT("加载中")));`
- **纹理常驻请求每作业重复下发且从不释放**：`:298`
  `Texture2D->SetForceMipLevelsToBeResident(1.f);`，而 `WarmingTextures` 每次
  `ClearPool()`（`:106`，被 `:198`、`:346` 调用）都清空。

**修法**：渲染降到 128²（卡片只显示 104 px，视觉差异需用户确认）；
**复用同一对 RT**（单作业管线本来就串行）；淘汰时给 `VisibleKeys` 加硬上限；
`Find()` 的 LRU 触达改到「重建/悬停」时；把两个占位字符串提成 `static const FText`。
风险：RT 复用需要重绑材质纹理参数，中；其余低。

---

### P16 — 面板/抽屉的每帧无效写 【低，但零风险】

- `VoxelBuildWidget.cpp:885-887`：`ShowState` 每次调用都**先**构造
  `SelectionText`（1 次 `Printf`）再拼 `Signature`（1 次拼接），**之后**才比较
  `Signature!=LastState` —— 守卫存在但成本已经付掉。而它每帧被调用
  （`VoxelBuildComponent.cpp:1359` 面板态、`:1375` 建造态）。
  应把签名前置（或由组件传一个数值状态 id）。
- `VoxelBuildWidget.cpp:870-884`：`Risk` 块在签名检查**之前**无条件执行，
  每次重设 `SetVisibility` 并在告警时再做 2 次 `Printf`。
- `VoxelBuildWidget.cpp:907-916`：`SetRenderTranslation`、两次 `SetRenderOpacity`、
  `SetVisibility`（`Backdrop`/`Blur`）在抽屉已完全展开/收起时仍然每帧写。
  （UMG setter 无「值未变」守卫；Slate 侧是否因此无效化**未验证**。）
- `VoxelBuildWidget.cpp:765-780`：`RefreshSelection` 每次选择变化重建每张卡片的
  `FSlateBrush` 并 `SetBrush` —— O(卡片数) 次 Slate 无效化，每次点击/数字键一次。
- `VoxelBuildWidget.cpp:252-280`：悬停时 `TooltipBox->ClearChildren()` 并逐行重建控件；
  `:331-343` 每帧 `GetCursorPos()` + 写 `TooltipSlot`.

**修法**：签名前置；`Risk` 块移到阈值判定之后；渲染写入加「值变才算」守卫
（`DrawerProgress` 已在端点时跳过）；选择刷新只改前后两张卡片；浮窗行做池化。
风险：全部低。

---

### P17 — 加载路径的冗余与无预留 【中，一次性】

`AVoxelBuildWorld::Initialize`（`VoxelBuildWorld.cpp:89-165`）全在游戏线程、同步：

1. **`SolveConnectivity()` 跑两遍**：`RefreshSupportGraph()` 内一次（`:228`），
   应用断键后又一次（`:151`）。加载前两次完整 BFS。
   **修法**：把 `BrokenBonds` 的 `Break`（`:150`）移到 `RefreshSupportGraph` **之前**，
   一次即可。
2. **`RebuildAffected(全部格)`**（`:156`）：`RebuildAffected` 每格扩 ±1 共 27 个 chunk key
   （`VoxelBuildWorldMesh.cpp:23-25`），20 000 格 = **540 000 次 `TSet::Add`**。
   加载时不需要 halo（还没有邻居改动），可直接由 `ChunkFor(Cell)` 得出脏块集。
3. **`TArray<FVoxelEditCell> Loaded` 无 `Reserve`**（`:154-155`）：
   `FVoxelEditCell` ≈ 48 B × 20 000 ≈ **1 MB**，按 log2 次重分配。
4. **自由体积被拷贝而非移动**：`:122` `FreeVolumes.Add(Volume.Id,Volume);`
   （循环变量是 `const auto&`）→ 每个体积多一次内层 map 建表。
   `:142` 的 `CellDamage=LoadedData->Damage;` 同理是整表拷贝。
   **修法**：`MoveTemp` 或直接反序列化进世界容器（需改 `Load` 签名，中风险）。
5. 构件：线性 `Palette->FindComponent`（`VoxelBuildPalette.h:82-85`，`FindByPredicate`）
   + 每件 `Mesh.LoadSynchronous()`（`:137`）→ O(件数 × 条目数) + 同步资产加载。
6. 之后是全量重网格（所有 chunk 置脏，2 作业/帧、1 应用/帧）与全量解算
   （`:157` 播种全部节点，`LastFullSolveAt=0` 使首次为全量），
   受 `MaxSolveNodes` 截断（默认 4096）。

风险：1、3 低；2 低（需确认 halo 在加载时确实不需要）；4、5 中。

---

### P18 — 碎片回收失败时每帧重做全部转换工作 【中高】

`Source/FPSGAME/Building/VoxelBuildWorldCollapse.cpp:121-133`

```cpp
TArray<FGuid> Recycled;
const float FrameDelta=GetWorld()->GetDeltaSeconds();
for(const auto& E:Fragments)
{
    AVoxelCollapseFragment* Fragment=E.Value;
    if(!IsValid(Fragment)||!Fragment->AccrueRestSeconds(FrameDelta,2.f))continue;
    const FVoxelFragmentSave Settled=Fragment->Snapshot();
    TMap<FString,int64> Blocks;
    for(const FVoxelDebrisCell& Cell:Settled.Cells)
        if(!Cell.Material.IsNone())Blocks.FindOrAdd(FString(TEXT("voxel_block_"))+Cell.Material.ToString())++;
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(Model&&!Blocks.IsEmpty()&&Model->GrantWorldBlocks(Blocks,Fragment->GetActorLocation()))Recycled.Add(E.Key);
}
```

`GrantWorldBlocks` 在**背包/地面物品达到存档上限时会返回 false 且不做事**
（`Source/FPSGAME/UI/ColdSteelAreaPickup.cpp:55`
`if(P.Items.Num()>=10000){Message=TEXT("地面物品已达存档上限，残骸暂未转换");return false;}`）。

此时 `Recycled` 为空 → 碎片**不被删除** → 下一帧进入同一分支，**再付一次全部代价**：

- `Fragment->Snapshot()`（`:127`）—— 按值返回并拷贝**全部残骸格**（`FVoxelFragmentSave`）
- 逐格构造 `FString(TEXT("voxel_block_"))+Cell.Material.ToString()`（`:130`）
  —— 即**每格一次 `FName::ToString()` + 一次字符串拼接**
- 地面物品循环内的 `FindOrAdd`

对每个「已静止但回收失败」的碎片，**每帧**重复。背包满（或地面物品 ≥10 000）
是**可以长期持续**的状态，且残骸越多越贵 —— 一块 4 096 格的大残骸就是每帧
4 096 次 `FName::ToString()`。`AccrueRestSeconds` 一旦达到 2 s 就恒为 true
（`VoxelCollapseFragment.h:36-38` 的 `RestSeconds` 不清零），所以这是个**持续**的每帧成本。

**修法**（任选，第一条最小）：

1. **把 `TMap<FString,int64>` 缓存到碎片上**，只在 `UpdateCellDamage` 时重建
   （`:130` 的 key 集合只随格集合变化）；`GrantWorldBlocks` 失败时记一个重试计时器
   （例如 1–2 s 退避），不要在下一帧立刻重试。
2. `Settled` 只在需要回收时取一次（当前每次成功也要 snapshot，但成功路径可接受）。
3. 长期：残骸回收改成「进入地面物品」之外的通道（直接进背包失败就不转），
   或把上限处理成「排队等空间」而不是每帧重试。

风险：1 低；3 中（改物品语义）。

> **更正**：本节初稿（依据委派审计的措辞）说 `continue` 会绕过 4 条/帧的预算。
> 复核后**这是错的** —— `Processed` 在 `:129` 与预算检查同一行递增，
> 且 `:57` 的 `while` 在 `IsEmpty()` 时退出，所以**真正被处理**的条目最多 4 条/帧。
> 真正的问题在 P19（`:75`/`:78`/`:88` 的 `continue` 跳过了 `:129` 那一行）。

---

### P19 — `DamageQueue` 的 `continue` 路径跳过预算检查，可单帧耗尽队列 【中，真实缺陷】

`Source/FPSGAME/Building/VoxelBuildWorldDamage.cpp:129`

```cpp
if(++Processed>=4||FPlatformTime::Seconds()-Start>.0015)break;
```

这一行的 `++Processed` 是**唯一的**预算递增点，但循环体内有四处 `continue`
在它**之前**跳出本次迭代：

| 行 | 条件 | 何时命中 |
| --- | --- | --- |
| `:67` | `if(Runtime->PendingCells.Contains(Key))continue;` | 目标格正在倒塌流程中 |
| `:75` | `if(Replacing)continue;` | 碎片正被替换（`PendingFragments` 里有 `Replaces==Id()`） |
| `:78` | `if(Targets.IsEmpty())continue;` | 该请求没有命中任何格 |
| `:88` | `if(Total<=0)continue;` | 权重合计为 0 |

所以**这些条目不消耗预算**。`TickDamage` 每帧从 `:57` 的 `while` 开始，
一边 pop 一边走 `continue`，直到队列空或碰到一条**真正被处理**的条目。
队列长度就是上界 —— `Runtime->DamageQueue` **无上限、无去重**
（`VoxelBuildRuntime.h:73`，推入点 `:33`/`:39`/`:45`/`:197`）。

危险场景：一批碎片进入替换流程后，新到的碎片伤害请求全部在 `:75` 被 `continue`，
此时一帧内可以把整个队列（可能上万条）**全部 pop 完** —— 而每条都要付
`:60-62` 的构造 + `GetActorTransform().InverseTransformPosition`，
以及 `:74` 对 `PendingFragments` 的**全量扫描**：

```cpp
bool Replacing=false;for(const auto& E:Runtime->PendingFragments)Replacing|=E.Value->Replaces==Fragment->Id();
```

这是个 O(待替换碎片数) 的内层循环，**放在 pop 循环里**。合计单帧
**O(队列长度 × 待替换碎片数)**。

另外 `:59` 的 `RemoveAt(0,1,EAllowShrinking::No)` 每 pop 一次就是 **O(n) memmove**。
正常路径只 pop 4 条 → O(4n)/帧（n = 队列长度）；队列到 10 万时每帧约 240 万次字移动。
配合上面那条路径则是 **O(n²) 单帧**。`EAllowShrinking::No` 还让峰值容量永久保留。

**修法**（低风险，建议全做）：

1. **预算检查提到循环顶部**，让每次 pop 都计数：

   ```cpp
   while(!Runtime->DamageQueue.IsEmpty())
   {
       if(++Processed>4||FPlatformTime::Seconds()-Start>.0015)break;
       ...
   }
   ```

   （同时删掉 `:129` 里的 `++Processed`，那里只留时间检查。）
2. **改头索引/环形缓冲**替代 `RemoveAt(0)`：加 `int32 DamageRead`，
   每帧末尾一次 `RemoveAt(0,DamageRead)`，或定期压缩。
3. **`Replacing` 判定改 `TMap` 反查**替代遍历 `PendingFragments`。
4. 给 `DamageQueue` 加上限/合并 —— 有语义风险，见 C14，单独评估。

风险：1、2、3 低。

---

### P20 — 等预算的残骸被当成"已静止"提前回收 【中，功能性缺陷】

`Source/FPSGAME/Building/VoxelCollapseFragment.cpp:51`

```cpp
bool AVoxelCollapseFragment::IsMoving() const {return bStarted&&!bReplacing&&Body->IsAnyRigidBodyAwake();}
```

`bStarted` 只在 `Activate()`（`:47`）里置真，而 `Initialize()`（`:22-32`）**不置**。
所以一件已经生成、但**因为准入预算还没轮到模拟**的碎片，`IsMoving()` 返回 **false**。

`AccrueRestSeconds`（`VoxelCollapseFragment.h:34-39`）据此累计静止时间：

```cpp
if(IsMoving()){RestSeconds=0;return false;}
RestSeconds+=Delta;
return RestSeconds>=Threshold;
```

于是这类碎片的 `RestSeconds` **从生成那一刻就开始累加**，2 s 后
`TickFragments` 的回收分支（`VoxelBuildWorldCollapse.cpp:126-138`）把它

```cpp
const FVoxelFragmentSave Settled=Fragment->Snapshot();
...
if(Model&&!Blocks.IsEmpty()&&Model->GrantWorldBlocks(Blocks,Fragment->GetActorLocation()))Recycled.Add(E.Key);
...
for(const FGuid Id:Recycled)
{
    if(AVoxelCollapseFragment* Fragment=Fragments.FindRef(Id))Fragment->Destroy();
```

**转成方块并销毁 —— 它从未模拟过**。

准入预算是 `Bodies=128` / `Shapes=2048`（`VoxelBuildWorldCollapse.cpp:12-13`），
激活速度是每帧 8 件（`:153`）。一次大倒塌产生的碎片数超过 128 时，
排在后面的碎片本来就在等（`VoxelBuildWorldCollapse.cpp:148-149`
`if(!Sleeping&&(Runtime->AwakeBodies>=...||...)){++I;continue;}`）。
对「睡眠」（`State.bSleeping`）碎片这条不成立，所以**只有曾被模拟过又睡着的**
才安全；被预算挡住的必中此缺陷。

表现：倒塌后一部分碎块**凭空消失并变成脚下方块**（观感是"塌了一半就没了"），
而且碎片数量越大越明显 —— 正好是最需要它正确的场景。

**修法**：`AccrueRestSeconds` 增加「必须已启动」前提，即

```cpp
if(!bStarted||IsMoving()){RestSeconds=0;return false;}
```

或在 `IsMoving()` 里把未启动也算作"未静止"（但那会改变 `:113-115` 的醒着统计语义，
`AwakeBodies` 会被低估）。**推荐改 `AccrueRestSeconds`**，它只有一个调用点。
风险：低。建议同时加一条日志区分「回收了从未激活的碎片」。

### P21 — 每帧三次全量碎片遍历 + 两次 Chaos 查询 【中低】

`Source/FPSGAME/Building/VoxelBuildWorld.cpp:418` + `VoxelBuildWorldCollapse.cpp:113-145`

每帧对 `Fragments`（`TMap<FGuid,TObjectPtr<AVoxelCollapseFragment>>`）的完整遍历：

1. `VoxelBuildWorld.cpp:418` `for(const auto& E:Fragments)if(IsValid(E.Value))E.Value->SampleVelocity();`
   —— 每件一次 `GetPhysicsLinearVelocity`（Chaos 查询）
2. `VoxelBuildWorldCollapse.cpp:113-116` `IsMoving()`（`Body->IsAnyRigidBodyAwake`，第二次物理查询）
   + 位置 / `KillZ` 检查
3. `VoxelBuildWorldCollapse.cpp:123-133` 回收扫描（见 P18）
4. `VoxelBuildWorldCollapse.cpp:140-145` 激活扫描，对每个 `MeshBarrier` 条目做
   `AppliedRevisions.FindRef`（每个 barrier 可达 27×格数 条）

即每帧 `O(碎片数)`，含 2 次物理查询/件。碎片数量在准入预算下**没有上限**：
`Bodies=128` 只限制**醒着的**数（`VoxelBuildWorldCollapse.cpp:148-149`），
睡着的碎片可以任意多 —— 长期游玩的残骸累积会让这几遍遍历持续变贵。

另外 `AVoxelBuildWorld` 自身永远 tick：`VoxelBuildWorld.cpp:46`
`PrimaryActorTick.bCanEverTick=true;` 从未 `SetActorTickEnabled(false)`，
即使世界里一格建筑都没有，每帧仍跑
`TickDamage/TickMeshes/TickFragments/TickStructure/TickPersistence` 五个函数。
（对照 `AVoxelCollapseFragment` 正确地设了 `bCanEverTick=false`，
`VoxelCollapseFragment.cpp:9`。）

**修法**：合并成一个循环，一次遍历算出 `IsMoving`/`Position`/`RestSeconds`
（两次物理查询合并为一次）；`Sleeping` 的碎片跳过 `SampleVelocity`；
在「没有建筑 + 没有碎片 + 脏集为空」时 `SetActorTickEnabled(false)`，
有编辑/碎片时再开启。风险：低。

### P22 — `Split` 与贪心盒合并的重复拷贝/重复哈希 【中低】

`Source/FPSGAME/Building/VoxelBuildGeometry.cpp`

- `:108` `FVoxelFragmentSave Part=Source;` —— **每个连通岛都完整拷贝一次源碎片**
  （全部 cells + 全部 `BrokenBonds`），紧接着 `Part.Cells.Reset()` 把内容丢掉，
  再在 `:109` 用 `Indices.FindChecked(K)` 逐格填回来。即 **O(N × 岛数)** 的纯浪费拷贝；
  大碎片 + 多岛时是数 MB 级无用复制。
  **修法**：`Part` 只拷元数据（`Id`/`Transform`/`Velocity`/`AngularVelocity`/`bSleeping`），
  `Cells` 直接按索引表构造。
- `:113-125` 细分循环**每一层都重算** `Volumes(...)`（`:116`）与 `Boxes(...)`（`:117`）：
  `Volumes` 建 `TMap<FIntVector,int32>` + `TSet<FIntVector>` 两个容器；
  `Boxes` 做 `Ordered.Array()` + 自定义比较排序 + 逐行/逐层 `Contains` 验证。
  层数随碎片形状可达 log₂(格数)。
  **修法**：把盒数沿细分传递，不要每层重算。
- `:129-140` 重键阶段每个 part 建两个 `TMap`（`VolumesMap`、`Keys`），
  并对**全部** `Graph.Broken` 逐条 `Keys.Contains` 两次（`:138`）。

风险：低到中（`Split` 决定残骸的物理体划分，改完要目视确认碎块分组不变）。

### P23 — `AnchorCache` 是只写不读的死容器 【低，但纯浪费】

`Source/FPSGAME/Building/VoxelBuildWorld.h:156`

```cpp
TMap<FVoxelBuildKey,bool> AnchorCache;
```

全目录 grep 只有**写入**与**删除**，**没有任何读取**：

| 位置 | 操作 |
| --- | --- |
| `VoxelBuildWorld.cpp:226` | `AnchorCache.Add(E.Key,E.Value.bAnchor);` |
| `VoxelBuildWorld.cpp:343` | `AnchorCache.Remove(Key);` |
| `VoxelBuildWorld.cpp:351` | `AnchorCache.Add(Key,Anchor);` |
| `VoxelBuildWorldPrefab.cpp:121` | `AnchorCache.Add(Key,false);` |

它本意是缓存 `IsGroundAnchor` 的射线结果（每格最多 5 条射线），
但既然从没被读过，**一点射线都没省下**，只是每格多占一个 `TMap` 条目
（键 28 B + bool + 哈希槽）。20 000 格约 0.6 MB 的纯浪费，随建筑规模线性增长。

**修法**：要么真读它（在 `IsGroundAnchor` / `RefreshSupportGraph` 里命中就直接返回），
要么删掉。**推荐先删** —— 当前它只贡献内存与 `Add`/`Remove` 成本。
风险：低（确认无读取后删除即安全）。删之前建议再全局 grep 一次，防止有分支在
`#if WITH_EDITOR` 下读取（本轮已 grep 全目录，未见）。

---

### C1 — `VoxelJointStrength::Ratio` 的 `static` 缓冲是**数据竞争** 【高】

`Source/FPSGAME/Building/VoxelJointStrength.h:86`

```cpp
static long long Lookup[64 * 64 * 64];
std::fill(Lookup, Lookup + 64 * 64 * 64, -1);
```

函数内 `static`（非 `thread_local`）的共享可变缓冲，且 `Ratio` 会被：
- 游戏线程调用（`PushPanelContent` → `MaxSpanMeters`，`VoxelBuildComponent.cpp:460-461`）
- 线程池调用（若按文档 3.3 的既有建议把面板计算移入后台）

两个线程同时进入 → **数据竞争**，`Lookup` 被一方清零时另一方正在读，
结果是**跨度数值静默错误**（不是崩溃）。即使目前只从游戏线程调用，
`VoxelJointStrength.h` 是与 `voxel_stress_probe.cpp` 共享的头，
探针若将来并行化也会命中。

**修法**：P4 的缩表方案顺手解决（`int32 Lookup[6*28*7]` 放栈上是 4.7 KB，
直接变成函数局部变量，连 `static` 都不需要）。**推荐把 P4 和 C1 一起修。**

### C2 — `Near()` 与 `GatherRead` 的单帧预算使 `MaxSolveNodes` 失效 【中】

见 P9 的详细分析。这是**实现与文档承诺不一致**，属正确性范畴。

### C3 — `VoxelBuildComponent::ValidatePlacement` 缺 `BuildWorld` 空检查 【低】

`Source/FPSGAME/Building/VoxelBuildComponent.cpp:1033-1052`

```cpp
void UVoxelBuildComponent::ValidatePlacement()
{
    const double Now=GetWorld()->GetTimeSeconds();
    const bool Changed=CheckedRevision!=BuildWorld->StructureRevision()||...
```

同文件其它函数（`UpdateTarget:566`、`UpdatePrefabTarget:843`）都检查了
`!BuildWorld`，这里没有。当前调用链上 `UpdateTarget` 已提前返回，
所以**现在不可达**；但 `ValidatePlacement` 是私有成员、未来可能被新路径调用。
建议加 `if(!BuildWorld)return;`。

### C4 — `FNameAsStringProxyArchive` 的存档体积 【低，需实测】

`Source/FPSGAME/Building/VoxelBuildPersistence.cpp:52`

```cpp
FNameAsStringProxyArchive Ar(Reader);Ar.ArMaxSerializeSize=Bytes.Num();
```

`FName` 以**字符串**序列化（这是为了跨版本/跨进程稳定，选择本身合理）。
每格 = `FIntVector`（12 B） + 材料名字符串（如 `"wood"` = 4 B 长度 + 5 B）。
20 000 格 → 约 0.5–1 MB；`Damage`（`TMap<FVoxelBuildKey,float>`，键 28 B）与
`BrokenBonds`（`TSet<FVoxelBuildBond>`，2 × 28 B）会显著放大。
存档在线程池上（`VoxelBuildWorldSave.cpp:57`），**不卡帧**，所以优先级低。
建议在 2 万格实测存档大小与 `TickPersistence` 的写入耗时，再决定是否换二进制 `FName` 索引表。

### C5 — 版本兼容与旧档兜底路径 【待确认】

`VoxelBuildWorld.cpp:109` 的版本检查是 `Version<1||Version>4`，
`VoxelBuildPersistence.cpp:31` 只对 `Version>=4` 读 `Prefabs`。
向前兼容路径看起来完整。旧 `USaveGame` 反射路径
（`VoxelPersistence.cpp:48` 的 `LoadGameFromMemory`）作为 magic 不匹配时的兜底，
**未验证**该路径在 UE 5.8 下是否仍可用（`UVoxelBuildSave::Prefabs` 是
非 `UPROPERTY` 的自定义序列化字段，反射路径读不到它 —— 代码里 `:33` 有注释说明，
所以旧档的构件会丢，属已知取舍）。

### C6 — 存档 CRC/解析失败会把整个建造世界变成不可用，且报错原因错误 【高】

`Source/FPSGAME/Building/VoxelBuildPersistence.cpp:50-54`

```cpp
if(Size!=uint32(Bytes.Num()-12)||FCrc::MemCrc32(Bytes.GetData()+12,Size)!=Crc)return nullptr;
...
if(Ar.IsError()||Reader.Tell()!=Bytes.Num())return nullptr;
```

CRC 不符或解析出错都**静默返回 `nullptr`**，而调用方把「任何 `nullptr`」一律当成版本问题：

`Source/FPSGAME/Building/VoxelBuildWorld.cpp:109-110`

```cpp
if(!LoadedData||LoadedData->Version<1||LoadedData->Version>4||LoadedData->CellSizeCm!=20||LoadedData->WorldKey!=WorldKey)
{Message=TEXT("建筑存档版本不兼容，已保留原档");return false;}
```

后果：① 玩家看到的是**错误的**原因（版本不兼容）；② 没有任何日志；
③ **不回退**到 `Write` 自己维护的 `.pre-structure` 备份
（`VoxelBuildPersistence.cpp:71-76`）；④ `Initialize` 返回 false 后
`SetBuildMode` 显示 `InitializationMessage` 并拒绝进入建造（`VoxelBuildComponent.cpp:229-231`），
即**建造功能整体不可用**，而不是「部分建筑丢失」。

**修法**：区分「文件不存在 / CRC 失败 / 解析失败 / 版本过高 / 世界键不匹配」四种返回，
分别打日志并给出不同的 `Message`；CRC/解析失败时自动尝试 `.pre-structure`；
把失败限制在「这一份存档」，而不是让整个建造系统不可用。

风险：低。`VoxelPersistence::Load` 的返回类型需要从 `UVoxelBuildSave*` 扩展为
「指针 + 原因」，或加一个 `FString& OutError` 出参。

### C7 — 存档写入只有 Windows 实现，其它平台永久重试 【中】

`Source/FPSGAME/Building/VoxelBuildPersistence.cpp:83-85`

```cpp
#else
    return false;
#endif
```

非 Windows 平台 `Write` **恒返回 false**。配合
`VoxelBuildWorldSave.cpp:47` 的失败重排：

```cpp
if(Runtime->bSaveFailed){Runtime->bSaveDirty=true;Runtime->SaveAt=GetWorld()->GetTimeSeconds()+5;}
```

结果是**永远存不下去，且每 5 s 重新做一次全量快照**（P13 的 450 KB 拷贝 + UObject 分配），
`Statusline` 常驻「保存失败」。同时 `.pending` 临时文件在失败路径上从不清理。

项目当前只跑 Win64，所以这条**现在不影响**；但它意味着任何非 Windows 构建
（或以后的专用服务器/编辑器跨平台）会静默地持续做无用功。
**修法**：补一个 `IFileManager::Get().Move(...)` 或一次性 `Delete`+`Move` 的通用路径，
并把 `.pending` 在失败分支里删掉。

### C8 — 单条坏记录让整份存档加载失败 【中】

`Source/FPSGAME/Building/VoxelBuildWorld.cpp:113`

```cpp
if(!MaterialSlots.Contains(Cell.Material)){Message=TEXT("建筑存档缺少材料定义，已保留原档");return false;}
```

同样的 fail-closed 模式出现在自由体积（`:119`、`:121`）与残骸（`:128`、`:131`）。
一个未知材质、一个 NaN 变换就**整份存档不可用**。构件是唯一会跳过的类型
（`:138` `UE_LOG(...skipped an unknown prefab piece...)` + `continue`）。

对于「材质 ID 是稳定存档键、将来可能新增/改名」的设计（工作流第 4 节），
这条是**可预期会踩到**的：删掉一种材质后，所有用到它的旧档全废。
**修法**：照构件的口径改成「跳过该格并记一条 warning」，而不是整份拒绝。

### C9 — 过载渐进损伤的中间态没有置脏 【中】

`Source/FPSGAME/Building/VoxelBuildWorldStructure.cpp:45-53`

```cpp
CellDamage.Add(Entry.Key,Damage);
if(auto* Node=SupportGraph->Nodes.Find(Entry.Key))Node->Damage=Damage;
if(!LegacyProtected.Contains(Entry.Key))Runtime->DirtySupport.Add(Entry.Key);
Runtime->NodeEpoch.Add(Entry.Key,Revision+1);
bChanged=true;
```

累加损伤时**没有 `MarkSaveDirty()`**；只有损伤满耐久走
`Removed` 分支（`:55` 的 `ApplyChanges(Removed)`）才会置脏。
所以「被打伤但没打掉」的格子，其损伤值只靠 `EndPlay` 的无条件 flush
（`VoxelBuildWorldSave.cpp:49-53`）才落盘 —— **崩溃/强退就丢失**。
对照 `VoxelBuildWorldDamage.cpp:110` 的伤害路径是有 `MarkSaveDirty()` 的。

**修法**：在 `bChanged` 为真时调 `MarkSaveDirty()`。风险：低
（代价是过载期间每 0.75 s 触发一次存档，与 P13 第 3 条的合并策略一起考虑）。

### C10 — 「全量」状态行在节点截断时仍在报 【低】

`Source/FPSGAME/Building/VoxelBuildWorld.cpp:497-498`

```cpp
return Runtime->bGatherFullSolve
    ?FString::Printf(TEXT("\n求解 %.1f ms · %d 节点（全量）"),Runtime->LastSolveSeconds*1000.f,Runtime->LastSolveNodes)
```

`bGatherFullSolve` 只表示「这次没有按 `SolveRegionHops` 裁剪」，**不表示收满了整块结构**。
结构超过 `MaxSolveNodes`（默认 4096，`VoxelBuildWorldStructure.cpp:23`）时，
`:237-244` 会停在上限并把其余邻居标成边界，但状态行仍写「全量」。
20 000 节点的建筑会在 4096 节点时声称「全量」。这与 P9 的计数缺陷是同一处代码，
修 P9 时顺带把 `bGatherFullSolve` 改成语义正确的 `bSolvedWholeGraph`。

### C11 — 审计工具的存档校验可以「假通过」 【低】

`Source/FPSGAME/Building/VoxelBuildAudit.cpp:139-140`

```cpp
const FString File=FPaths::ProjectSavedDir()/TEXT("SaveGames")/(SaveSlot+TEXT(".sav"));
Report(TEXT("build save written to disk"),SaveSlot.IsEmpty()||IFileManager::Get().FileSize(*File)>0);
```

`SaveSlot` 是 world key 的确定性 MD5（`VoxelBuildWorld.cpp:95-97`），
所以**上一次会话留下的文件**就能让这条通过；而检查在最后一次编辑后 1.5 s 触发
（`FPSGAMEPlayerController.cpp:65-69`），存档却被推迟 0.75 s 且是异步写。
既不校验 CRC/内容，也不比对 mtime。**修法**：写入后重读并校验
magic/CRC，或比对 mtime 晚于本次编辑时间。

`VoxelBuildAudit.cpp:84`、`:87` 另有一处：从
`FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")` 读文本做
`Text.Contains(Id)` 子串匹配 —— 打包构建没有这个路径，且注释掉的条目也会通过。

`VoxelBuildAudit.cpp:121-123` 还丢弃了 `CheckPlacementRoundTrip()` 的返回值：

```cpp
CheckPlacementRoundTrip();
if(Stage==0)Stage=2;
```

### C12 — `VoxelBuildDebug::Enabled()` 每次调用做字符串 CVar 查找 【低】

`Source/FPSGAME/Building/VoxelBuildDebug.h:14`

```cpp
const IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Building.DebugLog"));
```

每次诊断调用都做一次哈希字符串查找，而且它**静默依赖另一个翻译单元**里的
`TAutoConsoleVariable`（`VoxelBuildWorld.cpp:27`）—— 若那个 TU 未被链接，
开关会永远为 0 且没有报错。**修法**：把 CVar 声明成 `extern` 共享，
或缓存 `IConsoleVariable*`（CVar 在 `TAutoConsoleVariable` 生命周期内稳定）。

### C13 — 文档与代码的迭代次数不一致（512 vs 256）【低，但影响数值可信度】

`Docs/Building/voxel-build-workflow.md:225` 写：

> 用项目自带的 `Source/ThirdParty/Blast/Lib/Win64/FPSBlast.lib` … **512 次迭代**。

而共享头 `Source/FPSGAME/Building/VoxelJointStrength.h:80` 的默认值是 **256**：

```cpp
inline double Ratio(const FMaterial& Material, int SpanCells, double ExtraLoadKg, int Iterations = 256)
```

探针（`Tools/Building/voxel_stress_probe.cpp`）不覆盖该默认值，
运行期求解器也是 256（`VoxelBuildRuntime.h:63` 的 `NextIterations=256`，
非收敛时才翻倍到 2048，`VoxelBuildWorldStructure.cpp:86-87`）。
所以文档里的「512」是**过时数字**。

这不影响跨度表的正确性（256 与 512 都已收敛时结果相同），但会让
「探针数字可复现」这条承诺在读者核对参数时对不上。**修法**：把文档改成 256，
或明确写「默认 256，非收敛时提升」。风险：无（纯文档）。

### C14 — `DamageQueue` 无上限、无去重（合并有语义风险）【中，需谨慎】

`Source/FPSGAME/Building/VoxelBuildRuntime.h:73`

```cpp
TArray<FVoxelDamageRequest> DamageQueue;
```

四个推入点（`VoxelBuildWorldDamage.cpp:33`、`:39`、`:45`、`:197`）都不去重、不设上限，
而排出速率是 4 条/帧（`:129`）。碎片侧可以在一次碰撞里推两条
（`VoxelCollapseFragment.cpp:113-114` 的 `QueueFragmentDamage` + `QueueCollapseImpact`），
虽然每件碎片有 0.12 s 的全局限流（`:105` `if(Now-LastImpactTime<.12)return;`），
所以单件最多约 8 次/秒 × 2 条 —— **放大倍数有限**，但总量随碎片数线性增长。

**这条我建议暂不动**，原因：请求里带 `Fragment` 弱引用与 `Replaces` 语义
（`VoxelBuildWorldDamage.cpp:74-75` 用 `Replaces` 判定"该碎片正被替换"），
按位置/能量合并会改变 `ApplyOverloadDamage` 与替换流程的先后关系，
有真实的行为风险。**优先做 P19 的预算修复**（让排出速率真正生效），
再观察队列长度峰值；只有在实测确认队列会堆积时才考虑合并。
报告第 5 节把「队列长度峰值」列入建议补的基线。

---

## 4. 优化路线图（建议顺序）

按「收益 / 风险」排序，每条都可独立交付。

### 第一批：零风险、当天可做完

| 项 | 位置 | 预期收益 |
| --- | --- | --- |
| P1 过载索引用 `TMap` | `VoxelSupportGraph.cpp:192` | 消除 O(n²)，大面积过载从秒级降到毫秒级 |
| P4+C1 `Lookup` 缩表 + 去 `static` | `VoxelJointStrength.h:86` | 初始化卡顿大幅下降；消除数据竞争 |
| P6 第二档 `Near` 用 `TInlineAllocator<32>` | `VoxelSupportGraph.h:36` | 瞄准/校验路径每帧省十几次分配 |
| P12 第 1 条 `Values` 复用缓冲 | `VoxelSurfaceMesher.cpp:113` | 每块重建省 2.1 MB 分配 |
| P13 第 1 条 `Emplace` 去残骸双拷贝 | `VoxelBuildWorldSave.cpp:36` | 存档每次省一份残骸格拷贝 |
| P23 图标：降 128²、占位 `FText` 提 `static`；LRU 触达移到重建时 | `VoxelBuildIcons.cpp:19,308,67` | 显存降 4 倍；每帧省每卡片一次 `FText` |
| P16 签名前置 / `Risk` 后移 / 渲染写入加守卫 | `VoxelBuildWidget.cpp:870-887,907-916` | 常态每帧省多次字符串与 UMG 写入 |
| P2 第 1 步 `InFlightKeys` 集合 | `VoxelBuildWorldMesh.cpp:55` | 去掉一个乘数 |
| P17 第 1、3 条 去重复 BFS + `Loaded.Reserve` | `World.cpp:151,154` | 加载期两次改一次；省 1 MB 重分配 |
| P11 `UpdateStructureWarning` 提前返回 | `VoxelBuildComponent.cpp:1263` | 常态每帧省一次字符串构造 |
| C3 `ValidatePlacement` 空检查 | `VoxelBuildComponent.cpp:1033` | 防御性 |
| C9 过载损伤置脏 | `VoxelBuildWorldStructure.cpp:53` | 崩溃不再丢损伤 |
| C12 缓存 `IConsoleVariable*` | `VoxelBuildDebug.h:14` | 每次诊断省一次字符串查找 |
| **P20 回收前提加「必须已启动」** | `VoxelCollapseFragment.h:36` | **修「碎块凭空消失」；一行改动** |
| **P19 预算检查提到循环顶部** | `VoxelBuildWorldDamage.cpp:129` | 消除单帧 pop 完整个队列 |
| P19 `RemoveAt(0)` 改头索引 | `VoxelBuildWorldDamage.cpp:59` | 去掉每帧 O(n) memmove |
| P23 `AnchorCache` 删除或真读 | `VoxelBuildWorld.h:156` | 去掉每格 0.6 MB 死容器 |
| P18 `TMap<FString,int64>` 缓存 + 退避 | `VoxelBuildWorldCollapse.cpp:130` | 背包满时每帧数千次 `FName::ToString` |
| P21 合并碎片三遍遍历 | `VoxelBuildWorld.cpp:418` | 每帧省一遍 O(碎片) + 物理查询 |
| C13 文档 512 → 256 | `voxel-build-workflow.md:225` | 文档与代码一致 |

验收：`run_voxel_stress_probe.ps1` 跨度表不变（wood 8.80/6.80，stone·marble 7.80/7.40）；
`audit_voxel_placement.py` 放置判定报告不变。

### 第二批：需要一次游戏内手感确认

| 项 | 位置 | 说明 |
| --- | --- | --- |
| P3 第 1 条 `Query()` 提到循环外 | `VoxelGrounding.cpp` + `World.cpp:243` | 无手感影响，优先做 |
| P3b `Surfaces` 内联容量提到 8 | `VoxelBuildGrounding.h:22` | 无手感影响，优先做 |
| P3 第 3 条 校验硬节流 / 按格比较 | `VoxelBuildComponent.cpp:1036` | 改手感，需用户拍板 |
| P5 增量维护构件占格 | `VoxelBuildWorldPrefab.cpp:30` | 放/拆大构件的卡顿 |
| P8 `MaterialSlots`/`VolumeOrigin` 缓存 | `VoxelBuildWorldMesh.cpp:60-86` | 网格生成吞吐 |
| P21 `MaxSolveNodes` 跨帧累计 + C10 状态行 | `VoxelBuildWorldStructure.cpp:237` | 修复死上限与错误读数 |
| P13 第 2 条 删掉中间 `UVoxelBuildSave` | `VoxelBuildWorldSave.cpp:19-38` | 省一次 UObject 与一次 map 拷贝 |
| P13 第 3 条 存档合并到 ≥2 s/空闲 | `VoxelBuildWorldSave.cpp:9` | 连续建造时的周期卡顿；崩溃窗口变大 |
| P22 `NodeEpoch`/`MeshGroups` 回收 | `VoxelBuildRuntime.h:59,68` | 会话内内存单调增长 |
| P23 RT 复用 + 硬上限淘汰 | `VoxelBuildIcons.cpp:308-313` | 显存与每图标 2 次捕获 |
| P16 浮窗池化 / 选择刷新只改两张卡 | `VoxelBuildWidget.cpp:252,765` | 悬停与点击的开销 |
| P20 加「回收了未激活碎片」日志 | `VoxelBuildWorldCollapse.cpp:126` | 验收该修复确实生效 |
| P22 Split 元数据拷贝 + 盒数传递 | `VoxelBuildGeometry.cpp:108,113-125` | 残骸准备的拷贝与重复哈希 |
| P21 世界 Actor 空载时停 tick | `VoxelBuildWorld.cpp:46` | 无建筑时仍跑五个 Tick |
| C6 存档失败原因分类 + `.pre-structure` 回退 | `VoxelBuildPersistence.cpp:54` | 可用性 |
| C8 单条坏记录跳过而非整份拒绝 | `World.cpp:113,119,121,128,131` | 材质增删后旧档可继续用 |
| C11 审计校验重读 + CRC | `VoxelBuildAudit.cpp:121,139-140,84-87` | 验收可信度 |

### 第三批：独立立项（数值核心/架构）

| 项 | 说明 |
| --- | --- |
| P7 第 1 步 求解器复用已有边表 | 等价改动、收益最大；必须逐项回归 |
| P7 第 2 步 CSR 稠密邻接 | 架构级重写；同时解决 P22 的 5.8 MB `Edges` |
| P17 第 4 条 反序列化直入世界容器 | 消除自由体积/损伤表的整表拷贝 |
| P13 第 4 条 增量存档 | 需要压缩/版本路径 |
| P12 第 2/3 条 chunk 尺寸与碰撞合并 | 需要新的性能基线 |
| C7 非 Windows 写盘路径 | 当前只跑 Win64，可延后 |
| 梁单元聚合（工作流第 2 节既有待办） | 节点数按段长降 5–10 倍，但改失效语义 |

---

## 5. 验收与度量（建议补的基线）

当前可用的观测入口（工作流 3.7）：

- `run_voxel_stress_probe.ps1` —— 离线连接强度与跨度（不需要引擎）
- `audit_voxel_placement.py` —— 无头复现放置判定
- `read_voxel_save.py` —— 解析存档实际内容
- 运行内：`BuildWorld->SolverStats()` / `SolverSummary()` 已把
  `求解 X ms · N 节点（局部 + M 边界）` 写进状态行

**缺口**：没有建造系统的每帧 CPU 归因。建议补：

1. **`stat` 组**：给 `UVoxelBuildComponent::TickComponent`、`AVoxelBuildWorld::Tick`
   的五个子步骤（`TickMeshes`/`TickStructure`/`TickFragments`/`TickDamage`/`TickPersistence`）
   各加 `TRACE_CPUPROFILER_EVENT_SCOPE`（Unreal Insights 可直接看），
   或 `SCOPE_CYCLE_COUNTER` + 自定义 stat group。
   特别注意 `TickPersistence` —— P13 的快照拷贝在游戏线程，属这条统计。
2. **放置校验计数**：统计每帧 `CanPlaceAt` 调用次数与射线数，
   验证 P3 的「每帧 200+ 条射线」估算。
3. **chunk/组件计数**：`Chunks.Num()` 与总三角面数，
   在 2 万格建筑上取基线（验证 P12 的 draw call 估算）。
4. **`MeshJobs` 峰值**：验证 P2 的 `|DirtyChunks|` 实际峰值。
5. **存档规模实测**：2 万格建筑的 `.sav` 实际字节数 + `MakeSnapshot` 耗时
   （验证 P13 的 450–500 KB 与 game-thread 拷贝成本）。
6. **容器容量断言**：`NodeEpoch`/`MeshGroups`/`DamageQueue` 的
   `Num()`/`Max()` 在长会话（多次拆除+重建）下的增长曲线（验证 P14）。
7. **图标显存**：缓存键数与渲染目标字节数，开抽屉满屏展开后是否超 32（验证 P15 软上限）。

有了这些，上述每项优化都能给出前后对比数字，而不是靠推断。

**回归入口（改任何数值/求解相关代码后必跑）**：

```powershell
powershell -NoProfile -File Tools/Building/run_voxel_stress_probe.ps1
```

判据：跨度表不变（wood 8.80 / 6.80 m，stone·marble 7.80 / 7.40 m，
工作流第 2 节），且逐格证书的自重/站人比值不变。
改放置判定相关代码后另跑 `Tools/Building/audit_voxel_placement.py`。

---

## 6. 明确没做的事

- 没有改动任何代码。
- 没有启动引擎、没有跑探针或游戏内测试
  （遵循项目规则：默认不主动检查/测试/验收）。
- 所有复杂度与耗时估算都是**从代码结构推导**的，不是实测；
  字节数为字段宽度推算（推算式已写出）。P1/P2/P9 的复杂度结论是确定的，
  具体毫秒数需按第 5 节补基线后验证。
- **未验证项**（无法从仓库确认的引擎行为）已在正文逐处标注，汇总：
  UE 5.8 下 `TArray`/`TMap`/`TSet` 的容器框架开销与是否走 bulk 序列化、
  `FNameAsStringProxyArchive` 的实际每格字节、
  旧 `USaveGame` 反射兜底路径（`VoxelPersistence.cpp:48`）是否仍可用、
  UMG `SetRenderOpacity`/`SetRenderTranslation` 在值未变时是否触发 Slate 无效化、
  `SetForceMipLevelsToBeResident(1.f)` 的参数语义与是否有界。
- 未审计（本轮范围外）：`ColdSteelDoor`/`ColdSteelWindow`/`ColdSteelFountain`/`BronzeTorch`
  等构件自身的逻辑、动画与材质开销；
  `VoxelCollapseFragment` 的 Chaos 刚体组与 `ColdSteelFountain` 的水面表现。
  本轮只覆盖到它们与建造系统的接口（`EnqueueFragment`/`TickFragments` 的准入预算、
  `PrefabActors` 与逻辑构件的挂载链）。
- P1/P2/P9 的复杂度结论是确定的，具体毫秒数需按第 5 节补基线后验证。
