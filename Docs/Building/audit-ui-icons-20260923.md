# 体素建造 UI 侧性能与正确性审计（2026-09-23）

只读审计。范围：`Source/FPSGAME/Building/VoxelBuildWidget.cpp/.h`（928/190 行）、`Source/FPSGAME/Building/VoxelBuildIcons.cpp/.h`（382/91 行），以及与之直接交互的 `VoxelBuildComponent.cpp`、`VoxelBuildWorld.cpp` 相关行。审计过程中未修改任何源码、未启动引擎、未运行测试；本报告是本次审计唯一落盘产物。所有行号均经实读核对。

文中"每帧"指抽屉可见（`SelfHitTestInvisible`）期间的 NativeTick 频率；"建造态"指 `bActive==true`（含面板收起、正在摆放的阶段）。

---

## ① 执行摘要

### 最贵三件事（按真实成本排序）

| # | 问题 | 位置 | 量级估计 |
|---|------|------|----------|
| 1 | **打开抽屉/展开子菜单的图标渲染突发**：每键两次 `CaptureScene()`（Color+Coverage 双 pass），且 `Prepare` 首次命中资产时 `LoadSynchronous` 同步加载网格/材质，打开瞬间可能卡一帧 | `VoxelBuildIcons.cpp:315`（双 Capture）、`:196-197`（同步加载） | 同步加载 0.5–20 ms/资产（首帧卡顿）；之后每键 0.3–1.5 ms GPU，队列每帧只处理 1 键（`:328`），突发被摊到前 ~1 s，约 1–2 ms/帧 |
| 2 | **建造态每帧字符串构造链（生产端无守卫）**：`UpdateWidget` 每帧无条件拼 Message + 2 次 `FString::Printf`，叠加 `StructureStatus()`（2–3 次 Printf）与 `WeakestJointSummary()`（1 次 Printf），全部构造完才被 `ShowState` 的签名守卫丢弃；**面板收起后仍在跑** | `VoxelBuildComponent.cpp:1234-1255`、`VoxelBuildWorld.cpp:575-588`、守卫在 `VoxelBuildWidget.cpp:880-882` | ~3–8 µs/帧 + 每帧 4–8 次堆分配；绝对值小，但守卫位置错误且作用于玩家看不见面板的阶段 |
| 3 | **浮窗（Tooltip）活跃期每帧布局失效**：跟随阶段每帧 `SetPosition+SetSize` 重排浮窗子树；钉住后 `SetSize/SetPosition` 仍每帧无条件写入；hover 边沿整卡重建 10–30 个子控件 | `VoxelBuildWidget.cpp:342-343`（每帧写）、`:252-280`（hover 重建） | 跟随阶段 ~0.02–0.08 ms/帧；钉住后 <10 µs/帧（依赖 Slate 内部相等短路，见 ⑤-1）；hover 重建 ~0.1 ms/次 |

另确认一处**中低严重度 bug**（PIE 双开下文件级 `DrawerKeyFrame` 跨世界共享，BUG-1）与一处**文档-代码语义不一致**（超限播报的重新武装阈值，F-1）。任务书点名的"缓存回收正在显示的键""浮窗悬空回调""空指针"经逐路径推演**均未发现可复现问题**（见 ④）。

### 与文档（voxel-build-workflow.md）声明的核对

| 文档声明 | 代码事实 | 结论 |
|---|---|---|
| 图标缓存 `MaxCachedIcons=32`（第 372 行） | `VoxelBuildIcons.cpp:28` | 一致 |
| 失败重试 `MaxBuildAttempts=3`，"文件级计数"（第 373 行） | `VoxelBuildIcons.cpp:30`；计数 `Attempts` 是 subsystem **成员**（`VoxelBuildIcons.h:77`），非文件级 static | 上限一致；"文件级"表述与代码不符，但两种存放方式在 GameInstance 重建/类重载下都重置，**可见行为一致** |
| 成功记 `built key=...` 日志、成功后重试计数清零 | `VoxelBuildIcons.cpp:366,369` | 一致 |
| 面板预警 ≥85% 琥珀、≥100% 红（第 36 行） | `VoxelBuildWidget.cpp:875,887,894` | 一致 |
| 提示栏边沿播报、"回落到 80% 重新武装" | warn 通道实际 0.80 重新武装（正确）；**break（超限）通道是 1.0 边沿重新武装**（`VoxelBuildComponent.cpp:1269`），与文档"80%"不符 | **部分一致，见 F-1** |
| 状态行显示 `求解 3.2 ms · 480 节点（局部 + 96 边界）`（第 59 行） | `VoxelBuildWorld.cpp:597-603` `SolverSummary()` | 一致（任务简报中的 `求解 3.2 ms · 480 节点` 是无后缀简写） |

### 确认 bug 一览（详见 ④）

| ID | 严重度 | 摘要 |
|----|--------|------|
| BUG-1 | 中低（仅影响 PIE 调试） | `DrawerKeyFrame` 是文件级 static（`VoxelBuildComponent.cpp:96`），PIE 双开共享进程级 `GFrameCounter`，一个 PIE 窗口的抽屉按键会吞掉另一个窗口同帧的 B/Esc/数字键 |
| BUG-2 | 低 | `FailedKeys` 只在 `Deinitialize` 清空（`VoxelBuildIcons.cpp:123`）：瞬时环境失败（3 次重试用尽后）在整个 GameInstance 生命周期内永久拉黑该键，卡片恒显"暂无预览" |
| F-1 | 低（文档不一致） | 超限（≥100%）播报在 Risk 回落到 [85%,100%) 后即重新武装（`NoticeRisk<1.f`），并非文档所称回落 80%；Risk 在 99%↔101% 振荡时每次上穿 100% 都会再播"结构超限" |
| 备注 | 信息 | `SetContent` 的 Same 守卫漏比 `bExpandable` 字段（`VoxelBuildWidget.cpp:392-397`）；当前数据源恒 true（`VoxelBuildComponent.cpp:484`），无现行影响 |

审计中提出后又**排除**的候选问题（避免复查时重走弯路）：

- ~~收回动画期间 `RefreshIcons` 空转~~：`SetDrawerOpen(false)` 立即置 `bDrawerOpen=false`（`:348`），`RefreshIcons` 首行拦截（`:493`）。
- ~~缓存回收可能回收正在显示的键~~：淘汰循环只扫 `Uses`（仅 Build 成功才登记，`:321`），"正在显示"由同帧内先重建后 pin 的顺序保证（`:708`→`:910`→`:494`）；未找到可复现路径，仅存在对调用顺序的单点依赖（见 ④-B1 的加固建议）。
- ~~浮窗回调悬空持有~~：Proxy→Widget 是 `TWeakObjectPtr` 且判空（`.h:62`、`.cpp:96-108`）；`CardIndex` 与 `Cards` 同生命周期，RebuildCards 先 `HideTooltip(true)` 清索引（`:706`）。
- ~~建造世界未初始化空指针~~：所有链路均有判空（见 ④-B4）。

---

## ② 每帧路径审计

### 2.1 UVoxelBuildWidget::NativeTick（`VoxelBuildWidget.cpp:904-928`）

```cpp
904: void UVoxelBuildWidget::NativeTick(const FGeometry& Geometry,float Delta)
905: {
906:     Super::NativeTick(Geometry,Delta);
907:     RefreshLayout();
908:     if(bCardsDirty){bCardsDirty=false;RebuildCards();bSelectionDirty=true;RefreshCategory();}
909:     // Thumbnails are captured one per frame by the icon subsystem; the cards pick them up here.
910:     RefreshIcons();
911:     if(bSelectionDirty){bSelectionDirty=false;RefreshSelection();}
912:     if(TooltipIndex!=INDEX_NONE)UpdateTooltipPlacement();
913:     DrawerProgress=FMath::FInterpConstantTo(DrawerProgress,bDrawerOpen?1.f:0.f,Delta,4.f);
914:     if(Surface)Surface->SetRenderTranslation(FVector2D((1.f-DrawerProgress)*DrawerWidth,0.f));
```

#### 2.1.1 RefreshLayout：稳态有守卫，过渡期全量重排（低风险）

`VoxelBuildWidget.cpp:801-802`：

```cpp
801:     const FVector2D View=UWidgetLayoutLibrary::GetViewportSize(this);const float Scale=ColdSteelUI::PixelScale(this);
802:     if(View.Equals(LastViewport,.5)&&FMath::IsNearlyEqual(Scale,LastScale,.001f))return;
```

稳态下 View/Scale 恒定，802 行直接 return，每帧只剩两次查询（GetViewportSize + PixelScale，各 <1 µs）。**任务书担心的"每帧重排/Invalidate"在稳态不成立**。窗口拖动、RHI 尺寸过渡、DPI 曲线过渡期间 View 会亚像素步进，每次通过守卫触发一轮全量重排（约 60 次 SetFont + 30–60 组 SetBrush/SetPadding/SetOffsets，单轮 ~0.05–0.2 ms）；过渡通常 <1 s，随后收敛。`bScaleChanged` 时还会重建浮窗（`:838`）并置 `bCardsDirty` 整卡重建——这是过渡期最重的一步。**结论：稳态免费、过渡期一次性突发，无需修改**；若要削峰可给重排加"连续 N 帧尺寸稳定才应用"的去抖，不建议现在做。

#### 2.1.2 RefreshIcons 的每帧成本（打开状态下）

`VoxelBuildWidget.cpp:491-518`：每个带图卡片一次 `Icons->Find(Card.IconKey)`（TMap Find + FString 哈希 + `Uses.Add` LRU touch）+ `GetBrush().GetResourceObject()` 比较；未命中则 `Icons->Request(...)`（内部 3 次 TSet/TMap 查询，`:59-62`）。对三栏全展开的典型配置（3 材质行 + 5 形状 + 9 构件 ≈ 17 卡）：每帧 ~17 次 Find + 若干 Request 查询，**量级 ~2–5 µs/帧，可忽略**。

两处脏标记确认有效：

- `RefreshIconPins` 有 `bIconPinsDirty` 守卫（`:522`），且 `SetVisibleKeys` 内部还有一层集合相等短路（`VoxelBuildIcons.cpp:74-79`）——双保险，不是每帧重建哈希集。
- `RefreshSelection` 有 `bSelectionDirty` 守卫（`:911`）。

#### 2.1.3 Tooltip：跟随与钉住阶段的每帧布局失效（确认）

`UpdateTooltipPlacement`（`:315-344`）在 `TooltipIndex!=INDEX_NONE` 时每帧执行，末尾：

```cpp
338:     FVector2D Position=bTooltipPinned?TooltipSlot->GetPosition():FVector2D(Mouse.X-Extent.X-Gap,Mouse.Y+Gap);
...
342:     TooltipSlot->SetPosition(Position);
343:     TooltipSlot->SetSize(Extent);
```

- **跟随阶段（前 0.7 s）**：位置随鼠标每帧变 → 每帧 SetPosition+SetSize → 浮窗子树每帧 Measure/Arrange（10–30 行文本），~0.02–0.08 ms/帧。跟随本身就是移动 UI，这笔成本合理。
- **钉住后**：`Position` 取自当前槽位（`:338`），Extent 不变，但 `:342-343` 仍**无条件写入**。`UCanvasPanelSlot::SetSize/SetPosition` 是否有相等短路取决于引擎版本（UMG 槽位属性 setter 普遍直接触发布局失效），最坏情况是钉住期间每帧白做一次浮窗子树失效传播。量级小（<10 µs），但修复也小：

```cpp
// 钉住后值不变即跳过写入
if(!bTooltipPinned || !Position.Equals(TooltipSlot->GetPosition()) || !Extent.Equals(TooltipSlot->GetSize(),.01f))
{
    TooltipSlot->SetPosition(Position);
    TooltipSlot->SetSize(Extent);
}
```

- **重绘范围**：浮窗 `ClipToBounds`（`:217`），失效限于浮窗子树，不传染抽屉主体。**浮窗内容不每帧重建**——`ShowTooltip` 只由按钮 `OnHovered/OnUnhovered` 边沿触发（`:571-572,645-646` 绑定，`:101-109` 转发）。
- hover 边沿的整卡重建（`:252-280` ClearChildren + 逐行 `Text()`）：每次 ~0.1 ms、10–30 个新 UTextBlock/UBorder（`bTrack=false` 不进 `Labels`，`:119`），旧子控件等 GC 回收。快速扫过一排卡 = 每秒数次重建，可接受；若将来加长浮窗内容可考虑复用行控件。

#### 2.1.4 抽屉动画三写

`:914` `Surface->SetRenderTranslation`、`:919` `Backdrop->SetRenderOpacity`、`:922` `Blur->SetRenderOpacity` 每帧执行。动画期间值必变，必须写；收敛后（DrawerProgress 到 1 或 0）值恒定，Slate 的 render-transform/opacity setter 有相等短路，实际不触发重绘，仅剩三次虚调用。**量级 <1 µs，不构成问题**。

#### 2.1.5 状态行与预警行：守卫在消费端、成本付在生产端（确认）

调用链：`UVoxelBuildComponent::TickComponent`（`VoxelBuildComponent.cpp:1349`）→ `UpdateWidget()`（`:1222`）→ `Widget->ShowState(...)`（`:1229/1239/1252`）。

组件侧每帧无条件构造（`VoxelBuildComponent.cpp:1234-1235`）：

```cpp
1234:     const FString ClipNote=ClippedPlayerCells>0?FString::Printf(TEXT(" · 已跳过 %d 格（角色所在位置）"),ClippedPlayerCells):FString();
1235:     const FString Message=(FeedbackTime>0?Feedback:(SelectedPrefab()?PrefabMessage:TargetMessage))+ClipNote+TEXT("\n")+BuildWorld->StructureStatus();
```

加上 `:1239/:1252` 的 Headline/Brush 两次 Printf、`:1231/1242/1255` 的 `WeakestJointSummary()`（`VoxelBuildWorld.cpp:570-573` → `JointSummary` 一次 Printf，`:542-546`）、`StructureStatus()` 内部（`VoxelBuildWorld.cpp:575-588`，含 `JointSummary(...,true)` 与 `SolverSummary()` 各一次 Printf）——合计**每帧 4–8 次 FString 堆分配 + 2–5 次 Printf**。消费端 `ShowState` 的签名守卫（`VoxelBuildWidget.cpp:880-882`）随后把它们丢弃：

```cpp
880:     const FString Signature=FString::Printf(TEXT("%d|%d|%d|%s|%s|%s|%s"),
881:         bValid?1:0,bSnapEnabled?1:0,RiskLevel,*Headline,*Brush,*Message,bWarn?*StructureSummary:TEXT(""));
882:     if(Signature==LastState)return;
```

守卫本身设计正确（风险分级、摘要都参与签名，`Risk` 行只在文本变化时 SetText，`Risk->SetText` 不会每帧执行）；问题全在生产端。这些数值都是低频变化的（方块数、格坐标、求解毫秒、最弱接缝），却以帧率频率重新格式化。

**额外确认：面板收起的建造态（bPanelOpen==false && bActive==true）此链路每帧照跑**（`VoxelBuildComponent.cpp:1387` `UpdateWidget()`），此时玩家根本看不到状态行——纯浪费。

**建议（P1）**：把判定前移到组件侧——`UpdateWidget` 先用廉价分量（`FeedbackTime>0`、`SelectedMaterial/Component/Brush`、`ClippedPlayerCells`、`BuildWorld->StructureRevision()`、`ResultMessage` 缓存）拼签名，变化才构造字符串调 `ShowState`；或给 `AVoxelBuildWorld` 缓存 `StructureStatus()/WeakestJointSummary()` 结果、随 `StructureRevision()` 失效。后者还能顺带让 `UpdateStructureWarning` 的播报路径受益。

#### 2.1.6 Tick 在面板关闭时是否还在跑（任务书 A6）

| 阶段 | Widget Tick | 组件侧 UpdateWidget | 图标队列 |
|---|---|---|---|
| 抽屉打开 | 每帧全路径 | 每帧（`:1371`） | 每 Tick 1 job |
| 收回动画（~0.25 s） | 跑：RefreshLayout 守卫拦截、RefreshIcons 被 `:493` 拦截、动画插值必须跑 | 每帧（建造态） | 已 `Suspend()` 清空 |
| 完全收起（Collapsed） | **停**（UMG 不 tick 隐藏控件） | **仍在跑**（`:1387`，建造态） | `IsTickable()==false`（`VoxelBuildIcons.h:45`） |

结论：widget 侧关闭后零成本（除收回动画）；**真正的关闭态残留是组件侧 UpdateWidget 的每帧字符串构造**（见 2.1.5）。图标子系统队列空时不 tick，空闲零成本。

### 2.2 浮窗（Tooltip）专项（任务书 A2）

- **内容重建时机**：仅 hover 边沿（见 2.1.3），**不是每帧重建**。
- **鼠标移动重绘范围**：跟随阶段每帧移动+重排浮窗子树（ClipToBounds 限幅）；钉住阶段仅剩几何查询（`PointerWithin` ×2，纯 CachedGeometry 数学，<1 µs）+ 可疑的每帧 SetPosition/SetSize（见 2.1.3）。
- **悬停数据**：`ShowTooltip` 内 `Entry` 指针只在函数体使用；`TooltipIndex` 是整型索引而非指针，RebuildCards 先 `HideTooltip(true)`（`:706`）防止重建后旧索引指向新卡。**无悬空**。

### 2.3 PushPanelContent 与 WorstBond 更新频率（任务书 A4）

- `PushPanelContent`（`VoxelBuildComponent.cpp:445-543`）只在 `TryInitializeWorld` 成功路径调用一次（`:214`）。**不是每帧推**。内部约 150 次离线净跨求解（每材质 2 口径 × 25 格），是世界初始化一次性开销，与文档第 330 行声明一致，不进每帧。
- `SetContent` 全字段 Same 守卫（`VoxelBuildWidget.cpp:386-404`）覆盖 Id/Caption/Detail/MaterialId/ShapeMode/IconCells/Mesh/Surface/ActorClass/PivotOffset/Subtitle/Note/Rows/NumericRows；**漏比 `bExpandable`**（`:392-397` 无该字段）。palette 端恒 true（`:484`），现状无影响，列为守卫完备性备注。
- **WorstBond 更新频率**：面板每帧读 `BuildWorld->WeakestJointRatio()`，实现是一个 float 读取（`VoxelBuildWorld.cpp:565-568`），**读取廉价、不触发求解**；应力求解频率由 `VoxelBuildWorldStructure.cpp` 的脏标记驱动（不在本次审计范围）。

### 2.4 每帧 TMap 查找、大数组拷贝、FText 构造清单（任务书 A5）

| 项 | 位置 | 频率 | 量级 |
|---|---|---|---|
| `Icons->Find(key)` ×卡数 | `VoxelBuildWidget.cpp:501` | 每帧×~17 | ~2–5 µs |
| `SetVisibleKeys` 相等短路 | `VoxelBuildIcons.cpp:74-79` | 仅 pin 脏时 | 非每帧 |
| `FString::Printf` ×4–8 | `VoxelBuildComponent.cpp:1234-1255`、`VoxelBuildWorld.cpp:575-603` | **每帧（含面板收起）** | ~3–8 µs + 堆分配 |
| `FText::FromString`（状态区 4 行） | `VoxelBuildWidget.cpp:890-901` | 仅签名变化时 | 低频 |
| `FText::FromString`（占位符"加载中/暂无预览"） | `VoxelBuildWidget.cpp:514` | **每帧×未就绪卡数**（见下） | 小但可免 |

最后一项值得点名：`RefreshIcons` 对每张还没出图的卡，每帧执行 `Placeholder->SetText(FText::FromString(Icons->HasFailed(...)?"暂无预览":"加载中"))`（`:511-515`）——同一次重建里占位文本不会变，却每帧构造 FText 并 SetText。SetImage/SetVisibility 部分有"值相同即免"的行为（SetVisibility 相同值时引擎内部短路），但 FText 构造本身每帧发生。量级：每张等待中的卡 ~0.5 µs + 一次堆分配，首开抽屉的 1 s 内 ~17 张。**建议**：占位文本只在 `Icons->HasFailed()` 状态翻转时更新一次（FCard 里记一个 `bPlaceholderFailed` 位）。

### 2.5 状态行/预警行：脏标记还是无条件 SetText？（任务书 A1 收口）

- **SetText 调用是签名驱动的**：`Status/Selection/Structure/Risk` 四行全部位于 `:883` 签名守卫之后，内容不变时不写。
- **每帧字符串构造是无条件的**：成本在组件生产端（2.1.5）。
- **Risk 行**：`RiskLevel`（0/1/2）与 `StructureSummary` 文本参与签名（`:879-881`），Risk 90%→92% 时摘要里 `格(x,y,z)` 变化 → 签名变 → 刷新。琥珀/红由 `bDanger` 选色（`:894`）。**无遗漏**。

---

## ③ 图标子系统审计（VoxelBuildIcons）

### 3.1 队列与节流（任务书 A3）

- `Request`（`:56-63`）：`Materials/Pending/FailedKeys` 三重去重，**幂等**。
- `Tick`（`:325-382`）：每帧最多 1 job（`:328` 只取队头）；Prepare 与 Build 间隔 ≥0.05 s、纹理未流入再等到 0.35 s（`:337-340`）：

```cpp
337:         const double Age=FPlatformTime::Seconds()-Front.PreparedAt;
338:         bool bReady=true;
339:         for(const auto& Texture:WarmingTextures)if(Texture.IsValid()&&!Texture->IsFullyStreamedIn()){bReady=false;break;}
340:         if(Age<.05||(!bReady&&Age<.35))return;
341:         bOk=Build(Front.Request);
```

- `IsTickable()` 为 `!Queue.IsEmpty()`（`VoxelBuildIcons.h:45`）——队列空零开销。**设计良好**。
- **每键成本**：Build 里两次 `CaptureScene()`（`:315`，Color FinalToneCurveHDR + Coverage SceneColorHDR，各 256×256），`PRM_UseShowOnlyList` 限场景到本键组件（`:281-283`），阴影/雾/TAA 已关（`:151-153`）。量级 0.3–1.5 ms GPU/键。打开抽屉 17 键 → 前秒每帧 1 键、约 1–2 ms/帧的持续突发，随后衰减。**可接受；打开瞬间的同步加载（3.4）才是要修的**。
- Coverage 双 pass 是既有配方（与枪匠工作台一致，注释 `:163-164`），合并 pass 需改共享材质，**不建议在本次范围动**。

### 3.2 缓存回收与帧内同步重渲（任务书 A3 后半）

- 回收点两处：`SetVisibleKeys`（`:88-94`）与 Tick 成功路径（`:371-381`），`ReleaseEntry`（`:114-119`）只 `ReleaseResource()` + 移除四张表，**不触发任何重渲**。
- 被回收键重新显示时：`RefreshIcons` Find 未命中 → 占位"加载中" → `Request` 重新排队，走 3.1 节流。**确认：回收不会帧内同步重渲**。
- 回收扫描 O(Materials)（≤32+可见 pin 数），<1 µs，忽略。
- `Suspend()`（`:109-112`）清队列与 pin 集但**不缩缓存**（`SetVisibleKeys({})` 只把非 pin 项淘汰到 ≤32），重开抽屉命中缓存。符合 `:81` 注释"Cached images remain available for reopening"。

### 3.3 任务书 B1 前半：回收是否可能命中正在显示的键

逐场景推演：

1. **超限淘汰的候选集**：两处淘汰循环都只遍历 `Uses`（`:91`、`:375`）；`Uses.Add` 只在 Build 成功时执行（`:321`）。排队中（Pending）的键不在 `Uses`，**永远不会被淘汰循环选中**。
2. **"正在显示"的定义**：`VisibleKeys`，由控件在卡片重建同帧 pin（`:717` 置 dirty → 下一次 `RefreshIcons` 先 `RefreshIconPins`（`:494`）→ `SetVisibleKeys`）。重建（`:708` ClearChildren）与新 pin 之间无帧间隙。
3. **保护语义**：淘汰循环显式跳过 `VisibleKeys`（`:91/:375`），全 pin 时宁可超限（`:374` 注释自述）。三栏全展开 17 键 < 32 上限，正常操作到不了"全部 pin 且超限"。
4. **唯一脆弱点**：顺序依赖——`Suspend()` 里先 `Queue.Reset()` 后 `SetVisibleKeys({})`（`:111`）；若反过来，清 pin 后到清队列之间的同一个 Tick 有可能淘汰全缓存。现状顺序正确。

**结论：未发现可复现的"回收正在显示的键"**。文档第 372 行描述的是 16 上限旧版的历史行为，现行 pin 机制正确。给出一条零成本加固（消除对调用顺序的依赖，P3）：

```cpp
// 两处淘汰循环同时排除 Pending，语义上"排队中的键不属于可回收集合"：
for(const auto& Entry:Uses)
    if(!VisibleKeys.Contains(Entry.Key)&&!Pending.Contains(Entry.Key)&&Entry.Value<Use){...}
```

### 3.4 Prepare/Build 的同步加载与场景组装

- `Request.Mesh/Surface.LoadSynchronous()`（`:196-197`）：**打开抽屉若命中未加载资产，首帧同步加载卡 0.5–20 ms/资产**。构件类还有 `LoadSynchronous` Class + SpawnActor 组装（`:204-225`）。这是任务书 A3"打开抽屉的渲染突发"里比双 Capture 更尖的一根刺。
- **建议（P2）**：进建造模式（`SetBuildMode(true)`，`VoxelBuildComponent.cpp:247`）时对 `PushPanelContent` 产出的全部 icon 请求调一次 `Icons->Request(...)`（不打开抽屉也入队）。队列节流会把渲染摊开，而 `Prepare` 的同步加载发生在按 B 之后、玩家还在过渡的窗口里；抽屉打开时大部分键已 `Materials` 命中。注意 `Suspend` 只在抽屉关闭时调用（`:351`），进建造模式先于打开抽屉，时序成立。
- `Prepare` 在非 playing 世界组装（`SetEditor(false)`、`SetActorTickEnabled(false)`，`:138/:210`），池组件双清（Prepare 开头 `:198` 与 job 收尾 `:346` 各一次 `ClearPool`）。**组件不跨 job 保留，确认**。
- `ContentKey`（`:35-42`）只在建卡时调用，**不在每帧路径**。

### 3.5 任务书 B1 后半：重试计数与 FailedKeys

`VoxelBuildIcons.cpp:348-366`：

```cpp
351:         int32& Tries=Attempts.FindOrAdd(Job.Request.Key);
352:         ++Tries;
353:         if(Tries>=MaxBuildAttempts)
354:         {
355:             FailedKeys.Add(Job.Request.Key);
...
365:     // 成功清零，缩略图被 LRU 回收后仍能重建（此前成功也计数，重建 3 轮后永久拒绝）。
366:     Attempts.Remove(Job.Request.Key);
```

- 失败累加、3 次后进 `FailedKeys`、`Request` 对其静默跳过（`:60`）——与文档一致。
- **成功后 `Attempts.Remove` 清零：是**（`:366`）。任务书担心的"成功也计数→3 轮后永久拒绝"是已修复的旧版行为，注释与文档均记录。
- **BUG-2（低）**：`FailedKeys` 仅 `Deinitialize` 清空（`:123`）。瞬时环境失败（例如 `ResolvedMaterial` 尚未就绪的边缘窗口、某资产流送异常）会让该键整个 GameInstance 生命周期显示"暂无预览"。文档第 373 行"有限次重试"只覆盖了单次请求链路，没有覆盖"稍后环境恢复"场景。**建议（P3）**：`SetVisibleKeys` 重新包含某失败键时给一次重置机会，并加会话级防抖（每键最多重置 1–2 次）避免"失败→重试→再失败→每帧 2 次 CaptureScene"的抖动：

```cpp
// SetVisibleKeys 内，替换集合之前：
for(const FString& Key:Keys) if(FailedKeys.Contains(Key) && !FailedRetryBudget.Contains(Key))
{ FailedKeys.Remove(Key); Attempts.Remove(Key); FailedRetryBudget.Add(Key); }
```

### 3.6 文件级 static 与 PIE 双开 / Live Coding（任务书 B1 第三问）

- **UVoxelBuildIcons**：GameInstanceSubsystem，PIE 双开时每个 GameInstance 各一份实例，`Attempts/FailedKeys/Uses/Materials/Queue` 全部是成员——**互不干扰**。文档"文件级计数"与代码不符（成员），但可见行为等价（都随实例重建而重置）。
- **`DrawerKeyFrame`（`VoxelBuildComponent.cpp:96`）是真正的文件级 static**，见 ④ BUG-1。

---

## ④ 确认 bug 清单（对应任务书 B1–B5）

### B1 缓存回收 / 重试计数 / 文件级 static

1. **回收正在显示的键**：未发现可复现路径（推演见 3.3）；存在对 `Suspend()` 内清空顺序的单点依赖，建议加 `!Pending.Contains` 加固。
2. **重试计数成功后清零**：**是**（`VoxelBuildIcons.cpp:366`）。
3. **文件级 static**：
   - Icons 的计数容器是成员不是文件级，PIE 双开隔离正确；
   - **`DrawerKeyFrame` 是文件级 static，PIE 双开有实际影响 → BUG-1**：

```cpp
// VoxelBuildComponent.cpp
94:     // Last frame the drawer widget consumed a key itself; keeps the same press from running twice.
95:     // File scope instead of a member so the change stays a function-body patch.
96:     uint64 DrawerKeyFrame=0;
...
1089:     const bool bDrawerHandled=GFrameCounter==DrawerKeyFrame;
```

  两个 PIE 世界共享进程级 `GFrameCounter` 与该 static：窗口 A 的抽屉按键置位后，窗口 B 同帧的 `bDrawerHandled` 判定为 true，B 的 B/Esc/数字键被吞（`:1092/:1105/:1116-1124`）。影响限于 PIE 多窗口调试；打包单世界无影响。**修复（P4）**：把 `DrawerKeyFrame` 移为 `UVoxelBuildComponent` 成员——注释（`:95`）自述当初用文件级只是为了让改动停留在函数体补丁内，现在整个文件可改，没有理由保留。Live Coding 场景下成员随实例重建重置，语义与文档"热补丁重置只多试一次"一致。

### B2 预警边沿播报状态机（85/100/回落 80）

`VoxelBuildComponent.cpp:1258-1282` 全量推演（`NoticeRisk` 记上次读数）：

```cpp
1263:     if(Risk<.8f){NoticeRisk=0;return;}
1264:     if(Risk<.85f)return;
...
1269:     const bool bBreak=Risk>=1.f&&NoticeRisk<1.f;
1270:     const bool bWarn=Risk<1.f&&NoticeRisk<.85f;
1271:     if(bBreak||bWarn){ ... PostNotice ... }
1281:     NoticeRisk=Risk;
```

关键机制：**[0.80, 0.85) 区间在 1264 行提前 return，`NoticeRisk` 冻结不动**；只有 <0.80 才清零（1263），只有 ≥0.85 才更新（1281）。据此：

| 场景 | 行为 | 判定 |
|---|---|---|
| 0 直冲 120% | 首次 bBreak 播"结构超限"，此后不重复 | 正确 |
| 90%→95%→99% 连升 | 首次过 85% 播"结构预警"，之后 bWarn 需要 `NoticeRisk<0.85` 不再满足 | 正确，不刷屏 |
| 99%→101% | bBreak（0.99<1）播"超限"，warn→break 语义递进正确 | 正确 |
| 105%→92% | 不播（bWarn 假：1.05⊄<0.85）；1281 把 NoticeRisk 更新为 0.92 | 正确 |
| 86%→83%→86% 抖动 | 83% 走 1264 冻结 NoticeRisk=0.86，回 86% 不播 | 正确（这就是 1263/1264 组合的目的） |
| 86%→79%→86% | 79% 清零 NoticeRisk=0，回 86% 再播一次 | 正确，符合"回落 80% 重新武装" |
| **95%↔101% 振荡** | 每次上穿 100% 都播"超限"（101% 时 bBreak：NoticeRisk 已被上一轮 95% 更新为 0.95<1） | **与文档不符 → F-1** |
| 长期停在 102% | 只播一次，不刷屏 | 正确 |

**F-1（文档-代码不一致，低）**：文档第 36 行"回落到 80% 重新武装"对 warn 通道成立（0.80 显式清零 + 0.80–0.85 冻结的等效设计，实际很精巧）；但 **break 通道的重新武装条件是 `NoticeRisk<1.f`**，即 Risk 只要回落到 100% 以下就重新武装，80–100% 区间的回落同样武装。损伤在 99%↔101% 振荡（残骸被反复撞击、邻块连续失效等）时每次上穿都会再播。是否算缺陷取决于产品意图："每次重新超限都提醒"也是可辩护的语义。**建议**：若要严格匹配文档，把 bBreak 改为 `Risk>=1.f&&NoticeRisk<.8f`（与 warn 同一武装点）；若保留现行为，改文档措辞为"超限播报在回落到 100% 以下后重新武装"。**本次不改代码不改文档（只读审计）**。

**UI 侧行为**（Risk 文本行）：签名含 `RiskLevel` 与 `StructureSummary` 全文（`VoxelBuildWidget.cpp:879-881`），Risk 数值变化但摘要文本不变时（如 90%→92% 且最弱缝未换）不刷新——显示的是文本不是百分比，**可接受**；摘要文本一变即刷新。**无 bug**。

### B3 面板键位与 DrawerKeyFrame 同帧去重守卫是否漏

机制：抽屉持焦点时 `NativeOnKeyDown` 先收键，无条件 `MarkDrawerKeyHandled()`（`VoxelBuildWidget.cpp:443`）置帧戳；PC 的 `InputKey` 路径（`FPSGAMEPlayerController.cpp:262` → `HandleInput`）用帧戳去重。逐键核对：

- **B**（`:1090-1101`）、**Esc**（`:1103-1107`）：有 `!bDrawerHandled` 守卫。✅
- **数字键 1–9**：面板开时组件侧直接吞（`:1119-1121` `if(bNumberKey)return true;`，不依赖帧戳）；建造态走 `HandlePanelKey`（`:1123`）。widget 侧编号只认可见行（`:447-453`）。✅
- **0**：widget 侧 `:445` 明确排除 0、交给 `HandleDrawerKey`（内部 `HandlePanelKey`→`SelectComponent(None)` 并置帧戳）；组件侧 0 归入 `bNumberKey` 吞掉。✅
- **Tab/K/J/F6/LeftAlt**（建造退出键，`:1108-1109`）：**无帧戳守卫，直接执行**。widget 对这些键 `HandleDrawerKey` 返回 false → 未消费 → 事件自然落到 PC 路径 → 正常退出。帧戳置了但该分支不看它。✅ 无漏。
- **滚轮/R/F/Ctrl+Z/中键/左右键**：仅建造态（面板收起、widget 无焦点）有意义，无双路径。✅
- **冗余置位的副作用**：`MarkDrawerKeyHandled` 对 widget 收到的**每个**键都置帧戳（`:443`），包括它不处理的键。这让组件侧同帧所有帧戳守卫都为 true——但被守卫的三个分支（B/Esc/数字）widget 要么真处理了、要么组件侧另有吞键逻辑，**未发现漏键**。更精确的做法是只在 widget 真正消费键时置位，属整洁度改进而非 bug。

**B3 结论：未发现漏洞。**（帧戳机制本身在 PIE 双开下的跨窗口污染见 BUG-1。）

### B4 建造世界未初始化时的空指针

逐链路核对，**未发现空指针**：

| 链路 | 守卫 |
|---|---|
| `Builder()`（`VoxelBuildWidget.cpp:432-436`） | 可返回 null；调用点 `Pick:423`、`NativeOnKeyDown:440-441` 均判空 |
| `IconsFor()`（`:484-489`） | 可返回 null；调用点 `:351,379,495,524` 均判空 |
| `UpdateWidget`（`VoxelBuildComponent.cpp:1224`） | `if(!Widget\|\|!Palette\|\|!BuildWorld)return;` |
| `UpdateStructureWarning`（`:1273`） | GameInstance/Subsystem 链式判空 |
| `TickComponent`（`:1352`） | BuildWorld 未就绪时走重试，`!bActive` 早退；bActive=true 的前提是 `SetBuildMode(true)` 通过 `:226-232` 的就绪门 |
| `HandleInput` 内 `BuildWorld->...`（`:1151,1158,1176-1192`） | 只在 `bActive` 分支可达（`:1102`），bActive 蕴含 BuildWorld 就绪 |
| `UpdateTarget`（`:566`） | `if(!PC\|\|!PC->PlayerCameraManager\|\|!BuildWorld)return;` |
| widget 侧 `UpdateTooltipPlacement:330` 的 `RootWidget` | NativeOnInitialized 构造（`:139`），生命周期内恒有效 |

### B5 浮窗回调持有悬空数据

**未发现悬空**：

- Proxy→Widget：`TWeakObjectPtr<UVoxelBuildWidget> Panel`（`.h:62`），三个回调入口都 `Panel.Get()` 判空（`.cpp:96-108`）。
- Proxy→卡索引：`CardIndex=Cards.Num()`（`:562,636`）与 `Cards` 同生命周期；RebuildCards 开头 `Cards.Reset()+CardProxies.Reset()`（`:708`）同步重置，且先 `HideTooltip(true)`（`:706`）清掉指向旧列表的 `TooltipIndex`。
- 动态委托绑定在按钮与 proxy 之间（`:570-572,644-646`），按钮随 `ClearChildren` 脱离控件树销毁时解绑；proxy 是 widget 的 UObject 子对象，随 widget 或 GC 回收。
- `ShowTooltip` 内的 `Entry` 裸指针只在函数体使用（`:248`）。

---

## ⑤ 不确定项

1. **`UCanvasPanelSlot::SetSize/SetPosition` 的相等短路**：UMG 槽位 setter 是否在值不变时跳过布局失效，随引擎版本而异，未运行引擎验证 UE 5.8.2 的实现。2.1.3 的"钉住后 <10 µs"按"有短路"估计，若无短路则为每帧一次浮窗子树失效（0.02–0.08 ms）。修复代码两种情况下都无害。
2. **图标单键 GPU 成本**：0.3–1.5 ms/键为按 256×256 RT、ShowOnly 1–25 组件、无阴影无雾的纸面估计，未做 profile；集成显卡可能 ×3–5。
3. **`FPreviewScene` 双实例隔离**：PIE 双开时两个 subsystem 各自 `MakeUnique<FPreviewScene>`（`:138`），理论隔离；未验证 UE 5.8 下两个 preview 世界的渲染资源竞争。
4. **RT/MID 生命周期**：`ReleaseEntry` 的 `ReleaseResource()+Remove`（`:114-119`）后对象由 Transient UPROPERTY 持有至移除、再交 GC。代码层判断无泄漏，未做内存验证。
5. **文档"文件级计数"表述来源**：无法确定是笔误还是描述某个旧实现；本审计只报告差异，未改文档。
6. **`UpdateStructureWarning` 在面板打开时也每帧执行**（`UpdateWidget:1226` 先于 panel-open 分支）：设计意图（面板打开期间结构继续受力、继续播报）无法从代码确证；行为有边沿守卫、无性能问题。
7. **占位图 `SetDesiredSizeOverride(256,256)`**（`VoxelBuildWidget.cpp:587,674`）与 104 px 显示格的测量开销：UImage desired size 参与 Slate 测量，是否引入不必要的测量尺寸未实测。

---

## 附：建议优先级

| 优先级 | 项 | 收益 |
|---|---|---|
| P1 | 组件侧签名前移（2.1.5）：`UpdateWidget` 用 Revision+廉价分量短路字符串构造，或给 `AVoxelBuildWorld` 缓存 `StructureStatus()/WeakestJointSummary()` | 去掉建造态（含面板收起）每帧 4–8 次字符串构造 |
| P2 | 图标预热（3.4）：`SetBuildMode(true)` 时对全部面板卡调 `Icons->Request` | 把 `LoadSynchronous` 移出抽屉打开首帧 |
| P2 | 占位符文本状态化（2.4）：`HasFailed` 翻转才 SetText | 去掉等待期每帧 FText 构造 |
| P2 | Tooltip 钉住后值不变跳过 SetPosition/SetSize（2.1.3） | 消除钉住期的布局失效传播 |
| P3 | 淘汰循环加 `!Pending.Contains`（3.3） | 消除对清空顺序的单点依赖 |
| P3 | `FailedKeys` 有限重置（3.5） | 瞬时环境故障后自愈 |
| P4 | `DrawerKeyFrame` 改组件成员（BUG-1） | 消除 PIE 双开同帧互吞 |
| P4 | `SetContent` Same 守卫补 `bExpandable`（2.3） | 守卫完备性 |
| P4 | F-1：对齐超限播报武装点与文档（二选一：改 `NoticeRisk<.8f` 或改文档措辞） | 语义一致 |
