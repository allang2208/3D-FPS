# 天气系统代码审计（2026-09-23）

范围：`Source/FPSGAME/` 下全部天气相关 C++（FPSWeatherManager、StormCloudComponent、WeatherSurfaceComponent、WeatherViewEffectsComponent、验证器）。只读审计 + 构建通过，未做实机测试。

## 一、性能问题（按严重度排序）

### P1 高：`TrySynchronizeWithSkyClock()` 每帧全世界扫描

**位置**：`FPSWeatherManager.cpp:791-838`，在 `Tick:252` 每帧调用。

**现象**：每帧遍历所有 actor，对每个执行 `Actor->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager"))`；命中后再用 `TFieldIterator<FProperty>` 反射遍历该类的所有属性，每个属性做两次 `.Replace()`（各分配一个 FString），再用 `Contains(TEXT("SunHeight"))` 匹配。

**代价**：
- 全量 `TActorIterator`：O(世界 actor 数)，带指针追逐。丘陵地图数千 actor 时每帧可观。
- FName→FString 转换 + 子串搜索：每 actor 至少一次字符串分配。
- 反射属性遍历 + Replace 分配：找到 DayNightManager 后每帧重复。

**根因**：天空时钟是关卡静态内容——BeginPlay 已经解析过一次（`bSkyClockConnected = TrySynchronizeWithSkyClock()`），但 Tick 里每帧重新发现，而不是缓存结果。

**修复方向**：把发现的 Actor 与 FProperty 指针缓存为成员（弱引用），每帧只做"指针是否仍有效"检查；仅在失效时重扫。这是 O(N)→O(1) 的改动，风险低。

### P2 中：`UpdateSceneDayNight()` 每 0.1 s 全世界扫描 + 组件数组重建

**位置**：`FPSWeatherManager.cpp:717-789`，由 `Tick:270` 驱动，节流到 0.1 s。

**现象**：每 0.1 s 遍历所有 actor；对每个 actor 构造 `TInlineComponentArray<UStaticMeshComponent*>`（Normandy 分支）和 `TInlineComponentArray<ULightComponentBase*>`。Normandy 分支还对每个 mesh 调 `GetStaticMesh()->GetName().Contains(TEXT("SkySphere"))`——每 mesh 一次 FString 分配。

**影响**：仅 3 张无 BP 时钟的地图启用，但 10 Hz 的全量迭代在大世界上仍是固定税。灯光基线已缓存在 `SceneLightIntensities`，所以真正的问题只是迭代本身。

**修复方向**：Discover 阶段一次性收集需要驱动的灯光/SkySphere 组件到缓存数组，之后每 0.1 s 只遍历缓存，不再碰无关 actor。

### P3 中：`UStormCloudComponent::Discover()` 每 1 s 全世界扫描

**位置**：`StormCloudComponent.cpp:55-112`，由 `TickComponent:137` 以 1 s 节奏触发，且只要 tick 开着就持续运行（不依赖 Blend）。

**现象**：每秒 `TActorIterator<AActor>` 全量遍历，对每个 actor 构造 `TInlineComponentArray<UVolumetricCloudComponent*>` 和 `<ULightComponentBase*>`。风暴状态可能持续数分钟，期间每分钟约 60 次全量扫描。

**缓解因素**：Lights/SkyMeshes 的基线只在首次捕获（`!Lights.Contains` / `ContainsByPredicate`），不会每帧重置，所以没有视觉 bug；纯粹是 CPU 浪费。

**修复方向**：Discover 成功后停止周期重扫，或降到 5–10 s；云/灯光是关卡级静态对象，不需要秒级发现。

### P4 低：`UpdatePlayerFollowing()` 每帧无条件 SetActorLocation

**位置**：`FPSWeatherManager.cpp:446-454`。

**现象**：每帧 `SetActorLocation(CameraLocation + (0,0,900))`，即使相机静止也执行。SetActorLocation 走完整移动管线（更新组件变换、通知物理等）。

**修复方向**：`const FVector NewLoc = ...; if (!NewLoc.Equals(GetActorLocation())) SetActorLocation(NewLoc);`。一行守卫，零风险。

### P5 低：`fps.RainQuality 0` 并未真正停掉表面效果的工作

**位置**：`WeatherSurfaceComponent.cpp:88-181`。

**现象**：Quality==0 时 `Side=0` → `Wanted` 为空，placement trace 被跳过；但 L121-137 的主循环仍然每 0.1 s 遍历全部 16 个 patch，对每个做 `SetVisibility(false)`、两个 MID `SetScalarParameterValue`、两个 Niagara `SetFloatParameter`、Activate/Deactivate 判断。L164 还对 4 个 Drip 写 SpawnRate=0+Deactivate。也就是说"关闭"只省了射线检测，没省组件参数写入。

**另外**：`Wetness` 积分（L93）不受 Quality 门控，关质量后地面湿润度继续涨落，重新开启会看到残留水渍——可能是故意的跨档连续性，但值得确认意图。

**修复方向**：Quality==0 时在函数开头早退（先把可见性/速率清零一次，再跳过后续逻辑），或在组件层禁用 tick。

### P6 低：MPC `Wetness`/`Cloudiness` 每帧无条件写入

**位置**：`FPSWeatherManager.cpp:531-532`。

**现象**：`Cloudiness` 在非雨稳态下是常量却每帧写；`Wetness` 渐变期每帧变属必要。同文件 Lightning 已有变化守卫（L535），这两个参数却没有。

**影响**：MPC 集合参数写入是全局 uniform buffer 上传，频率 60 Hz×2 个标量。开销不大但与项目自己的守卫惯例不一致。

**修复方向**：仿照 Lightning 的写法加 `!= Published*` 守卫。

### P7 低：`AcquireWet` 的 SharedWet 池永不清理

**位置**：`WeatherViewEffectsComponent.cpp`（本次新增）。

**现象**：池按 Original 资产指针键控，同一武器反复装备不增长；但玩家持过的每种不同干材质都会永久留一个 MID，上限≈游戏内武器材质种类数（几十）。单个 MID 很小，实际不构成问题，属于"有界但无显式上限"的集合。

**处置建议**：保持现状即可；若要洁癖可在 RestoreMaterials(pawn 切换) 时清空池。

## 二、正确性观察（非 bug，但值得记录）

1. **`AdvanceGameTime()` 天空时钟分支不递增 DaySerial**（L307-311 注释明确"日序仍由同步逻辑记"）。跨午夜推进靠下一帧 `TrySynchronizeWithSkyClock` 的回绕检测补偿，存在一帧窗口；若该帧恰好 sky clock actor 失效，日序少加一天。设计自洽但脆弱，建议在该分支内直接比较 `Advanced < Units` 判回绕并 ++DaySerial。

2. **雨→晴没有 lead-out**：`RequestState(Clear)` 直接 ApplyState，EffectiveRainIntensity 渐弱但云层/雾同时散——与"先阴天后下雨"不对称。若这是刻意的（雨停无需预告），忽略本条。

3. **遮蔽判定是相机正上方单点射线**（L473-482）：宽屋檐边缘、树冠、电线会误判。技能文档已列为已知限制，不展开。

4. **切出 Storm 会丢弃排队中的雷声**（ResetLightning(true) 清 PendingThunderDelay）：A/V 配对保留是对的，但闪电闪光已发生而雷声消失的情况用户可感知。当前行为合理，仅记录。

5. **`SetWeatherState` 默认 `bDisableAutomaticSchedule=true`**：UI 漏传第二参会永久关闭自动日程直到 Resume。接口易误用，考虑改默认值或在面板侧显式传参。

## 三、做得对的地方（避免回归）

- 云层组件 setter（LayerBottomAltitude 等）引擎侧只在值变化时 MarkRenderStateDirty，项目的每帧常量写入被引擎吸收。
- 闪电补光 `ConfigureFill` 明确 `SetCastShadows(false)`、关体积散射，闪一下不会重建阴影立方体。
- 雷声双 voice 复用 + 随机不重复上一次，无 per-strike 组件创建。
- MPC Lightning 已有变化守卫；ViewEffects 武器湿润本次已加量化守卫与计数器。
- EndPlay 生命周期干净：Restore 灯光/云/天空网格、清 MPC、还原武器材质。
- 排布预算每 0.1 s 最多 2 次 placement trace，檐口探针轮转单槽位——这两处节流是教科书级的。

## 四、优先级建议

| 级别 | 项 | 改动量 | 风险 |
|---|---|---|---|
| ✅ 已修（2026-09-23） | P1 天空时钟缓存 | ~20 行 | 低 |
| ✅ 已修（2026-09-23） | P4 跟随守卫 | 1 行 | 极低 |
| ✅ 已修（2026-09-23） | P5 RainQuality 0 早退 | ~10 行 | 低 |
| 待办 | P3 Discover 降频/停止 | ~5 行 | 低 |
| 待办 | P2 UpdateSceneDayNight 缓存化 | ~30 行 | 中（涉及 3 张图灯光基线） |
| 待办 | P6/P7 | 各几行 | 极低 |

P1 是唯一每帧都付的全量扫描，其余都有节流或规模有限。若只做一件事，做 P1。

### 修复实施记录（2026-09-23，构建通过 `Saved/BuildEditor/build-20260923-135650.log`，未实机测试）

- **P1**：`TrySynchronizeWithSkyClock()` 拆成"发现 + 读取"两段。新增 `SkyClockActor`（TWeakObjectPtr）与 `SkyClockProperty`（TWeakFieldPtr<FProperty>）成员；actor 有效时每帧只做弱句柄校验和一次属性读取，反射遍历与 FString 分配只在未解析或失效后发生。行为不变：回绕判日序、Fmod、NormalizedDayTime 写入全部保留。
- **P4**：`UpdatePlayerFollowing()` 加 `NewLocation.Equals(GetActorLocation())` 守卫，相机静止时不再走移动管线。
- **P5**：`WeatherSurfaceComponent::TickComponent` 在 Quality<=0 时一次性清零池内可见性/MID/Niagara 参数后置 `bQualityOffApplied` 并返回，之后零工作；重新开启质量立即恢复。Wetness 积分保持在门控之前（跨档连续性按现状保留，如需改为关档冻结可一行调整）。
- 构建期间遇到的 `M4GunsmithVisual.cpp` C4458 报错来自另一条任务线的未提交改动（PSO1 瞄准镜），在本次构建进行中被其作者自行修正，与本审计无关。
