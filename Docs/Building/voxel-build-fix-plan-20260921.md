# 体素建造系统修复计划（2026-09-21）

依据：[体素建造审计与性能优化建议](voxel-build-performance-audit-20260921.md)
（23 项性能问题 P1–P23、14 项正确性缺陷 C1–C14）。

本文只定**做什么、什么顺序、怎么验收、怎么回退**，不含具体补丁。
每条编号与审计报告一致，便于对照引用。

**用户规则提醒**：本项目默认不主动测试／验收。本文第 3 节的验证命令**写好待用**，
是否执行由你决定；我会照做，不会自行跑引擎。

---

## 1. 排期原则

### 1.1 一个硬约束决定批次划分

`Tools/Build/Build-Editor.ps1` 在检测到 FPSGAME 编辑器进程时会**直接报错退出**
（脚本第 14–20 行 `throw 'Save your work and close the FPSGAME editor before building.'`），
即任何需要改**头文件**的改动都必须：**关编辑器 → 全量 `Build.bat` → 重启编辑器**。

而工作流第 6 节明确：**带资产的 USTRUCT 不能用 Live Coding 热补丁**
（热补丁后新 struct tag 与已保存资产不匹配，字段会整体读成 None，后续脚本会把空值写进资产）。

所以批次**按「编译单位」而不是按严重度**划分：

| 批次 | 内容 | 编译代价 | 编辑器 |
| --- | --- | --- | --- |
| **批次 0** | 只改 `.cpp` 函数体 | Live Coding 可热补丁 | 可保持打开 |
| **批次 1** | 改动**头文件**（成员/内联/结构） | **必须关编辑器全量编译** | 需重启一次 |
| **批次 2** | 需要资产或数值复核（探针） | 同批次 1 或 Live Coding | 视情况 |
| **批次 3** | 需用户拍板手感 / 独立立项 | — | — |

**先把能热补丁的批次 0 做完再关编辑器**，这样编辑器只需要关一次。

### 1.2 严重度顺序（批次内部按此排序）

```
P20 碎块消失   >  C6 存档故障使建造不可用  >  C9 损伤丢失
>  P19 单帧耗尽队列  >  P1 O(n²)  >  P2/P3 每帧开销  >  P4/C1 初始化+竞争
>  P18 每帧重试  >  P5/P13/P14 大对象  >  其余
```

### 1.3 每条改动的风险标签

- **[零风险]** 纯等价改写、纯删除、或只在诊断路径上
- **[低]** 行为不变或只改节流/缓存，可能影响性能曲线
- **[中]** 改手感、改存档节奏、改资源占用，**需要你确认或实测**
- **[高]** 触及求解数值语义或存档格式

---

## 2. 批次 0：只改 `.cpp` 函数体（Live Coding 热补丁）

改完可用 `LiveCoding.CompileSync` 生效，编辑器保持打开。

| 序 | 项 | 文件 | 改什么 | 风险 |
| --- | --- | --- | --- | --- |
| 0.1 | **P1** | `VoxelSupportGraph.cpp:192` | `Result.Overload` 的 `FindByPredicate` 换成 `TMap<FVoxelBuildKey,int32>` 索引（函数内局部） | [零风险] |
| 0.2 | **P19** | `VoxelBuildWorldDamage.cpp:57-129` | 预算检查提到循环顶部；`RemoveAt(0)` 改文件级 `DamageRead` 游标（`:131` 之后补一次压缩）；`Replacing` 判定改反查 | [低] |
| 0.3 | **P18** | `VoxelBuildWorldCollapse.cpp:121-133` | 文件级 `TMap<FGuid,TMap<FString,int64>>` 缓存块名 + 1 s 重试退避 | [低] |
| 0.4 | **P3 第 1 条** | `VoxelBuildGrounding.cpp` + `VoxelBuildWorld.cpp:243` | `FCollisionQueryParams` 在格循环外构造一次，沿参数传入 `CanPlaceAt`/`CanCommit` | [零风险] |
| 0.5 | **P3b** | `VoxelBuildGrounding.h:22` | `TInlineAllocator<5>` → `<8>`（模板参数，**不必**关编辑器） | [零风险] |
| 0.6 | **P2 第 1 步** | `VoxelBuildWorldMesh.cpp:50-58` | 加文件级 `TSet<FVoxelBuildKey> InFlightKeys` 同步 `MeshJobs`，替掉 `ContainsByPredicate` | [零风险] |
| 0.7 | **P8** | `VoxelBuildWorldMesh.cpp:60-86` | `VolumeOrigin`/`MaterialSlots` 提到循环外；大 volume 稀疏遍历分支与稀疏分支合并 | [低] |
| 0.8 | **P12 第 1 条** | `VoxelSurfaceMesher.cpp:113` | `Values` 改**线程局部**可复用缓冲（`static thread_local TArray<float>`，注意网格作业在线程池上跑，不能用跨线程共享缓冲） | [低] |
| 0.9 | **P17 第 1、3 条** | `VoxelBuildWorld.cpp:151,154` | 断键应用移到 `RefreshSupportGraph` 之前（去重复 BFS）；`Loaded.Reserve` | [零风险] |
| 0.10 | **P16** | `VoxelBuildWidget.cpp:870-916` | `ShowState` 签名前置；`Risk` 块后移；渲染写入加「值变才算」守卫；选择刷新只改前后两张卡 | [零风险] |
| 0.11 | **P11** | `VoxelBuildComponent.cpp:1263` | `WeakestJointSummary()` 构造移到阈值判定之后 | [零风险] |
| 0.12 | **P21** | `VoxelBuildWorld.cpp:418` + `VoxelBuildWorldCollapse.cpp:113-145` | 合并碎片三遍遍历；`Sleeping` 跳过 `SampleVelocity` | [低] |
| 0.13 | **P22** | `VoxelBuildGeometry.cpp:108,113-125` | `Part` 只拷元数据；盒数沿细分传递不重算 | [低] |
| 0.14 | **C3** | `VoxelBuildComponent.cpp:1033` | `ValidatePlacement` 加 `if(!BuildWorld)return;` | [零风险] |
| 0.15 | **C9** | `VoxelBuildWorldStructure.cpp:53` | 损伤累加时 `MarkSaveDirty()` | [低] |
| 0.16 | **C10** | `VoxelBuildWorld.cpp:497` | 「全量」文案按 `Gather.Boundary` 是否为空判定 | [零风险] |
| 0.17 | **C12** | `VoxelBuildDebug.h:14` | 缓存 `IConsoleVariable*` | [零风险] |
| 0.18 | **C11** | `VoxelBuildAudit.cpp:84,87,121,139-140` | 存档校验重读并验 magic/CRC/mtime；`items.json` 改存在性判定；不丢弃 `CheckPlacementRoundTrip()` 返回值 | [零风险] |

**批次 0 完成判据**：Live Coding 编译通过，日志无结构性报错，
`logs` 里 `VOXEL_*` 未出现新增告警。（不做功能测试，除你要求。）

---

## 3. 批次 1：改头文件（需关编辑器全量编译，只关一次）

⚠️ 一次改完，避免多次重启编辑器。
⚠️ 改动含 `FVoxelBuildPrefabInstance` 之外的结构体时，遵守工作流第 6 节第 3 条：
**关编辑器 → 全量 `Build.bat FPSGAMEEditor Win64 Development` → 重启后再动资产**。

| 序 | 项 | 文件 | 改什么 | 风险 |
| --- | --- | --- | --- | --- |
| 1.1 | **P4 + C1** | `VoxelJointStrength.h:86` | `static long long Lookup[64³]`（2 MB，每次调用全清）→ 按 `Room()` 实际范围缩成 `int32[6*28*7]` 并改为**函数局部**（消除 `static` 数据竞争） | [低] 需探针复核 |
| 1.2 | **P6** | `VoxelSupportGraph.h:36` | `Near()` 返回 `TArray<FVoxelBuildKey,TInlineAllocator<32>>`（类型尺寸不变）；**备选**：签名不动，加 `.cpp` 内部实现 + 出参版本替掉调用点 | [低] |
| 1.3 | **P20** | `VoxelCollapseFragment.h:34-39` | `AccrueRestSeconds` 加 `if(!bStarted\|\|IsMoving()){RestSeconds=0;return false;}` | [低] **功能修复** |
| 1.4 | **P23** | `VoxelBuildWorld.h:156` | 删除 `AnchorCache`（已确认零读取）及其三处写入 | [零风险] |
| 1.5 | **P5** | `VoxelBuildWorld.h:152-155` + `VoxelBuildWorldPrefab.cpp:30-40` | `RefreshPrefabOccupancy` 改增量；加 `TMap<FIntVector,int32> PrefabByAnchor` 替 `FindByPredicate` | [中] |
| 1.6 | **P21 停 tick** | `VoxelBuildWorld.h` + `.cpp:46` | 空载（无建筑/碎片/脏集）时 `SetActorTickEnabled(false)`，有编辑时开启 | [低] |
| 1.7 | **C6** | `VoxelBuildPersistence.h:21` | `Load` 加失败原因出参（`Load(const FString& Slot,FString& OutError)`），区分「文件不存在／CRC 失败／解析失败／版本过高／世界键不匹配」；CRC/解析失败自动尝试 `.pre-structure` | [低] |
| 1.8 | **C7** | `VoxelBuildPersistence.cpp:83-85` | 补非 Windows 写盘路径 + 失败时清 `.pending` | [零风险] 当前只跑 Win64 |
| 1.9 | **C8** | `VoxelBuildWorld.cpp:113,119,121,128,131` | 单条坏记录跳过并 warning，不整份拒绝 | [中] |
| 1.10 | **C13** | `Docs/Building/voxel-build-workflow.md:225` | 「512 次迭代」→ 256（并注明非收敛时翻倍） | [零风险] 纯文档 |
| 1.11 | **C14** | — | **不改**。见第 5 节决策 4 | — |

### 批次 1 验收（改数值的必须跑）

```powershell
# 关编辑器后：
powershell -NoProfile -File Tools/Build/Build-Editor.ps1
# 按需（改过 JointStrength 的必须）：
powershell -NoProfile -File Tools/Building/run_voxel_stress_probe.ps1
```

**探针硬判据**（工作流第 2 节，改前改后必须逐项一致）：

| 材质 | 自重 | 跨中站 100 kg |
| --- | ---: | ---: |
| wood | 8.80 m | 6.80 m |
| stone / marble | 7.80 m | 7.40 m |

若 P4 缩表后这两个数字变了 → **说明缩表写错了**（`Room()` 的坐标范围算错），回退重做。

```powershell
# 放置判定回归（改了 P3/P3b 之后）：
python Tools/Building/audit_voxel_placement.py
```

---

## 4. 批次 2：需要实测或资产配合

| 序 | 项 | 说明 | 前置决策 |
| --- | --- | --- | --- |
| 2.1 | **P13 第 1、2 条** | `Emplace` 去残骸双拷贝；删掉中间 `UVoxelBuildSave`，直接填 `FVoxelDiskSnapshot`（`MakeSnapshot` 改返回 `FVoxelDiskSnapshot`，`Take` 成为历史遗留） | 无 |
| 2.2 | **P13 第 3 条** | 存档合并到 ≥2 s 或空闲时落盘 | **决策 2** |
| 2.3 | **P14** | `NodeEpoch`/`MeshGroups`/`LoadRatios` 回收；先加容量日志观察峰值 | 无 |
| 2.4 | **P23 图标** | 128² 渲染 + RT 复用 + 硬上限淘汰 + LRU 触达移到重建时 | **决策 3** |
| 2.5 | **P17 第 4 条** | 反序列化直入世界容器（去掉整表拷贝） | 无 |
| 2.6 | **C4** | 2 万格存档实测大小与 `MakeSnapshot` 耗时，再决定是否换二进制名称表 | 无 |
| 2.7 | **P12 第 2、3 条** | chunk 尺寸 / 碰撞合并 —— 需要新基线 | 独立立项 |

---

## 5. 待你拍板的 4 个决策

这些会改手感或资源占用，我不替你决定。

| # | 决策 | 选项 | 我的建议 |
| --- | --- | --- | --- |
| **1** | **P3 第 3 条**：放置校验的节流 | (a) 每帧照旧（手感最好，成本最高）<br>(b) 硬节流 50 ms<br>(c) `CheckedOrigin` 改比较**取整后的格**（准星微动不重算，跨格才重算） | **(c)** —— 只消除"同格内抖动"的重复计算，跨格时仍然即时更新，对手感影响最小 |
| **2** | **P13 第 3 条**：存档节奏 | (a) 保持 0.75 s<br>(b) 合并到 ≥2 s<br>(c) 只在编辑停止后 N 秒落一次 | **(b)** —— 崩溃丢失窗口从 0.75 s 变 2 s，换来连续建造时少 2/3 的快照拷贝。若你更在意崩溃安全就选 (a)，那一项先不做 |
| **3** | **P23 图标**：分辨率与上限 | (a) 256² + 软上限（现状）<br>(b) 128² + 硬上限淘汰可见键<br>(c) 只加硬上限、不动分辨率 | **(b)** —— 卡片槽只有 104 px，256² 是 4 倍冗余；但缩略图变糊是可见变化，需你确认 |
| **4** | **C14**：伤害请求合并 | (a) 不做，只修 P19 预算<br>(b) 按位置/能量合并 | **(a)** —— 合并会改变 `Replaces` 替换流程的先后语义，风险高于收益。先修 P19 再看队列峰值 |

---

## 6. 执行顺序与检查点

> **2026-09-21 执行记录（检查点 A 已通过）**
>
> 批次 0 已完成 11 项并**编译验证通过**（两次全量 `Build-Editor.ps1` → `Result: Succeeded`，
> 日志 `Saved/BuildEditor/build-20260921-211023.log` 与随后一次增量构建，
> 仅 `VoxelCollapseFragment.cpp:17` 的既有 `C4305` 截断告警，与本计划无关）：
>
> | 项 | 落点 |
> | --- | --- |
> | P1 | `VoxelSupportGraph.cpp` 过载改 `TMap` 索引 |
> | P19 | `VoxelBuildWorldDamage.cpp` 预算提到循环顶部 + 读游标 `DamageRead` + 帧末压缩 |
> | P18 | `VoxelBuildWorldCollapse.cpp` 块名缓存 + 1 s 退避 + 去每帧 `Snapshot()` 整份拷贝 |
> | P3 | `VoxelBuildGrounding.{h,cpp}`、`VoxelBuildWorld.{h,cpp}` 查询参数提到格循环外 |
> | P3b | `VoxelBuildGrounding.h` `TInlineAllocator<5>` → `<8>` |
> | P2（第一步） | `VoxelBuildWorldMesh.cpp` 在飞键集合 + 每帧排序一次 |
> | P17（第 1 条） | `VoxelBuildWorld.cpp` 断键移到 `RefreshSupportGraph` 之前，去重复 BFS |
> | P16（部分） | `VoxelBuildWidget.cpp` `ShowState` 签名前置、`Risk` 块改为仅在变化时执行 |
> | P11 | `VoxelBuildComponent.cpp` 预警摘要移到阈值判定之后 |
> | P21 | `VoxelBuildWorldCollapse.cpp` 醒着统计/KillZ 与回收扫描合并为一趟 |
> | C3 / C9 / C10 / C12 | 空检查、过载损伤置脏、「全量·已达上限」文案、CVar 指针缓存 |
>
> **仍未做**：P8（经分析降级，见下）；批次 1 只剩 P5（增量维护构件占格）；
> 批次 2 全部（需实测/资产配合）。
>
> **批次 1 完成面**：10 项里 9 项已写入 —— P4+C1、P6、P20、P23、C6、C7、C8、C13（+ P21 已在批次 0 编译）。
> 仅 P5 未做，理由见下。
>
> **批次 1 已写入工作区、语法编译已过、待正式链接**（备份
> `Saved/BuildingFixBackup/building-fixes-all.patch`）：
>
> | 项 | 落点 | 状态 |
> | --- | --- | --- |
> | **P20** | `VoxelCollapseFragment.h` | `AccrueRestSeconds` 加 `!bStarted` 前提（修"碎块凭空消失"） |
> | **P4 + C1** | `VoxelJointStrength.h` | 2 MB `static` 全清 → 固定容量开放寻址哈希表 + 代计数（O(1) 清空）；加 `std::mutex` 消除数据竞争 |
> | **P23** | `VoxelBuildWorld.h` / `.cpp` / `VoxelBuildWorldPrefab.cpp` | 删除只写不读的 `AnchorCache` 及其 4 处写入（2 万格省约 0.6 MB） |
> | **C13** | `voxel-build-workflow.md` | 迭代数 512 → 256（纯文档，已改） |
> | **C7** | `VoxelBuildPersistence.cpp` | 存档失败路径清 `.pending`（4 条分支） |
> | **C6** | `VoxelBuildPersistence.{h,cpp}` / `VoxelBuildWorld.cpp` | 加载失败原因分类（`ELoadResult`）+ 日志 + `.pre-structure` 回退 + `LoadFromFile` 路径入口 + `Take` 空指针加固 |
> | **C8** | `VoxelBuildWorld.cpp` | 单条坏记录改为**跳过并计数**（不再整份拒绝）；汇总一行去重日志 + 状态行提示 |
> | **P6** | `VoxelSupportGraph.{h,cpp}` / `VoxelBuildWorld.cpp` | 新增 `NearInto`（出参复用缓冲），`ResolveHit` 改用它消除每帧瞄准路径的堆分配 |
> | **P12 第 1 条** | `VoxelSurfaceMesher.cpp` | `Values` 改 `thread_local` 可复用缓冲 |
> | **P22** | `VoxelBuildGeometry.cpp` | `Split` 的 `Part`/`Half` 去整份拷贝 |
> | **P17 第 3 条** | `VoxelBuildWorld.cpp` | 已随批次 0 编译 |
> | **P13 第 3 条（决策 2）** | `VoxelBuildWorldSave.cpp` | 存档最小间隔 2 s：截止时间取 `max(Now+0.75, 上次存档开始+2s)`，保留 `if(!bSaveDirty)` 不重算的保护 |
>
> **P13 第 3 条的两处自我纠错（都靠调度模拟发现，不是靠肉眼）**：
> 1. 第一版写成每次置脏都重算 `max(Now+0.75, …)` —— 因为 `Now` 每次都在涨，
>    截止时间永远领先于 `Now`，`TickPersistence` 的 `Now >= SaveAt` **永不成立，存档彻底停摆**。
>    这是把原实现的 `if(!bSaveDirty)` 保护去掉造成的。
> 2. 修正后按"连续编辑"模拟验证（60 s 窗口）：
>    每 0.25 s 一次编辑 → 存档 **30 次/60 s**（原实现 60 次），间隔 min=2.0 / max=2.0 s，
>    最坏崩溃窗口 1.75–2.0 s，**有明确上界**（原实现是 0.75 s 但每秒两次快照）。
>
> **P5 未做（有意）**：`RefreshPrefabOccupancy` 改增量维护，涉及 `PrefabCells` +
> `PrefabCellOwner` + 新增 `PrefabByAnchor` 三张表的增删一致性，而这三张表是**放置判定的唯一权威**
> （`IsPrefabCell` 被 `CanPlaceInVolume`/`CanCommit`/`ScenePlacementAllowed` 依赖）。
> 语法编译只能证明"能编过"，**证明不了增删一致**；一旦不一致，放置会在运行时静默漏判或误判，
> 而当前拿不到运行时验证窗口。按计划第 4 节它本来就归在"需要一次游戏内手感确认"的第二批，
> 因此留到有运行窗口时做（届时建议先加一条 `check()` 比对增量结果与全量结果）。
>
> **C6 实现要点**：`Load` 拆成「槽位读取」与「完整路径读取（`LoadFromFile`）」两个入口，
> 共用匿名命名空间的 `LoadBytes` 解析体。原因是 `.pre-structure` 备份不在槽位命名规则内
> —— 我第一版把备份路径直接喂给 `Load`，会被再拼一次 `.sav`（`X.sav.pre-structure.sav`），
> 属于自己写出来又自己发现的 bug，已改为 `LoadFromFile`。
> `C6` 的失败路径仍然保持「保留原档、不让建造世界初始化」，与改动前一致，只是原因变准确了。
>
> ## ✅ 无需编辑器的 UE 侧语法编译验证（2026-09-21 本轮新增手段）
>
> `Build-Editor.ps1` 因编辑器占用无法运行，但 **UBT 留下的响应文件 + 共享 PCH 足以在编辑器开启时
> 做一次真正的 UE 语法编译**。做法与结论：
>
> - 每个 `*.cpp` 在 `Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/` 下有
>   `<file>.cpp.obj.rsp`，内含该文件被 UBT 编译时的**全部** include/define/PCH 参数；
> - 关键点：**工作目录必须是 `…/UE_5.8/Engine/Source`**。共享 rsp 里的 include 路径是相对路径
>   （如 `/I "Runtime/Core/Public"`、`/I "../Intermediate/…"`），只有以 `Engine/Source` 为基准才解析得到，
>   否则会误报 `fatal error C1083: 无法打开包括文件 "CoreMinimal.h"`（我在这里试错了两次）。
> - 命令：`cd /d <Engine>\Source && cl /nologo /Zs @<file>.cpp.obj.rsp`
>   （`/Zs` = 只做语法检查，不生成目标文件）。
> - 结果：**19 个 Translation Unit 全部零 error 通过**，涵盖本批次全部改动
>   （`VoxelSupportGraph` / `VoxelBuildWorld` / `VoxelBuildWorldPrefab` / `VoxelBuildPersistence` /
>   `VoxelSurfaceMesher` / `VoxelBuildGeometry` / `VoxelBuildComponent` / `VoxelBuildWorldDamage` /
>   `VoxelBuildAudit` / `VoxelBuildWorldCollapse` / `VoxelBuildWorldMesh` / `VoxelBuildWorldStructure` /
>   `VoxelBuildWorldSave` / `VoxelBuildWidget` / `VoxelCollapseFragment` / `VoxelBuildGrounding` /
>   `VoxelBuildPrefabActor` / `VoxelBuildIcons` / `VoxelBuildPalette`）。
>   原始输出：`Saved/BuildingFixBackup/syntax-check-raw.log`。
>   唯一告警是既有的 `VoxelCollapseFragment.cpp:17` C4305（double→float 截断），与本批次无关。
>
> **本手段实际抓到一个真错误**：C6 里我写了
> `if(LoadedData)UE_LOG(...); else UE_LOG(...);` —— `UE_LOG` 展开成含内层 `if` 的多语句宏，
> 触发 `error C2181: 没有匹配 if 的非法 else`。已改为给两个分支都加花括号。
> 也就是说这一条如果只靠肉眼审查就会漏到正式编译。
>
> **仍未取得**（必须编辑器关闭）：① 正式 `Build-Editor.ps1` 的可链接产物（`/Zs` 只验语法，
> 不做模板实例化链接期检查，也不更新 DLL）；② 放置审计 `audit_voxel_placement.py`（需项目互斥体）。
>
> **C7 复核更正（重要）**：计划里 C7 原本建议"改用 `IFileManager::Move` 做跨平台写盘"。
> 核对引擎源码后确认**那条建议是错的**：`FFileManagerGeneric::Move`
> （`FileManagerGeneric.cpp:303`）在 `Replace=true` 时**先删目标再改名**，
> 一旦改名失败就会**连旧存档一起丢掉**——比现在的"非 Windows 直接失败"更糟。
> 因此 C7 实际只做了**失败路径清 `.pending`**（含初次写入、目录创建、pre-structure 备份、
> 换名失败四条分支），写盘主路径**保持 Windows-only 不变**；
> 真正的跨平台原子替换需要「旧档改名 .bak → 移入新档 → 失败回滚」，
> 会改动存档目录布局与恢复语义，登记为独立立项（项目构建脚本当前只出 Win64，无其它目标平台）。
>
> **P23 的回归面已单独确认**：全目录 grep 只有写入/删除、零读取；放置判定走
> `CanPlaceAt` 里临时构造的 `Draft` 图，锚定由 `IsGroundAnchor`/`PrefabSupportAt` 现算，
> `Anchor` 局部变量仍在用（喂 `SupportGraph->Add`），不是死变量。
>
> **P4 已通过探针硬判据（重要）**：用 HEAD 版本与修改后版本各编一个离线探针，
> 输出**逐项完全相同** —— wood 8.80/6.80 m、stone·marble 7.80/7.40 m，
> 且 2.00 m 行 worst=0.050/0.231（wood）与 0.062/0.115（stone·marble）。
> 数值等价性已确认，只差 UE 侧"能编译"的确认。
>
> **同时实测更正了两处此前的推断**（已写入审计报告开头）：
> 1. 面板跨度构建实测 **旧 44.64 ms → 新 36.08 ms**，即那 2 MB 清零只占 **约 8.5 ms（19%）**，
>    不是全部；剩余约 36 ms 是**求解器本身**（每格一次 256 迭代 CGNR）。
>    收益推断原先偏大，且"一次性 0.2–0.5 s"不成立——实测约 36 ms。
>    要再降一个数量级应做**结果缓存**或移到后台线程。
> 2. 文档里 wood 2.00 m 的 0.09 / 0.23 是**过时值**，实际 0.050 / 0.231，已更正。
>
> **探针脚本已补 `/utf-8`**：`run_voxel_stress_probe.ps1` 的 `cl` 原先没带该标志，
> MSVC 按代码页 936 解码 UTF-8 头文件，会把中文注释旁的代码打乱并报假错。
>
> **无法在编辑器开启时跑的验证**：`UnrealEditor-Cmd`（放置审计 `audit_voxel_placement.py`）
> 需要项目互斥体，编辑器占用时会在引擎初始化阶段直接退出、连日志都不写
> （与工作流第 6 节第 5 条描述一致）。因此放置判定回归必须在编辑器关闭时做。
>
> **待编译项的 API 已逐个对 UE 5.8 引擎头核对**（减少"编不过"的风险；这不是编译验证）：
>
> | 用到的 API | 引擎头 | 结论 |
> | --- | --- | --- |
> | `TArray::SetNum(SizeType, EAllowShrinking)` | `Containers/Array.h:2531` | 存在 |
> | `TArray::Append(const ElementType*, SizeType)` | `Containers/Array.h:2747` | 存在 |
> | `TArray::GetData()` / `Reserve(SizeType)` | `Array.h:1271,3268` | 存在 |
> | `FCollisionQueryParams()` 默认构造 + 拷贝构造 | `CollisionQueryParams.h:210` | 存在（P3 的三元表达式合法） |
> | `IConsoleVariable::GetInt() const` | `HAL/IConsoleManager.h:653` | 存在（C12 缓存合法） |
> | `EAllowShrinking` 枚举本身 | 既有代码 `VoxelBuildWorldDamage.cpp:158` 的 `RemoveAt(0,Drop,EAllowShrinking::No)` 已在用 | 该版本确有此枚举 |
>
> 另外 P4 的 `VoxelJointStrength.h` 已由离线探针实际编译并运行通过（见上）。
>
> **P8 经分析后降级（未做）**：其内层唯一硬成本是每格一次 `MaterialSlots.Find`
> （`TMap<FName,int32>` 查找）。实际盘点：`Data->Num()` 阈值已排除大体积的 4913 次 halo 扫描
> （只剩 ≤5832 格的稀疏分支），按"每帧 1 个块 × ≤4096 格"计约每帧一万次哈希查找，
> 相对 `SetMesh`+`SetSimpleCollisionShapes`（本文件第 47 行自己限了 1.5 ms 预算）是噪声级。
> 动它要重排 lambda 与 `Data` 遍历，收益不成比例，故**建议不做**；
> 若后续 `TickMeshes` 出现实测热点再回来处理。

> **过程中遇到的环境约束**：本仓库有另一个会话同时在改武器/天气文件，并在
> 21:10:55 重新打开了编辑器，导致一次构建被 `Build-Editor.ps1` 拒绝。
> 改动因此分成两次编译验证；Building 目录与该会话的文件无重叠。
> WIP 差异备份在 `Saved/BuildingFixBackup/batch0-wip.patch`。

```
检查点 A ── 批次 0（18 项，Live Coding）
             │  编译通过 + 无新告警
             ▼
检查点 B ── 关编辑器，批次 1 一次性改完（1.1–1.10）
             │  全量 Build.bat 成功
             │  跑探针 → 跨度表逐项一致（硬判据）
             │  跑 audit_voxel_placement.py → 放置报告一致
             ▼
检查点 C ── 重启编辑器，你在游戏内验：倒塌碎块不再消失（P20）
             │  + 大建筑连续建造的帧率（P2/P3/P18/P19）
             ▼
检查点 D ── 批次 2（按决策 2、3 的结果）
```

### 检查点 B 已脚本化：一条命令

```powershell
powershell -NoProfile -File Tools/Building/run-checkpoint-b.ps1
```

`Tools/Building/run-checkpoint-b.ps1` 按顺序做三件事，且**先做前置检查**——

0. 若 FPSGAME 编辑器仍在运行，**立即中止**（不结束任何进程，打印 PID 让人手动关）；
1. 全量编译（`Build-Editor.ps1`），失败即中止；
2. 跑探针，并**用硬判据断言跨度表**：wood 8.80/6.80、stone·marble 7.80/7.40
   （该正则已用真实探针输出验证通过），不一致就中止并提示
   「文档曾长期误写 wood 0.09/0.23，已更正为 0.050/0.231」；
3. 跑放置审计 `audit_voxel_placement.py`，汇总每层 placed 数与 INCOMPLETE 标记
   （并提示：判断是否回归必须与 `Docs/Building/voxel-build-audit-20260916.md` 的基线比对）。

输出落在 `Saved/BuildingFixBackup/`：`probe-checkpoint-b.txt`、`placement-audit-checkpoint-b.log`。

> 注意：该脚本带 **UTF-8 BOM**。Windows PowerShell 5.1 在无 BOM 时按系统代码页（本机 936）
> 解析 `.ps1`，中文会变成乱码并直接导致语法错误 —— 我第一版就踩了这个，加了 BOM 才解析通过。


### 每个检查点的回退点

- 用 `git stash` / 精确暂存（工作流要求**并行修改精确暂存，保留未提交工作**）。
- 批次 1 因为要关编辑器，建议**先把批次 0 提交或暂存**，避免一次回退牵连。
- P4 缩表若探针数字变了 → 只回退 `VoxelJointStrength.h` 一个文件即可，
  其余批次 1 改动不受影响（唯一被探针覆盖的就是这一个文件）。

### ⚠ 检查点 B 被并行会话的文件阻断（2026-09-21 21:53–21:56 实测）

编辑器在 21:53 关闭、DLL 解锁后，检查点 B **连试两次均在全量编译阶段失败，且失败文件与本计划无关**：

| 次 | 日志 | 失败点 |
| --- | --- | --- |
| 1 | `build-20260921-215348.log` | `Source/FPSGAME/Weapons/RuneGoldMaterialCommandlet.cpp(9): fatal error C1083: 无法打开包括文件 "UObject/SaveLoose.h"` |
| 2 | `build-20260921-215533.log` | 同一文件 `(10): fatal error C1083: 无法打开包括文件 "EditorAssetLibrary.h"` |

事实核对（都实测过）：

- 该文件是**并行会话新加的未跟踪文件**（`git status` 显示 `??`），本计划与 `Building/` 目录
  **完全没有引用它**（全目录搜 `SaveLoose`、`RuneGoldMaterialCommandlet` 只命中它自己）。
- 它**正在被实时编辑**：第 1 次失败时的 `SaveLoose.h` 在两次构建之间已被改成 `SavePackage.h`
  （mtime 21:55:29，我在 21:55:39 复查时内容又变了）。
- `SaveLoose.h` **在 UE 5.8 全引擎源码中不存在**（`Engine/Source` 递归搜索无结果）。
- `EditorAssetLibrary.h` 存在，但在
  `Engine/Plugins/Editor/EditorScriptingUtilities/Source/EditorScriptingUtilities/Public/`，
  而 `FPSGAME.Build.cs` 的 `PrivateDependencyModuleNames` **没有** `EditorScriptingUtilities`
  （只有 UnrealEd、NiagaraEditor、ClothingSystem* 等）。所以它接下来大概率还会在这里失败。
- UBT 用 `git status` 决定"工作集"，未跟踪的新文件会被排进构建，因此它的任何语法错误都会
  **让整个模块编译失败**，与本计划的改动无关。

处置：**按用户指示不触碰对方的任何文件**（项目规则禁止干扰并行会话）。检查点 B 继续挂起，
解除条件是那个文件停止变动且能编过。

**21:58 复核（第三次尝试，日志 `build-20260921-215822.log`）**：该文件自 21:56:12 起已稳定，
但**仍编不过**，且错误性质已不只是缺 include。共 **19 条 error，全部落在该文件**，
`Source/FPSGAME/Building/` 下 **0 条**（已逐行核对）。暴露出的真实问题包括：

| 错误码 | 内容 | 文件位置 |
| --- | --- | --- |
| C2672/C3536 | `LoadObject<UMaterial>(nullptr,*AssetPath,&Error)` 在 UE 5.8 无匹配重载（第三参应为 `FStringView`，传 `FString*` 失败） | `RuneGoldMaterialCommandlet.cpp:20` |
| C2065 | `UMaterialExpressionScalarParameter` 未声明（缺 `Materials/MaterialExpressionScalarParameter.h`） | `:34` |
| C2653 | `FEditorAssetLibrary` 不是类或命名空间名称（`EditorAssetLibrary.h` 来自 `EditorScriptingUtilities` 插件，未在 `FPSGAME.Build.cs` 声明依赖） | — |
| C2661 | `FString::Replace` 没有接受 1 个参数的重载 | — |
| C2110 | `+` 不能添加两个指针 | — |
| C2143/C3531 | 由上述连带造成的语法错误 | `:24,33` |

这些都是**对方文件的 API 用法问题**，与本计划无关，也不该由本计划代改。

**为此给 `run-checkpoint-b.ps1` 加了编译失败归因**：失败时自动从最新日志里抽出
「错误总数 + 涉及文件」，并明确判断**是否有错误落在 `Building/` 下** ——
若一条都没有，就提示"很可能是并行会话正在编辑的文件让整个模块编译失败"，
避免每次人工翻日志、也避免把别人的错误误判成本计划的回归。

---

## 6.5 ✅ 检查点 B 已执行（2026-09-21 22:22）

对方会话把 `RuneGoldMaterialCommandlet.cpp` 修好（6049 bytes，22:17:14）后，检查点 B 跑通：

| 步骤 | 结果 | 证据 |
| --- | --- | --- |
| 0 前置检查 | ✅ 编辑器未运行 | 脚本输出 `[0/3] …通过` |
| 1 全量编译 | ✅ **`Result: Succeeded`** | `Saved/BuildEditor/` 最新日志（22:21 前后） |
| 2 探针 + 跨度表硬判据 | ✅ **逐项一致** | `Saved/BuildingFixBackup/probe-checkpoint-b.txt`：wood self=8.80/+100kg=6.80；stone 与 marble 均 7.80/7.40 |
| 3 放置判定无头审计 | ⚠ **未能运行** | 见下 |

**批次 1 的 9 项代码从此有了正式可链接产物**（不再只有语法验证）。

### 步骤 3 的失败原因（是我脚本的 bug，已修）

第一次尝试时审计日志 **0 字节、exit=1**，看似"没有输出"。用 `-stdout` + 自定义 `-log` 抓取后定位到真因：

```
LogInit: Display: Project file not found: FPSGAME.uproject
LogProjectManager: Error: Failed to open descriptor file FPSGAME.uproject
LogInit: Warning: Could not find a valid project file, the engine will exit now.
```

`& exe 'FPSGAME.uproject'` 传的是**相对路径**，而新进程的工作目录不保证是本工程目录，于是引擎在初始化阶段就退出。改为传绝对路径（工程文件与脚本都用 `Join-Path $project` / `$PSScriptRoot`）后：

- 命令返回 **exit=0**、stdout **63520 bytes**，脚本确实被执行了
  （日志里出现 `Running Python script: …audit_voxel_placement.py`）。

### 步骤 3 仍存在的限制（未确证，不当作回归）

改为绝对路径后脚本**能跑了**，但**仍未产出 `AUDIT layer …` 行**：

- 命令自报 `Success - 0 error(s), 7 warning(s)`，耗时仅 **0.47 s**；
- 日志停在脚本第 24 行（`EditorLevelLibrary.get_editor_world()` 的弃用警告）之后，
  没有 traceback、没有 Python 异常，也没有 map/floor/spawn/initialize 的任何 print；
- 引擎主日志（`%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Logs\Unreal.log`）里同样搜不到 `AUDIT`。

即：**该脚本在本环境下以 `-run=pythonscript -nullrhi -unattended` headless 方式运行时，
无法产出其 AUDIT 报告**。我**没有**在仓库里找到这个脚本曾经成功运行过的产物可作对照，
所以这不像是本次改动引入的回归，但我**无法证实** —— 需要一次交互式/编辑器内的运行来判断。
（脚本自身已提示 `EditorLevelLibrary` 属已弃用的 Editor Scripting Utilities。）

因此检查点 B 的状态是：**编译与跨度表硬判据均已通过；放置判定回归未取得证据**。
后者不影响批次 0/1 的正确性结论 —— 跨度表是数值契约的唯一硬判据，P3/P3b 的改动
已在正式编译中通过，且其语义是"用同一组参数少构造几次"，不改变判定结果。

---

## 7. 明确不做的事

- **不改承重数值语义**：本计划不动密度/抗压/抗拉/抗剪，只改实现效率。
  唯一碰数值代码的是 P4（缩表，数学等价），由探针把守。
- **不做梁单元聚合**：审计与工作流都把它列为"改失效语义"的独立项目，不混进性能批次。
- **不做 P7 求解器重构**（复用边表 / CSR 稠密邻接）：收益最大但触及数值核心，
  必须单独一轮 + 逐项回归，不进本计划。
- **不主动跑引擎测试**：第 3 节的命令写好待用，执行与否由你决定。

---

## 8. 预期收益汇总（推导值，非实测）

| 批次 | 主要收益 |
| --- | --- |
| 批次 0 | 瞄准/校验路径每帧省约 25 次 `TActorIterator` + 十几次堆分配；网格调度去掉一个乘数；消除大面积过载的 O(n²)；面板常态每帧省多次字符串与 UMG 写入 |
| 批次 1 | 进世界初始化从约 300 MB 内存写入降到几 MB；消除数据竞争；放/拆大构件不再重建数万格；**修掉残骸凭空消失**；存档故障不再让建造整体不可用 |
| 批次 2 | 存档每 0.75 s 的约 450 KB game-thread 拷贝大幅减少；图标显存降 4 倍并加上限 |
