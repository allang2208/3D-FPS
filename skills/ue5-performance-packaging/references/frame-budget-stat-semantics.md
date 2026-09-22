# UE5 帧预算统计的正确读法（引擎源码核对，2026-09-22）

本文件只记录**逐行核对过本机 UE 5.8 引擎源码**的口径与陷阱，不含未验证的实测结论。
凡标注「源码核对」的条目都可直接引用；标注「待验证」的不要当结论用。

## 1. 线程耗时的两组变量语义不同（源码核对）

`Engine/Source/Runtime/RenderCore/Public/RenderTimer.h`：

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

- `...Time` **不含空闲**，是纯计算量。
- `...TimeCriticalPath` **含依赖等待**，是跨度。
- 因此 `GRenderThreadTimeCriticalPath` 远大于 `GRenderThreadTime` 时，
  只能说明**渲染线程在等**，不能据此判定 GPU 受限 —— 等待对象可能是更慢的游戏线程。
- 严禁把 Game 与 Draw 相加：两者在时间上重叠。

**错误示范（本次真实发生）**：看到 `Draw 自身 4.69 ms` 而 `Draw 关键路径 43.58 ms`，
就断定「差出来的 38.9 ms 是 GPU 阻塞」。这是误读关键路径的含义。

## 2. `GGameThreadTime` 是帧间隔减空闲，不是「游戏线程干了多久」（源码核对）

`Engine/Source/Runtime/Engine/Private/UnrealClient.cpp` 的 `FViewport::Draw` 开头：

```cpp
uint32 CurrentTime = FPlatformTime::Cycles();
const uint32 ThreadTime = CurrentTime - Lastimestamp;          // 两次 Draw 的间隔
GGameThreadTime     = (ThreadTime > GameThread.Waits) ? (ThreadTime - GameThread.Waits) : ThreadTime;   // L1844
GGameThreadWaitTime = GameThread.Waits;                        // L1845
```

`Lastimestamp` 在**同一次 Draw 的结尾**更新（L1857），所以它测的是**帧间隔**。
推论：

- `GGameThreadTime` **不可能显著超过帧时间**。若面板上 `Game` 大于平均帧时间，那是口径/更新点
  不一致，**不要拿它做推理地基**。
- 与 `GAverageMS` 比较时注意后者是 EMA（`UnrealEngine.cpp:824-829`，
  `GAverageMS = GAverageMS*0.9 + FrameTimeMS*0.1`，`GAverageFPS = 1000/GAverageMS`），
  平滑窗口与逐帧量不同，两者本就不该严格相等，但也不该差出 1.5 倍以上。

**正确做法**：以自洽的一组为基准（`GAverageMS` / `GAverageFPS` 互为倒数，可交叉验算：
`1000 / 平均 ms == FPS`），`Game` / `Draw` 只用于**趋势对比**。

## 3. 面板经 UI Tick 采样帧时间会截断长卡顿（待验证，来源为外部审查）

若采样链是 `Widget::NativeTick → 采样`，Slate 会把 delta 限制在 1/8 秒
（`SlateApplication.cpp` 的 TickTime 上限）。表现是长卡顿被**截到约 125 ms 封顶**，
所以「峰值 125.00 ms」这种整齐的数字往往不是真实停顿长度。

结论：**UI 驱动的采集不能作为卡顿长度的依据**。要真实长帧，
在固定引擎帧边界用单调墙钟记录，并记录 FrameId / 时间戳 / 是否暂停或加载。

## 4. GPU 时间不要用 `RHIGetFrameTime()`（待验证，来源为外部审查）

`RHIGetFrameTime()` 基于 RHI 帧间隔（墙钟），不是 GPU busy 时间；返回 0 也不能
解释成「显卡不上报」。引擎 `stat unit` 的 GPU 一行走的是
`FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(GPUIndex))`。
两者语义不同，**不要混用，也不要给墙钟量贴 GPU 执行耗时的标签**。

## 5. 逐组件耗时与逐图元 GPU 耗时都拿不到（源码核对）

- `FTickTaskLevel` 定义在 `TickTaskManager.cpp` 内部，`ULevel::TickTaskLevel` 私有
  → **没有公开的逐组件 tick 计时钩子**。
- MSM（Material Scene Mapping）不导出逐图元 GPU 耗时。
- 因此任何「某组件花了 X 毫秒」的界面数字都是编造的。
  可替代：给出**加权相对分**并明确标注它不是毫秒；或统计**昂贵的 setter 调用次数**。

## 6. 计数比计时更可得的替代手段（本次采用）

引擎不提供逐组件计时，但**每帧调用了多少次昂贵 setter** 是能精确数的，而且它直接
对应游戏线程开销：

| setter | 代价 |
| --- | --- |
| `SetOwnerNoSee` / `SetOnlyOwnerSee` / `SetCastShadow` | 置脏图元渲染状态（render state recreate）+ 触发组件重注册（重入阴影场景） |

**做法**：在这些 setter 的调用点加守卫（`if (值 != 目标值)`）并在真正发生变化时 `++` 计数，
面板显示**每秒速率**。速率才是关键 —— 每帧 1 次与每帧 60 次是完全不同的病。
稳态下该计数应接近 0；持续几十次/秒即说明守卫失效、脚本在持续 churn 渲染状态。

同理可数的、与装备无关的固定开销：
`EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones` 的网格数
（该选项**每帧强制求值骨骼变换，即使网格不可见**），配合总骨骼数可判断骨骼求值规模。

## 7. 测量纪律（本次两次假设被推翻后的硬性结论）

- **同一构建、同一设置，两次相隔两分钟的测量可以差 3 倍**（35.56 ms vs 12.41 ms）。
  在这个量级的噪声下，单次 A/B 结论无效。
- A/B 必须：关掉编辑器、关掉串流/虚拟显示层、同一地点静止、跑 2–3 次取中位数。
- **「换装备后症状不变」是极高价值的排除证据** —— 它一次性否掉整条与装备相关的假设链。
  遇到它要立刻把排查面收敛到「不随该变量变化的东西」上，而不是继续细究装备。

## 8. 本项目专用运行时开关

| CVar | 作用 |
| --- | --- |
| `fps.body.WorldBody` | 世界身体副本总开关 |
| `fps.body.WorldBodyShadow` | 世界身体副本及其世界装备副本是否投影（`0` 关闭）。第一人称相机子件本就 `bCastShadow=false`，只有世界副本在付阴影深度 pass 的钱 |

注意 `SetCastHiddenShadow`/`bCastHiddenShadow` 的引擎判定是
`bCastHiddenShadow || !IsVisible()`（`PrimitiveSceneProxy.cpp`）——
这是**引擎支持的合法路径**，不是 bug；但配合 `bCastHiddenShadow` 时**不可见网格仍进阴影场景**，
所以要么让它跟随开关，要么明确接受这份开销。