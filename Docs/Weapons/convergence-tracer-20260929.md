# 汇聚弹曳光：加粗、纯白、螺旋环绕、0.5 秒白色光柱拖尾

2026-09-29 为附魔「汇聚」影响的狙击步枪（当前只有 SVD）单独做的弹道表现层：
**加粗**、**轨迹转白**、**螺旋环绕弹道**，以及**沿整条弹道铺开、命中后留 0.5 秒再淡出的白色光柱**。

只作用于带汇聚附魔的那一发；普通曳光一个字节都没变。数值、伤害、命中判定、弹速、节流规则全部不动。

关联：[附魔卷轴「汇聚」](../Combat/enchant-convergence-20260929.md)、
[Gunplay 与 Niagara 验收](../../skills/ue5-weapon-workflow/references/gunplay-vfx.md)、
[曳光升级方案](tracer-upgrade-plan-20260921.md)。

## 四层表现

| 层 | 普通曳光 | 汇聚弹 |
| --- | --- | --- |
| 核心段 | 4 px 基准、最小 1.6 cm、上限 28 cm（镜内 12 cm） | 同上**整体 ×2**（像素基准、最小值、世界上限一起乘） |
| 颜色 | `1.0,0.30,0.03` 暖橙 | `1,1,1` 纯白 |
| 亮度 | `Emission 2.6` | `Emission 1.8`（白到一定程度就裁白，调高只会更糊） |
| 光晕 | 外发光 ×2.8 / 0.55 | 外发光再 **×1.2**，同样转白 |
| 螺旋层 | 无 | 贴着弹道的螺旋管：**20 圈 / 半径 12 cm / 管粗 3 cm / 自转 540°/s** |
| 光柱拖尾 | 无 | 出膛点→弹头的**整条弹道**发光，宽 ×2.5、`Emission 0.55`，命中后留 **0.5 s** 逐步淡出 |
| 随弹光 | 橙色 220 lm | 转白并 **×1.3** 亮度 |

"整匣聚合"的手感来自这四层叠加：一发打出去是一条粗白的光柱，外面绕着一圈自转的螺旋，
身后沿着整条弹道拖出一道柔和的白光，命中后先收螺旋、再收光柱。

## 白色光柱拖尾（0.5 秒）

用户要的是"弹道上的白色光柱，作为拖尾留 0.5 秒然后逐步淡出消失，线条感不要太强、自然一些"。
落实成四条：

1. **铺满整条弹道，不设上限**。光柱从出膛点长到弹头：弹丸飞多远，柱子就铺多长。
   **实测 SVD 的 `TraceDistance` 是 100000 cm（1000 m）**——不是有效射程 300 m，
   代码里是 `TraceDistance = max(Defaults->TraceDistance, EffectiveRangeCM×3)`，
   所以"一条 1 km 的光柱"是常态，几何与亮度都必须按这个量级设计（见下节）。
2. **出膛点不用额外存状态**。`Head - Direction × TraveledCM` 就是它：直射弹方向固定、
   `TraveledCM` 逐帧累加（命中回收时 `AcquireTracer` 归零），所以这个式子是精确的，
   弹道与瞬发两条路径都成立。
3. **它比曳光段活得久**。曳光段本体依旧 0.12 s 淡完并隐藏，光柱走自己的一条时间线：
   `fps.Tracer.Trail.LingerSeconds`（默认 0.5 s）。所以汇聚段的池格子会一直占到光柱淡完为止
   （释放阈值取两者较大值），中途曳光段/光晕/螺旋先隐藏，只剩光柱继续淡。
   命中瞬间的观感就是"螺旋先收、光柱后收"。
4. **往"宽而暗"做，不做硬管**。宽度取核心段的 ×2.8、自发光 0.9（核心是 1.8），
   再叠一条 `Pow(t, 1.5)` 的缓出曲线——先快速暗下去，再拖一条很淡的尾巴，
   比线性淡出自然。想更硬就把 `fps.Tracer.Trail.Width` 调小、`Emission` 调高。

### 亮度必须重映射：材质是按比例衰减的（首版看不见光柱的真正原因）

`TracerVisibleV13.hlsl` 的沿轴亮度是**比例**函数，不是世界尺度函数：

```hlsl
float along = saturate(LocalPosition.z * 0.01 + 0.5);  // 0 = 尾端, 1 = 弹头端
float taper = smoothstep(0.03, 0.62, along);           // 尾端渐亮
```

也就是说**引擎圆柱局部 z ∈ [-50, +19] 这一段（along < 0.62）是渐亮甚至全透明的**。
照引擎圆柱直接铺满整条弹道时，亮区就跟着长度按比例跑掉了。实测日志：
一次 SVD 汇聚射击 `traveled=100000cm`（1000 m），于是

- 最靠近玩家的**前 30 m 完全不透明为 0**（along < 0.03）；
- 前 620 m 都到不了满亮（along 0.03→0.62）；而真正占屏幕像素的恰恰就是这一段；
- 满亮段在 620–1000 m 处，那里已经细到不足 1 像素。

光柱一直在画（`TRACER_CONVERGED close` 里 `trail=100000cm` 说明组件当时可见），
但亮度全给了看不见的远端——这就是"没有看到有尾的弹道轨迹"。

**修法**：光柱不再用引擎圆柱，改为 `BuildTrailColumn()` 自建一段**只覆盖亮度平台**
（局部 z ∈ [13, 50] → along 0.63→1.0，taper 恒为 1）的圆柱，长度完全交给实例 Z 缩放：

- 局部 z 跨度 37 个单位映射到整条弹道 → `ScaleZ = 长度 / 37`；
- 组件原点沿弹道退回 `TrailLocalNear × ScaleZ`，亮段起点才落在枪口；
- XY 缩放把局部半径 50 映射成世界宽度的一半 → `ScaleXY = 宽度 / 100`；
- 几何与弹道长度无关，所以**只生成一次**，逐帧只改变换（渲染器照旧拿到真实速度）；
- 直圆柱的截面环在 XY 平面内，不会被 Z 缩放拉扁（螺旋管会，因为它的环随螺旋斜率倾斜）。

改完之后整条 1 km 弹道都在 78%–100% 亮度上（枪口端 78%，弹头端 100%），
近场终于有像素也有亮度。另加 `fps.Tracer.Trail.MaxLengthCM`（默认 0 = 整条弹道）作为可选的限长开关。

### 宽度必须有世界上限（首版没看见光柱的第二个原因）

光柱是**唯一一条从枪口起就贴着视线轴的元件**：核心段永远跟在弹头后面（离玩家很远），
光柱却从枪口一路铺到弹头。核心段的像素宽度在远距离会被 28/12 cm 的世界上限接住，
再乘宽度倍率就是 **1.5 m 粗的管子**——它的起始端面离眼睛只有 ~70 cm，
那不是"光柱"，是一个糊在眼前的白色大盘子（也正好是最不"自然"的样子）。

所以追加 `fps.Tracer.Trail.MaxWidthCM`（默认 **40 cm**）作为硬上限：
`TrailWidth = min(核心直径 × Width, MaxWidthCM)`。这个上限同时保证：
- 近端端面的角尺寸可控（40 cm 在 70 cm 处约 32°，是画面下缘的一根柱，不是满屏白）；
- 光柱不再是"贴脸的光墙"，读起来像一道从枪口射出去的光。

另外首版 `Emission` 0.55 在明亮的白色核心旁边基本看不出来，提到 **0.9**。

## 排查：怎么确认这条链路真的在跑

链路只在"带汇聚附魔的狙击枪开火"时才成立，所以怀疑没生效时先看日志。
两个诊断开关默认开着，事件很稀（一次打空弹匣 + 4.6 s 换弹），噪音可忽略：

| 开关 | 日志行 | 说明 |
| --- | --- | --- |
| `fps.Weapon.ConvergenceDiag` | `CONVERGENCE_SHOT rounds=%d scale=%.3f damage=%.1f mag_left=%d` | **有这行 = 附魔生效**（`rounds` 应为整匣发数）；没有 = 手上那把枪没带汇聚 |
| `fps.Tracer.Diag` | `TRACER_CONVERGED open round=%d seg=%.0fcm trail=%d spiral=%d` | 有这行 = 曳光层收到了汇聚标记（`trail`/`spiral` 是两层开关的当前值） |
| `fps.Tracer.Diag` | `TRACER_CONVERGED close round=%d held=%.2fs traveled=%.0fcm trail=%.0fcm` | 收段：`held` 应约等于 `Trail.LingerSeconds`（默认 0.5 s），`traveled` 是这条弹道总长 |

排查顺序：先看 `CONVERGENCE_SHOT`（附魔是否生效）→ 再看 `TRACER_CONVERGED open`
（标记是否传到曳光层）→ 最后看 `close` 的 `held`（0.5 s 停留是否成立）。

## 螺旋几何为什么这样写

**先说圈数**：可见曳光段长 800–1800 cm，而螺旋半径只有 12 cm。按"3 圈"铺满 800 cm，
每圈要吃 267 cm——螺距远大于圈周长（75 cm），看起来只是一条缓慢扭转的直线，不是"环绕"。
所以默认改成 **20 圈**（800 cm 段上螺距 40 cm，1800 cm 满段上 90 cm），
`fps.Tracer.Converged.SpiralTurns` 可实时改（改动会重建几何）。

段数由圈数推导（每圈 16 段、上限 512 段、管截面 10 边），20 圈约 5k 三角形；
几何只生成一次，逐帧不碰顶点。

曳光材质 `M_BallisticTracerVisibleV13` 是**按引擎圆柱的局部坐标写死**的
（源 `SourceAssets/GunplayVFX20260914/TracerVisibleV13.hlsl`）：它直接读 `LocalPosition.z`
（局部 z ∈ [-50,50] 映射成 0→1 的沿轴位置）和 `LocalPosition.xy`（半径 50 映射成 0→1），
再用 `NormalWS` 做侧面衰减、用 |z| 判断端盖。

所以螺旋管**必须落在同一局部口径内**，否则沿轴的头尾渐变、端盖和侧面衰减全都会错位：

- 局部螺旋半径固定 **20**（材质径向量的中段），世界螺旋半径靠实例 XY 缩放映射：
  `ScaleXY = 世界半径 / 20`。
- 局部 z 仍取 ±50，实例 Z 缩放 = `段长 / 100`，与核心段同一套算法。
- 管半径按同一比例反推：`局部管半径 = 世界管粗 / 2 / ScaleXY`。
- **法线必须自己生成**：材质用 `NormalWS` 决定侧面 alpha，缺法线会只剩 22% 的基础透明度。
  生成方式与 `FPSHolyLightEffect.cpp` 的 `Column()` 一致（`EnableAttributes` +
  `PrimaryNormals()->AppendElement` + `SetTriangle`），UV 顺带补上。

几何只在**参数变化**时重建（`SpiralMeshBuilds` 计数器可验证），逐帧只改世界变换与自转，
所以渲染器拿到的仍是真实速度——这是 2026-09-21 曳光合同要求的，换成逐帧重建顶点会重新引入 TSR 残影。

自转取世界时间的纯函数（`fmod(Now × 540°/s + RoundId × 37°, 360°)`）：不需要逐段状态，
命中后的停留期间也照旧旋转（曳光段自己 0.12 s 淡完即隐藏）。

## 实现落点

| 位置 | 改动 |
| --- | --- |
| `FPSBallisticsComponent.h/.cpp` | `FFPSFlyingRound::bConverged`；`Launch(...,bool bConverged=false)` 尾部参数；传给 `OnTracerSegment` |
| `FPSWeaponFXComponent.h/.cpp` | `FFPSWeaponFXTracer::bConverged/SpiralMesh/SpiralMaterial/SpiralBuilt*/TrailMesh/TrailMaterial`；`EnsureSpiral()`；`EnsureTrail()`；`BuildSpiralTube()`；`ApplyTracerTransform` 的宽度/颜色/光晕/螺旋/光柱分支；释放阈值与随弹光分支 |
| `FPSGAMECharacter.cpp` | 弹道与命中两条曳光调用各带上 `ConvergenceParams.Enabled` |

开关与参数全部走实时控制台变量，便于不改代码定观感：

| CVar | 默认 | 说明 |
| --- | --- | --- |
| `fps.Tracer.Converged.Width` | 2 | 核心宽度倍率（同比放大最小直径与世界上限） |
| `fps.Tracer.Converged.Tint` | `1.0,1.0,1.0` | 颜色，默认纯白 |
| `fps.Tracer.Converged.Emission` | 1.8 | 自发光 |
| `fps.Tracer.Converged.HaloScale` | 1.2 | 光晕额外加宽倍率 |
| `fps.Tracer.Converged.Spiral` | 1 | 螺旋层总开关（0 = 只保留加粗与白色） |
| `fps.Tracer.Converged.SpiralTurns` | 20 | 圈数（改动会重建几何） |
| `fps.Tracer.Converged.SpiralRadiusCM` | 12 | 世界螺旋半径 |
| `fps.Tracer.Converged.SpiralThicknessCM` | 3 | 世界管粗 |
| `fps.Tracer.Converged.SpiralEmission` | 2 | 螺旋自发光（0 等于关闭该层） |
| `fps.Tracer.Converged.SpiralSpinDeg` | 540 | 自转角速度（0 = 静止螺旋） |
| `fps.Tracer.Converged.LightScale` | 1.3 | 随弹光额外亮度倍率 |
| `fps.Tracer.Trail` | 1 | 白色光柱拖尾总开关（0 = 完全不画） |
| `fps.Tracer.Trail.LingerSeconds` | 0.5 | 命中后光柱停留秒数，然后淡出（0 = 跟着曳光段一起消失） |
| `fps.Tracer.Trail.Width` | 2.8 | 光柱宽度倍率（相对汇聚核心段） |
| `fps.Tracer.Trail.MaxWidthCM` | 40 | 光柱宽度硬上限（cm）；防止近端端面变成满屏白盘 |
| `fps.Tracer.Trail.MaxLengthCM` | 0 | 可选限长（cm）；0 = 整条弹道，非 0 只保留最后一段 |
| `fps.Tracer.Trail.Emission` | 0.9 | 光柱自发光；**越低越柔**，调高就会变成硬亮管 |
| `fps.Tracer.Trail.FadePower` | 1.5 | 淡出指数，>1 表示先暗下去、再拖一条淡尾 |

## 保持不变的合同

- **一条光段认领一颗子弹**：螺旋与光柱都挂在段上，不是新的段；`TracerSegments`、
  `ExpiredTracerSegments`、`GetActiveTracerCount()` 的语义都没变
  （"活动段数 = 在飞子弹数 ÷ 每 N 发"、"停火后归零"的断言照旧成立）。
  `BallisticPresentationAudit` 的 `PeakTracers<=8` 与"没有累积拖尾"断言用的是 M4A1，
  不产生汇聚段，因此逐字照旧通过。
- **池与预算**：螺旋与光柱组件挂在 `FFPSWeaponFXTracer` 上，随段一起 `ReleaseTracer` 隐藏；
  只有汇聚段才会创建它们。SVD 一次射击打空弹匣后要换弹 4.6 s，同时最多一条汇聚段在飞，
  所以两层的实际占用是"1 个 DynamicMesh 组件 + 2 个 StaticMesh 组件 + 3 个 MID"。
- **空闲不耗**：无曳光时段落被回收，两个组件随段隐藏；组件 Tick 仍由既有的
  "有段才开"逻辑控制。
- **不写玩法**：不碰伤害、命中、弹速、散布、后坐力与射程；`ApplyTracerTransform` 仍是纯表现。

## 新增诊断计数

| 计数 | 含义 |
| --- | --- |
| `ConvergedTracerSegments` | 开过的汇聚段总数 |
| `SpiralMeshBuilds` | 螺旋几何重建次数；逐帧重建会让它暴涨，是"只在参数变化时重建"的验证点 |

## 验证

按用户规则**未运行**编辑器、PIE、截图或验收用例；实际画面与观感由用户确认。

- 编译并链接：`FPSGAMEEditor Win64 Development` → `Result: Succeeded`
  （`build-20260929-212017.log`、`build-20260929-220302.log`、`build-20260929-222215.log`，均 `BUILD OK`）。
  光柱那次时间戳链：源 `22:02:53` → obj `22:03:25` → `UnrealEditor-FPSGAME.dll` `22:03:34`；
  可见性修正 + 诊断那次：源 `22:21:11` → DLL `22:22:35`。
- 产物自检：DLL 内（UTF-16）可查到 `fps.Tracer.Converged.*`、`fps.Tracer.Trail.*`
  （含 `MaxWidthCM`）、`fps.Tracer.Diag`、`fps.Weapon.ConvergenceDiag`，以及三条诊断日志格式串
  和 `EnsureSpiral`、`EnsureTrail` 符号。
- **用户首轮反馈"没看到有尾的弹道轨迹"的排查结论**：`Saved/Logs` 里那次测试会话是
  22:10:24–22:16:09（在 22:03:34 的新 DLL 之后，所以跑的确实是含光柱的版本），
  会话日志内**没有任何错误、断言或 ensures**；当时代码一句话都不打，所以先补了诊断日志。
- **用户第二次实测（22:40:49，含诊断的那版）**，日志三行齐全，链路完全打通：

  ```
  CONVERGENCE_SHOT rounds=20 scale=15.000 damage=2550.0 mag_left=0
  TRACER_CONVERGED open round=145 seg=537cm trail=1 spiral=1
  TRACER_CONVERGED close round=145 held=0.67s traveled=100000cm trail=100000cm
  ```

  结论：附魔生效（整匣 20 发、倍率 15、伤害 2550）、标记传到曳光层、光柱组件当时**可见**
  且长度 1000 m、停留时长生效（`held=0.67s` 是那一帧的帧长偏大导致的过冲，阈值仍是 0.5 s）。
  看不见的原因是**亮度按比例衰减**（上节），与链路无关——这是靠日志数字定位出来的，
  不是猜的。
- 亮度重映射那次构建：源 `22:44:23` → obj `22:47:33` → DLL `22:49:24`，`BUILD OK`。
  中途一次构建失败来自**别的会话正在编辑的 `UI/StatusEffectsComponent.cpp`**（语法错误），
  与本改动无关，等其作者 22:49:04 修好后重跑即通过；未改动他人文件。
- 首轮编译修过一个真实错误：`SpiralTriangle` 里 `FIndex3i` 未加 `UE::Geometry::` 限定
  （文件作用域的辅助函数没有 `using namespace UE::Geometry`）。
- 中途一次构建失败来自**别的会话正在编辑的 `ColdSteelExpHUD.cpp`**（`FGeometry::GetScale`），
  与本改动无关，等其作者修好后重跑即通过；未改动他人文件。
- 几何自检（未运行，留给实机）：`SpiralMeshBuilds` 应等于"改过几次几何参数"而不是帧数；
  三条 CVar 通路（宽度/颜色/螺旋开关）应当对**已在飞**的段立即生效。
- 材质口径风险：螺旋管用的是曳光材质本身，若实机发现螺旋过暗或过曝，先调
  `fps.Tracer.Converged.SpiralEmission`，再考虑给螺旋单独做材质；材质源与生成器在
  `SourceAssets/GunplayVFX20260914/` 与 `Tools/AssetPipeline/build_tracer_v13.py`。
- 已知取舍：螺旋管与核心段共用同一套实例缩放 `(XY, XY, 段长/100)`，段长 800–1800 cm 而
  螺旋半径只有 12 cm，所以管截面沿弹道方向被拉长（约 3×），读数上像被速度拖出的光带。
  要消掉它只能按段长逐帧重建几何，那会破坏"逐帧只改变换、渲染器拿真实速度"的合同，不划算。