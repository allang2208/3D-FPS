# F6 开发面板：性能监测页（2026-09-22）

## 1. 这是什么

F6 开发面板新增第四个页签「性能监测」，用来在运行时回答两个问题：

1. **现在这一帧的时间花在哪**（帧预算）
2. **哪些组件在吃性能**（组件开销排行）

入口：游戏内按 `F6` → 顶部页签选「性能监测」。

## 2. 两条数据腿，来源不同——页面上也分开显示

这是本页最重要的设计约束：**实测值和推导值不能混在一起**。

### 2.1 帧预算：实测

| 指标 | 来源 | 说明 |
| --- | --- | --- |
| 帧时间 | `GAverageMS` | 引擎的指数平均（0.1 平滑） |
| FPS | `GAverageFPS` | 引擎直接给出 |
| Game | `GGameThreadTime` | 游戏线程占用周期数，不含空闲 |
| Draw | `GRenderThreadTime` | 渲染线程占用周期数，不含空闲 |
| RHI | `GRHIThreadTime` | RHI 线程 |
| Game 等待 | `GGameThreadWaitTime` | 主线程空闲等待；偏高说明被渲染或 RHI 拖住 |
| 关键路径 | `GGameThreadTimeCriticalPath` / `GRenderThreadTimeCriticalPath` | **含依赖等待**，比上面两个更能反映卡顿 |
| GPU | `RHIGetFrameTime()` | RHI 报告时才有，否则显示「由 RHI 未报告」 |
| 中位 / P90 / 超预算占比 | 面板自己按帧采样的滚动窗口（240 帧） | 用实测 delta，不受引擎平滑影响 |

这些量与 `stat unit` 是**同一批变量**（`RenderCore/Public/RenderTimer.h`），
所以面板上的数字应当和 `stat unit` 对得上——对不上就是有 bug。

**硬性约束：Game 与 Draw 在时间轴上重叠，不得相加当作 CPU 计算耗时。**
面板只并列显示，不做求和。

### 2.2 组件开销：推导排序分

遍历世界里的图元 / 光源 / 粒子 / 音频组件，对每一项读取**真实数据**：

- 三角形数、顶点数（LOD0）
- 材质槽数量
- 是否投射阴影
- 存活粒子数
- 距离与是否在视锥内

然后加权成一个 `Rank` 排序分：

```
几何量 = 三角数 × TriangleWeight + 顶点数 × 0.1 × TriangleWeight
Rank   = 几何量
       + 材质槽数 × 2500
       + 粒子数 × ParticleWeight × 1000
       若投射阴影且可见 → × ShadowWeight
       视锥外 → × 0.15      不可见 → × 0.05
       距离衰减 → × clamp(1 - 距离/60m, 0.1, 1)
```

**`Rank` 是相对排序分，不是毫秒。** 页面底部写明了这一点。

## 3. 为什么不显示「某组件耗时多少毫秒」

不是不想做，是 UE 不提供。写在这里避免以后重复踩：

1. **没有公开的逐组件 tick 计时接口。** `FTickTaskLevel` 定义在
   `TickTaskManager.cpp` 内部，`ULevel::TickTaskLevel` 也是私有，
   `AllEnabledTickFunctions` 不对外暴露。没有钩子可以插进去计时。
2. **GPU 不导出逐图元耗时。** MSM（多散射模型）拿不到逐图元 GPU 时间。
3. 引擎的 `stat gpu` / `stat game` 给的是**按类聚合**的耗时，不是按实例。

所以本页给的是「帧预算（实测线程级）+ 组件相对开销（真实几何量加权排序）」。
要线程级拆解用 `stat unit` / `stat gpu`；要逐实例排序用本页。

## 4. 实现时必须绕开的三个坑

### 4.1 `MinimalAPI` 类的方法在别的模块里不可见

`UStaticMesh` / `USkeletalMesh` 都声明为 `UCLASS(..., MinimalAPI, ...)`。
这意味着**只有带 `ENGINE_API` 的方法**能跨模块调用。
所以静态网格只能用 `GetNumTriangles()` / `GetNumVertices()`。

### 4.2 一批好用的取数接口是编辑器专用的

`IsNaniteEnabled()`、`GetMeshDescription()`、`GetNumImportedVertices()`
**全都被包在 `#if WITH_EDITORONLY_DATA` 里** —— 编辑器构建有，独立游戏构建没有。
用它们会让 `-game` 构建直接编译失败（报「不是 XXX 的成员」，很容易误判成头文件问题）。

因此：
- **Nanite 维度被移除**。无法在运行时可靠判定，宁缺毋滥。
- 骨骼网格改用运行时可见的 `GetResourceForRendering()->LODRenderData[0].GetNumVertices()`。
- 骨骼网格的三角数没有公开取数接口（`NumTriangles` 成员不可见），
  代码里用顶点数代替并注释说明——同量级，排序够用。

### 4.3 `ELightComponentType` 不是 UENUM

它定义在 `SceneTypes.h`，是共享给着色器的普通枚举，**没有反射**，
所以 `StaticEnum<>()` 编译不过（会报「尝试引用已删除的函数」）。
只能手动 `switch` 映射成中文名。

## 5. 面板自身的开销

扫描要遍历世界里所有 Actor 的组件，是**真实开销**。所以：

- 默认 **0.5 秒**刷新一次，可切 0.25 / 0.5 / 1 / 2 秒
- 可**暂停**
- **只在性能页可见且面板打开时**才刷新（`ActivePage == 3 && IsPanelOpen()`）
- 页面显示扫描用时（`扫描 N 个 Actor / M 个组件，用时 X ms`），
  让用户知道面板自己花了多少

排行行的控件树按 **8 行为粒度增长**，超出当前结果的行**隐藏而不销毁**。
原因：扫描只返回 `Rank > 0` 的条目，实际条数会随场景在阈值附近浮动（例如 20 与 19 之间），
若每次按实际条数重建整张列表，刷新时会持续闪烁。

## 6. 文件

| 文件 | 作用 |
| --- | --- |
| `Source/FPSGAME/UI/FPSPerformanceMetrics.h/.cpp` | 数据层：`UFPSPerformanceMetricsSubsystem`（WorldSubsystem）+ 三个 USTRUCT |
| `Source/FPSGAME/UI/DevelopmentPerformancePanel.cpp` | 页面层：构建页面、刷新排行 |
| `Source/FPSGAME/UI/DevelopmentPanelWidget.h/.cpp` | 接入：第四个页签、`ActivePage == 3` 驱动刷新 |

## 7. 设计参考：原 Godot 面板（已找到）

用户要求参考「原项目 gamedev 中性能面板的设计」。该面板**不在解包的目录树里**，
而是封在一个 zip 内，经搜索后取出：

| 文件 | 内容 |
| --- | --- |
| `E:\3d\trash\repository-ue5-root-20260910\docs\handoffs\wilderness-performance-20260908\local-experiment.zip` → `ui/performance_panel.gd` | 面板本体（F10 开关，CanvasLayer） |
| 同 zip `scripts/performance_diagnostics.gd` | 逐帧采样、F10 热键、计数器、环形缓冲（18000 帧） |
| 同 zip `scripts/performance_report.gd` | 统计契约、排序、Markdown 导出 |
| `docs\reference\game-dev-cold-steel\src\ui\panels\dev-tools.js` 第 1311–1657 行 | **设计祖先**（`性能` 页签，含占比条） |

血统证据：`performance_report.gd` 第 2 行写着
`## Statistical contract migrated from game-dev PerformanceMonitor.`

注：`E:\3d\3-dfps` 与 `E:\无尽轮回`（原 Godot 工程根）**都已不存在**，这些源码只存活在那个 zip 里。

### 7.1 从参考里采纳的部分

| 参考设计 | 本页实现 |
| --- | --- |
| **占比条** `barWidth = averageMs / topAverageMs` | 每行一条 3 px 定宽前景条，宽度 = `ShareOfTop × 轨道实测宽`，最小 2% |
| **近邻法百分位** `sorted[int((n-1)*p)]` | `NearestRank()`，不做插值，与参考同契约 |
| 八项窗口指标各带 `平均/P50/P95/P99/峰值` | 帧预算按此格式显示；着色按 **P95**（体感由尾部决定） |
| **采集器自身开销单列**（`monitor_ms`） | 帧预算里显示「面板自身扫描 平均 / 峰值 ms」 |
| 慢帧阈值 `33.34`、目标帧率、超预算帧 | `SlowFrameThresholdMs` / `TargetFps` 作为子系统 public 字段 |
| 刷新节流 2 Hz、只在可见时刷新 | 默认 0.5 s 可调，且 `ActivePage == 3 && IsPanelOpen()` 才刷 |
| 两级占比（分项占比 / 墙钟占比） | 本页用「占统计总权重」替代；墙钟占比在 UE 侧无对应量，未做 |

### 7.2 未采纳的部分及原因

- **导出 JSON / Markdown 报告**：参考的强项（含 9 条测量口径说明）。
  本页未做——用户要的是「实时检视」，导出是另一个需求。若以后要加，
  `FFPSPerformanceSnapshot` 已经带了全部所需字段。
- **慢帧样本表（帧序/位置/主要分项）**：需要逐帧记录世界状态，开销与复杂度都高。
- **环境与计数器 JSON 转储**：Godot 的 `Performance.get_monitor` 覆盖面很广；
  UE 侧对应量（`stat memory` 等）在独立构建里可用性不一，暂不纳入。
- **参考有的「诊断线索」启发式**（如 `p99 > 平均×2.5` → 尾部尖峰）：本页未做，
  因为 UE 侧的判据应与 Godot 不同，需要先有现场数据再定阈值。

### 7.3 一处纠正：参考面板没有配色阈值

子代理明确指出：Godot 面板**没有逐行配色**，只有 `title/caption/body` 三种文本角色，
阈值语义全在数值里（`threshold_ms := 33.34`、`target_fps := 140.0`）。
本页的帧预算着色（绿/黄/红）是**本页新增**的，不是从参考搬来的。

## 8. 首次实测诊断（2026-09-22，20.8 FPS）

用户现场截图（1024×1177，帧预算 + 排行前 9 项）。以下是从那一次数据得出的结论。

### 8.1 帧预算读出来的东西

```
20.8 FPS · 帧 48.07 ms
平均 49.85 · P50 50.94 · P95 52.31 · P99 54.92 · 峰值 61.96 ms
Game 51.00  Draw 4.69  RHI 2.62  Game 等待 0.00
关键路径  Game 51.00  Draw 43.58     GPU 由 RHI 未报告
超目标预算 96.2%   超 33.3 ms 慢帧 96.2%   (53 帧样本)
面板自身扫描 平均 0.4 ms · 峰值 0.6 ms
```

**先看引擎对这些变量的定义**（`Runtime/RenderCore/Public/RenderTimer.h`，逐字）：

```cpp
/** How many cycles the gamethread used (excluding idle time). */
extern RENDERCORE_API uint32 GGameThreadTime;              // L16
/** How much idle time in the game thread. */
extern RENDERCORE_API uint32 GGameThreadWaitTime;          // L19
/** How many cycles the renderthread used (excluding idle time). */
extern RENDERCORE_API uint32 GRenderThreadTime;            // L7
/** How many cycles the gamethread used, including dependent wait time. */
extern RENDERCORE_API uint32 GGameThreadTimeCriticalPath;  // L25
```

关键在最后两行：**`...Time` 不含空闲，`...TimeCriticalPath` 含依赖等待。**

于是：

1. **`Game 51.00 ms` 是游戏线程的纯计算耗时（不含空闲）** —— 这是真实工作量，不是等待。
2. **`Game 等待 0.00 ms`** —— 游戏线程没有空闲。它确实在满负荷干活。
3. `Draw` 自身 4.69 ms，而 `Draw` 关键路径 43.58 ms → 渲染线程含约 38.9 ms 的依赖等待。
   但渲染线程在等待，说明**它在等游戏线程**（游戏线程 51 ms 才是帧的限速环节）。
4. 帧时间 48.07 ms ≈ 游戏线程 51.00 ms。**限速环节就是游戏线程。**

> **结论修正（2026-09-22 晚）**：这是**游戏线程计算受限，不是 GPU 受限**。
> 早先一版本文档把它写成"GPU 受限"，那是误读了 `Draw` 关键路径的含义 ——
> 关键路径长只是说明它在同步等待，而等待的对象正是更慢的游戏线程。
> `GPU 由 RHI 未报告` 说明本次没拿到 `RHIGetFrameTime()`，GPU 时间仍是未知量，
> 但**它不构成当前限速环节**。

参考：此前同构建的 720p 稳态中位帧时间是 **12.41 ms**。现在游戏线程 **51 ms**，
约为其 **4 倍**。这是一个**游戏线程侧的回归**。

### 8.2 排行读出来的东西：玩家自己的网格占了 59%

前 9 项里 **6 项是 `FPSGAMECharacter0`（玩家）**：

| 排名 | 组件 | 三角面 | 占统计总权重 |
| --- | --- | --- | --- |
| 1 | `SkeletalMeshComponent_6` | 107.2K tri · 9 材质槽 · 投影 | 18.8% |
| 3 | `SkeletalMeshComponent_5` | 57.1K tri · 9 材质槽 · 投影 | 11.5% |
| 4 | `CharacterMesh0` | 48.7K tri · 2 材质槽 · 投影 | 7.8% |
| 5 | `DualPistolLeft` | 107.2K tri · 9 材质槽 | 7.6% |
| 6 | `AKMViewModel` | 57.1K tri · 9 材质槽 | 4.6% |

合计 **50.3%**；把第 2 名（`DGN_Maintenance_RecessPanel`，17.9%）以外的场景件都算作
「正常」，玩家自身相关项占前 9 项权重的 **59%**。

场景总量很小（188 Actor / 291 组件），所以瓶颈不在场景规模，就在这几件东西上。

### 8.3 一个明确的浪费：看不见的身体网格仍在校投影

`Content/ColdSteelData/player_body.json` 的 body mesh 是 `SKM_Manny_PlayerSkin`，而
`FPSPlayerBodyComponent.cpp:157` 写了：

```cpp
Body->SetOnlyOwnerSee(false); Body->SetOwnerNoSee(true);
Body->SetCastShadow(true);    Body->bCastHiddenShadow = true;
```

即**第一人称下玩家看不见自己的身体，但它仍在为阴影贴图渲染一遍深度**。
`FPSPlayerBodyCamera.cpp:48-51` 还把世界武器/配件/服装副本的 `bCastShadow` 一起置 true。

更要紧的是：引擎里 `bCastHiddenShadow` 的实际判据是
`bCastHiddenShadow || !IsVisible()`（`PrimitiveSceneProxy.cpp`），也就是说
**隐藏网格投阴影是引擎主动支持的合法路径**，不是 bug —— 但它每帧都要付深度 pass 的钱。

注意这与上一轮「玩家模型不是原因」的结论并不矛盾：当时测的是
`fps.body.WorldBody 0`（把网格整个隐藏），隐藏后成本**转移**到世界武器副本上，
所以总帧时间变化不大。本次是**关阴影**（网格还在，只是不再投），是另一条正交的路径。

### 8.4 新增的测量开关

```cpp
// FPSPlayerBodyComponent.h
FPSGAME_API bool FPSPlayerBodyWorldBodyShadowEnabled();
// FPSPlayerBodyComponent.cpp
void UFPSPlayerBodyComponent::ApplyWorldBodyShadow();
```

控制台变量 **`fps.body.WorldBodyShadow`**（默认 1）：

- `1` = 身体与世界装备副本照常投影
- `0` = 停止投影。第一人称下它们本来就不可见，所以只省下阴影深度 pass

第三人称下自动忽略该开关（身体是可见主体，阴影必须保留）。
必须在 `ApplyWorldBodyVisibility()` 与 `UpdateWorldOwnerVisibility()` **之后**施加：
这两条路径都会把 `bCastShadow` 重新写成 true，顺序反了会被撤销。

### 8.5 建议的 A/B 步骤

1. 打开 F6 性能页，站在同一个位置静止（先让 cvar 生效再采样）
2. 记录基线：帧预算的中位/P95
3. 控制台 `fps.body.WorldBodyShadow 0`
4. 再记录一次。**中位帧时间下降多少，就是玩家网格阴影深度 pass 的占比**
5. 顺便对照 `fps.body.WorldBody` 与 `stat gpu`

若下降明显 → 把第一人称下的玩家阴影默认关掉（保留第三人称）；
若几乎不变 → GPU 时间在别处（候选：VSM 的静态缓存失效、Lumen HWRT 的蒙皮网格 BLAS
每帧更新、场景里的 `DGN_Maintenance_RecessPanel` 那类大静态件）。

**注意测量纪律**：同构建同设置的两分钟间隔曾测出 35.56 ms 与 12.41 ms（差 3 倍），
所以任何 A/B 都要跑 2–3 次取中位，且编辑器必须关闭（否则资源争用会污染结果）。

## 9. 联机场景下的可持续方案（2026-09-22 讨论）

用户提出的正确质疑：**联机后第三人称模型必须渲染，关阴影只是治标。**

这个质疑成立，但结论要反过来 —— 联机不会让开销"不可避免"，它暴露的是当前
**资产用法**的问题，而不是"渲染第三人称"本身的必然成本。

### 9.1 根因：高精度主资产被当成世界代理用

第 8.2 节那 5 个网格的 LOD0 是 **10 万面级**。这个精度对**第一人称近景**是合理的，
但对**世界代理**（远处的其他玩家）是严重过剩 —— 一个远处玩家在屏幕上只占几十像素。

而当前架构里，世界代理**就是**第一人称那把枪的网格本体（`player_body.json` 的
`body_mesh` 与世界装备副本共用同一份资产，只是 owner-no-see 标志不同）。
单机下看不见所以没暴露，联机下每个远端玩家都要按这份精度渲染。

**所以问题不是"要不要渲染第三人称"，而是"凭什么用 LOD0 渲染第三人称"。**

### 9.2 真正可持续的方向（按收益排序）

| 方向 | 说明 | 为什么联机下更关键 |
| --- | --- | --- |
| **骨骼网格 LOD** | 让世界代理走 LOD1/2/3。UE 的骨骼 LOD 支持逐档骨骼裁剪 | N 个玩家时开销随 LOD 档位线性下降，而不是随 N 线性上升 |
| **专用的低模世界化身** | 第三人称代理用独立低模 + 武器作为挂件，不复用第一人称主资产 | 这是主流 FPS 做法；主资产可以继续为近景堆精度 |
| **距离/可见性剔除** | 远端玩家按屏幕占比与距离降档 | 联机下开销与"看得见几个人"挂钩，而不是"房间里几个人" |
| **关掉第一人称视图模型的阴影** | `fps.body.WorldBodyShadow 0` | 这条**本来就该关**，与联机无关（见 8.3） |

第 4 条是治标，但它是**正确的默认值**而非权宜：第一人称视图模型永远不被别人看见，
它的阴影没有观察者。这条不该等到联机才做。

### 9.3 面板新增 LOD 链显示

为回答"这个网格能不能降面"，面板每行现在显示 LOD 链：

```
107.2K tri · LOD 107.2K → 53.6K → 26.8K · SKM_AKM
```

- **多档**：说明远端玩家能降面，联机可扩展
- **`仅 LOD0` 且标黄**：说明该网格没有 LOD，联机时每个实例都按最高精度渲染 —— 这是隐患

同时修正了一个**之前的错误**：旧代码用顶点数冒充三角数（注释写"骨骼网格没有公开
三角数接口"），导致面板上 `107,176tri · 107,176vtx` 完全相等。实际上
`FSkeletalMeshLODRenderData::RenderSections[].NumTriangles` 是公开的，
真实三角数可以逐 section 累加。现已修正。

### 9.4 结论

- **不要**为了联机预先关掉第三人称渲染 —— 那是把功能砍掉换帧数
- **要**现在就查 LOD 链：面板标黄的行就是联机下的瓶颈候选
- 单机下 LOD0 不变（近景需要），所以这项工作对联机是纯增量收益

### 9.5 更重要的：真正的限速环节在游戏线程，与联机无关

第 8.1 节修正后的结论是**游戏线程计算 51 ms**。这意味着上面这些渲染侧的优化
（阴影、LOD、剔除）**都不会解决当前的 20 FPS** —— 它们优化的是渲染线程和 GPU，
而限速环节在游戏线程。

**当前第一优先级是找出游戏线程那 51 ms 花在哪**，而不是继续优化渲染。
候选方向：

- `stat game` 看按类聚合的游戏线程耗时
- 世界装备副本的逐帧重建（`RebuildWeapons` / `ApplyOutfit` / `CaptureEquipment`）
- `UpdateOwnerVisibility()` 与相机路径里的 `SetOwnerNoSee` / `SetCastShadow`
  反复置脏渲染状态（这两条路径每帧都跑，见下）
- `BodyAnimation` 每帧的状态写回与动画蓝图求值

其中**第二、三条值得优先查**，因为它们正是玩家建模功能引入的代码路径，与"调整加入
玩家建模以后开始有一定卡顿"这个用户观察的时间点吻合。

注意 8.5 节的 A/B（`fps.body.WorldBodyShadow 0`）仍然有价值，但它验证的是
**渲染侧**假设；若结果"几乎不变"，那就与"限速在游戏线程"的结论一致，
应立刻转向 `stat game`。

## 10. 排查游戏线程 51 ms：新增「每帧动作计数」

### 10.1 为什么不做「逐组件耗时」

引擎**没有**公开的逐组件 tick 计时接口 —— `FTickTaskLevel` 定义在
`TickTaskManager.cpp` 内部，`ULevel::TickTaskLevel` 也是私有，没有钩子可插。
所以面板不会假装给出「某组件花了 X 毫秒」。

但有一类东西**可以精确数出来，而且正好是游戏线程开销的常见来源**：
**每帧有多少次「昂贵的 setter 调用」**。

### 10.2 原理：setter 的代价

`SetOwnerNoSee` / `SetOnlyOwnerSee` / `SetCastShadow` 各自会：

1. 置脏图元的渲染状态（render state recreate）
2. 触发一次组件重注册（重新加入阴影场景）

在骨骼网格上这两件事都不便宜。而 `FPSPlayerBodyComponent` 的可见性刷新路径
**每帧都在跑**（`CalcCamera` 驱动 + 0.2 s 节流路径），一旦守卫失效，
就会从「一次性设置」变成「持续 churn」。

`FPSPlayerBodyEquipment.cpp` 里已经有守卫（只在值变化时才调 setter），
注释也写明了原因。**计数器就是来验证这个守卫是否真的生效。**

### 10.3 面板新增的计数（性能页「每帧动作计数 · 实测」）

| 计数 | 含义 | 稳态下的期望 |
| --- | --- | --- |
| **标志改动 /s** | `ApplyOwnerVisibilityFlags` 实际改动标志的次数 | **≈ 0**。持续几十次/秒 = 守卫失效，这是首要嫌疑 |
| **装备重建 /s** | `RebuildWeapons` / `ApplyOutfit` 次数 | 换武器时才该出现。持续 >0 = `EquipmentKey` 比较失效 |
| 可见性刷新 /s | 两条可见性路径的执行次数 | 每帧跑是**设计如此**，本身不代表有问题 |
| 装备采集 次 | `CaptureEquipment`（0.2 s 节流） | 约 5/s |
| 骨骼网格 / 总骨骼 | 全场景骨骼动画求值规模 | 与帧时间对照看规模 |
| 隐藏投影 | `bCastHiddenShadow && !IsVisible()` 的网格数 | 越大阴影深度 pass 越重 |
| 线程 | Game / 等待 / Draw / 等待 | 与帧预算同源，便于对照 |

速率而非绝对次数是关键：**每帧 1 次和每帧 60 次是完全不同的病。**

「标志改动」或「装备重建」速率偏高时该行会**标黄**。

### 10.4 怎么用这张截图定位

按这个顺序读：

1. **看「标志改动 /s」**
   - 若 **几十~几百** → 找到病根：可见性守卫失效，每帧在重注册组件。
     下一步查 `ApplyOwnerVisibilityFlags` 的哪个标志在反复翻转。
   - 若 **≈ 0** → 排除这条路径，继续下一步。
2. **看「装备重建 /s」**
   - 持续 >0 → `EquipmentKey` 比较失效（武器/配件路径每帧变），
     `CaptureEquipment` 里的 Key 拼接可能有非确定性字段（如 `RelativeTransform.ToString()`）。
3. **两条都正常** → 游戏线程的 51 ms 在别处。此时「隐藏投影」和「总骨骼」
   两个数能判断骨骼动画/阴影规模，若规模很大则转向 `stat anim` / `stat scenerendering`。

### 10.5 建议的截图

在**同一位置静止**，隔几秒截两三次，看速率是否稳定：

- 性能页完整内容（含新的「每帧动作计数」段）
- 顺便记录：地点、第一人称还是第三人称、画质档次

**注意**：面板默认 0.5 s 刷新一次；速率是「本刷新周期内的增量 ÷ 周期时长」，
所以采样窗口越短越灵敏，但跳动也越大。要稳态数字就把刷新间隔调到 1–2 秒。

### 10.6 用户反馈：换手枪/近战同样卡 → 武器不是主因

2026-09-22 用户实测：**切成手枪或其他近战武器一样卡**。据此：

- **A762 配件密度假设作废**（第 8.2 节那一版推测）。武器换了但症状不变，
  说明变量不在武器上。
- 注意面板第 8.2 节的排行仍然有效 —— 它反映的是**当下装备**的几何量，
  只是不能据此推断「换个武器就好了」。

**换任何武器都卡 → 主因必然在「不随武器变的东西」上**：

| 不随武器变的 | 为什么可疑 |
| --- | --- |
| 玩家身体网格 `SKM_Manny_PlayerSkin` | 始终存在，且始终投影 |
| 世界装备副本机制 | `RebuildWeapons` 在换武器时触发（可观察「换的瞬间是否更卡」） |
| **骨骼动画求值规模** | 与武器无关，**新增计数重点盯它** |
| 可见性刷新的每帧执行 | 与武器无关 |

### 10.7 新增：tick 选项分布计数

`EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones` 会**每帧强制求值
骨骼变换**，即使网格不可见 —— 比默认的 `OnlyTickPoseWhenRendered` 贵得多。
它不随装备变化，正是「换任何武器都卡」的头号候选。

面板新增两个计数：

| 计数 | 含义 | 判读 |
| --- | --- | --- |
| **每帧强制刷骨骼 N 个** | 开着 `AlwaysTickPoseAndRefreshBones` 的骨骼网格数 | **>2–3 就该警惕**；配合「总骨骼」看规模 |
| 仅求值 pose N 个 | 开着 `AlwaysTickPose`（求值 pose 但不刷骨骼变换） | 中等开销 |

若「每帧强制刷骨骼」数量大（例如十几个）而总骨骼数又高，那每帧都有大量骨骼变换
被白白重算 —— 这能解释一个与武器无关、与玩家建模同时出现的固定开销。

### 10.8 一个必须说明的读数问题

面板上 `Game 47.29 ms` 与 `平均 30.06 ms`（=31.7 FPS）**互相矛盾**：
`GGameThreadTime` 在 `UnrealClient.cpp:1844` 是「两次 `FViewport::Draw` 之间的
时间差减去空闲」，理论上应当 ≈ 帧间隔，不该超过帧时间。

**所以不要把 `Game` 那一行当成精确耗时。** 它的量级（几十毫秒）与趋势可信，
绝对值与 `平均` 对不上，说明口径有差异（可能是平滑窗口不同，或该统计取自
与 `GAverageMS` 不同的更新点）。在查清之前：
- **以「平均 / P95 / FPS」为准**（这几个数自洽：1000/31.52 = 31.7）
- `Game` / `Draw` 只用于**互相比较趋势**，不用于绝对判断

## 11. 已知缺陷与外部审查

同期另一份审查（`performance-panel-review-plan-20260922.md`，2026-09-22 12:29）对本文档
描述的面板源码做了逐条复核，指出以下缺陷。**本文档尚未逐条复核其结论，也不表示已修复**，
在此登记以免下游误用：

| 编号 | 结论 | 与本文档的关系 |
| --- | --- | --- |
| F01 | 帧时间采样链是 `Widget NativeTick → RefreshPerformance → SampleFrame`；Slate 把 delta 限制在 1/8 秒，长卡顿被截到 125 ms | **与本面板 10.3 节的计数无关**，但说明「峰值」一列不可作为卡顿长度依据 |
| F02 | `RHIGetFrameTime()` 返回 RHI 帧**间隔**（墙钟），不是 GPU busy 时间 | 直接推翻第 8.1 节里对 `GPU` 一行的用法；「GPU 由 RHI 未报告」的措辞也需重写 |
| F03 | 百分比与「前 N 项占统计总权重」公式错误 | 影响第 8.2 节排行里所有百分比 |
| F04 | 静态网格的 LOD 链末尾追加了假的 0 | 只影响第 9.3 节静态网格的 LOD 显示，骨骼网格不受影响 |

第 10.8 节记录的「`Game` 与 `平均` 互相矛盾」与 F01 同源。

## 12. 未验证

按用户全局规则（默认不主动测试），本项**只确认编译通过**：

- `FPSGAME Win64 Development`
- `FPSGAMEEditor Win64 Development`

**未验证**：页签显示是否正常、数值是否与 `stat unit` 对得上、排行的权重是否合理、
刷新开销是否可接受。这些需要用户现场看。

若数值与 `stat unit` 对不上，优先查第 2.1 节的变量来源；
若排行结果反直觉，先调 `ShadowWeight` / `DistanceFalloffMeters`（在
`UFPSPerformanceMetricsSubsystem` 上是 public 字段，可直接改）。