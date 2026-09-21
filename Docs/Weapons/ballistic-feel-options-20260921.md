# 弹道"抛射物感"诊断与曳光方案调研（2026-09-21）

用户报：曳光改造后仍有一种**抛射物（缓慢飞行物）**的观感，怀疑是自己设的弹速过慢。本文给出量化诊断、社区/开源方案调研与三个可落地预设。**本轮未运行、未测试、未做画面验收**——表里的时间是按目录数值算的，不是实测手感。

## 1. 量化：当前弹速确实落在"冷兵器"区间

`Content/ColdSteelData/gunsmith.json` 的 `base.bullet_speed` 与实测换算（`t = 距离 / 弹速`）：

| 枪 | 弹速 | 有效射程 | 25 m 用时 | 有效射程用时 | 射速 |
| --- | --- | --- | --- | --- | --- |
| `ue_m4a1` | 90 m/s | 70 m | 0.278 s | **0.778 s** | 750 发/分 |
| `ue_qbz191` | 90 m/s | 85 m | 0.278 s | 0.944 s | 667 发/分 |
| `ue_akm` / `ue_a762` | 90 m/s | 100 m | 0.278 s | 1.111 s | 600 / 900 发/分 |
| `ue_m16a2` | 95 m/s | 110 m | 0.263 s | 1.158 s | 750 发/分 |
| `ue_pkm` | 90 m/s | 150 m | 0.278 s | **1.667 s** | 600 发/分 |
| `ue_ash12` | 78 m/s | 80 m | 0.321 s | 1.026 s | 462 发/分 |
| `ue_m1911` | 253 m/s | 50 m | 0.099 s | 0.198 s | 333 发/分 |
| `ue_dan_wesson715` | 420 m/s | 65 m | 0.060 s | 0.155 s | 188 发/分 |

参照：**现代复合弓箭约 90 m/s**，弩箭约 100 m/s，音速 343 m/s，5.56 实弹约 940 m/s（70 m 只要 0.074 s）。也就是说长枪的弹丸现在**正好以箭速飞行**，"抛射物感"不是错觉而是字面成立；ASH12 甚至比箭还慢。

四个把"延迟"放大成"抛射物"的叠加因素：

1. **弹丸在空中的数量**：M4 间隔 80 ms，弹丸飞 70 m 要 778 ms → 第一发命中时，枪口已经出去了 **约 10 发**。空中挂着一串可见弹丸，是目前最强的抛射物线索。
2. **曳光是短棒而不是光带**：当前步枪段长 250–350 cm、宽 1.7 px、带头部辉光——读起来像一颗带光晕的"小飞虫"，而不是"一束光扫过"。
3. **命中反馈随弹丸到达**：impact 特效、命中判定都在弹丸抵达时才发生，所以"打中了"永远晚于扣扳机。
4. **帧率越低越像跳格**：60 fps 下每帧前进 150 cm；即便段长足够，也只有 60 个采样点。

## 2. 社区 / 开源方案调研

**A. "纯表现曳光 + hitscan 命中"（Source / UT 系，最主流）**

- Source 引擎的 [`UTIL_ParticleTracer`](https://developer.valvesoftware.com/w/index.php?title=UTIL_ParticleTracer)：伤害走 hitscan，曳光只是沿射线的装饰粒子——玩家看不到飞行过程，也就没有抛射物感。
- UT2004 的 [`TracerProjectile`](http://kos.informatik.uni-osnabrueck.de/download/utdocu/Source_utclassic/tracerprojectile.html)：引擎级"视觉专用弹丸"类，命中逻辑与表现分离。
- 可借：**把"看得见的飞行"降级为可选表现**。本项目 `FPSBallisticsComponent` 已经按帧做扫掠线检测（不穿墙），改成 hitscan 或混合判定在机制上安全。

**B. 数据驱动弹丸管理（UE5，与本项目架构最接近）**

- [`YyepPo/Data_Driven_Projectile`](https://github.com/YyepPo/Data_Driven_Projectile)：`UTickableWorldSubsystem` + struct 数组集中管理、线检测推进、Niagara 表现（1.2 版把表现换成 ISM 静态网格，正是本项目现在用的路子）。带重力下坠、Data Asset 配置弹速与视觉。
- 可借：**架构无需更换**——它的做法与本项目现有的子组件+结构体池同族；README 里值得抄的是"表现层用 ISM 批量绘制"和"每种子弹一种 Data Asset"。

**C. 发光弹丸 + 拖尾（Blueprint 演示）**

- [`droganaida/Customizable-Projectile-FX-UE5`](https://github.com/droganaida/Customizable-Projectile-FX-UE5)：发光材质 + `NS_Trail` 拖尾 + 命中贴花 + 跳弹，颜色统一参数。
- 可借：颜色/参数统一的组织方式；但它的观感恰恰是"看得见的发光弹丸"——即当前被嫌弃的那一类，不作为目标。

**D. 混合命中（Insurgency: Sandstorm 式的思路）**

- [\[Unreal\]Ballistics 实践记录](https://www.mattheuswhale.com/projects/unreal/ballistics/)：在弹道平直段用 hitscan，超出该距离才生成弹丸并计算下坠与伤害衰减，兼顾手感与真实感（多人同步）。
- 可借：**按距离分流**。本项目无重力下坠，可以直接变成"有效射程内即时命中，超出射程才飞弹丸"——中近距离立刻变成枪感，远距离保留可见飞行。

**E. 高速曳光的已知坑**

- Epic 论坛 [Need advice on how you guys make bullet tracers… problems of tracers flickering in high speeds](https://unreal2.epic-prod-us2.discourse.cloud/t/need-advice-on-how-you-guys-make-bullet-tracers-for-an-fps-game-i-have-questions-about-niagara-effects-and-problems-of-tracers-flickering-in-high-speeds/2234150)：社区共识是"每帧生成粒子"在高速下必然闪烁，需要改成沿射线的光束/拖尾或池化网格。
- 这正是本项目已经踩过的一半（每帧新建 → TSR 残影），也是**提弹速前必须先加长段长**的原因。

**F. 光带/丝带渲染实现**

- [Niagara Ribbon 拖尾做法（中文）](https://zhuanlan.zhihu.com/p/2011867887430828109)、[UE5.8 Ribbon/Mesh/Sprite 渲染器解析](https://ixueyouxi.com/2026/07/14/ue58-niagara-renderers/)：把飞行轨迹做成 ribbon 连续拖尾，天然没有"断点"问题。
- [Epic 论坛：从 line trace 生成 Niagara](https://unreal2.epic-prod-us2.discourse.cloud/t/spawn-niagara-from-line-trace/2388170/6)、[UE C++ Niagara 激光/光束套件](https://halukoral.github.io/posts/laser/)：光束沿射线生成、命中点接 impact 的 C++ 组织方式。
- 可借：若后续要"连贯拖尾"而非"分段短棒"，ribbon 是替代几何；代价是引入 Niagara 资产与 GPU 开销。

**G. 曳光稀疏化的现实依据**

- 真实弹链/弹匣通常**每 5 发装 1 发曳光弹**（[示例专利说明](https://patents.google.com/patent/US20160102936A1/en)）。稀疏化既是观感需要，也与现实一致——本项目 P3（每 N 发一条）至今未定。

## 3. 三个可落地预设

段长与弹速的覆盖判据：**每帧位移 = 弹速 × 100 / 帧率（cm）必须 ≤ 段长上限**，否则出现断点。当前上限 350 cm ⇒ 60 fps 下弹速上限约 210 m/s。

| 预设 | 弹速（长枪） | 段长（基准/上限） | 节奏 | 有效射程命中延迟 | 需要的代码工作 |
| --- | --- | --- | --- | --- | --- |
| **① 只改表现** | 不动（90） | 900 / 1400 cm | 每 2 发 | 仍 0.78 s | 只改常量 |
| **② 速度 + 表现（推荐）** | 90 → 300–350 m/s | 600 / 1400 cm | 每 3 发 | **0.20–0.23 s** | 常量 + 节奏计数 |
| **③ 即时命中 + 纯表现曳光** | 逻辑 hitscan（表现可保留飞行） | 300 / 600 cm | 每 3–5 发 | **0 s** | 判定分流 + 伤害/穿透链调整 |

- 预设②在 ≥30 fps 全程无断点：350 m/s 在 30 fps 是 1167 cm/帧 < 1400 cm 上限；60 fps 是 583 cm；144 fps 是 243 cm。段长随帧率在 6–12 m 间浮动（低帧率更长），观感是一束扫过的光而非一颗飞虫。
- 预设③最彻底：命中与 muzzle flash 同帧，"枪感"最强；表现层可继续让曳光飞行（纯装饰），代价是失去"看得见来袭弹丸"这一属性（若这一属性是玩法设计的一部分，需要先确认）。
- 任何把弹速推到 **>700 m/s** 的方案都会超出"一段覆盖一帧"的能力，那时才需要把每帧位移切成多段（原 P0-d 子分段）。

## 4. 建议

1. **先加实时 CVar 再定数值**（本项目既有习惯，如 `fps.Camera.Shake`）：一个段长倍率、一个"每 N 发一条"、一个弹速倍率。这样可以在 PIE 里两分钟内定手感，不必为每个候选值走一次编译。
2. 手感基线按预设②取（步枪 300–350 m/s、段长 600/1400 cm、每 3 发一条），预设③作为"仍然不够像枪"时的下一档。
3. 弹速属于玩法数值（会影响预判、命中延迟与"可见来袭"），改动前需要用户确认；判定分流（预设③）改动更大，单独一轮。

## 5. 实施记录（2026-09-21 第二轮，按用户选定的"CVar + 预设②"）

**目录数值**（`Content/ColdSteelData/gunsmith.json` 的 `base.bullet_speed`）：

| 枪 | 原 | 新 |
| --- | --- | --- |
| `ue_m4a1` / `ue_akm` / `ue_qbz191` / `ue_a762` | 90 | **350** |
| `ue_m16a2` | 95 | **350** |
| `ue_ash12` | 78 | **300** |
| `ue_m1911` / `ue_dan_wesson715` | 253 / 420 | 不变（已在枪感区间） |
| `ue_pkm` | 90 | 不变——该武器块仍属其他会话未提交改动，未触碰 |

**代码**：

- 段长窗口 `FPSWeaponFXComponent.cpp`：步枪 250/350 → **600/1400 cm**，手枪 150/300 → **300/1200 cm**。
- 曳光节奏：`FFPSFlyingRound` 新增 `bShowTracer`，`UFPSBallisticsComponent` 新增每武器计数器 `TracerRoundCounter`；**第 1 发必画，其后每 3 发一条**，Tick 里 `if(WeaponFX&&R.bShowTracer)`。纯表现，命中／伤害／衰减／穿透／命中特效都不读它。
- 三个实时 CVar：

| CVar | 默认 | 作用 |
| --- | --- | --- |
| `fps.Ballistics.SpeedScale` | 1.0 | 发射时乘弹速（钳制 0.05–10）；1 = 目录值。抑制器的 `bullet_speed_mult 0.85/0.8` 仍在之后生效 |
| `fps.Tracer.Every` | 3 | 每 N 发画一条曳光，≥1；1 = 每发都画 |
| `fps.Tracer.LengthScale` | 1.0 | 同时缩放段长基准与上限（钳制 0.1–5） |

- 审计合同同步：`BallisticPresentationAudit` 的 `PeakTracers>0&&PeakTracers<=2` 放宽为 `<=4`，因为"活动段数 = 在飞弹数"只在每发都画时成立，加上节奏后变成"在飞弹数 ÷ N"。

**试法**：重启编辑器后先看默认值（350 m/s、6–14 m、每 3 发一条）；要现场对比就在 PIE 控制台里改 `fps.Ballistics.SpeedScale`（例如 1 → 2.7 回到原来的 90 m/s 手感、0.5 更慢）、`fps.Tracer.Every 1`（每发都画）、`fps.Tracer.LengthScale 0.4/2`。定下来的数值再写回目录与常量。

## 6. 未验证

以上延迟与覆盖率均由目录数值推算；本轮没有运行游戏，也没有做 `t.MaxFPS`、`r.AntiAliasingMethod` 对照或任何画面验收。

编译状态：三个改动过的 TU（`FPSBallisticsComponent.cpp`、`FPSWeaponFXComponent.cpp`、`BallisticPresentationAudit.cpp`）用 `-SingleFile` 逐个编译均 `Result: Succeeded`（日志 `Saved/BuildEditor/single2-*.log`）。**完整构建与链接取决于编辑器占用**：本轮多次尝试时 FPSGAME 编辑器由其他会话持续占用，`Tools/Build/Build-Editor.ps1` 按既有守卫拒绝构建（不结束他人进程），因此链接是否完成以实际 DLL 时间戳为准——构建成功后 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 应晚于本轮全部源码。