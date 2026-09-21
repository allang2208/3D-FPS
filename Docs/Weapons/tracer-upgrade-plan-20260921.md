# 曳光弹表现升级方案 · 2026-09-21

用户反馈：开枪后曳光弹的表现不好，且移动时有明显残留拖影。

本文只做**现状核对与方案设计**：未改代码、未改资产、未启动游戏、未做画面验收。所有"看起来如何"的结论都标注了来源（代码事实／推断），最终观感由用户实测判定。

## 1. 现状（可核对的实现事实）

| 环节 | 位置 | 现状 |
| --- | --- | --- |
| 发射 | `FPSBallisticsComponent::TickComponent` (L28-60) | 每帧对每颗在飞子弹算 `Distance = Speed × Δt`，线扫后调 `OnTracerSegment(Start, End)`；`Start`/`End` 是**本帧**的飞行段，不是枪口到子弹 |
| 生成 | `FPSWeaponFXComponent::OnTracerSegment` (L209-237) | 从 **64 槽通用池**取一个 `UStaticMeshComponent`（引擎 100 cm 圆柱），`Size=(Diameter, Diameter, Length)`；位置 `= End − 方向×Length/2`，即贴在子弹**尾部** |
| 长度 | 同上 L213 | `Length = min(|End−Start|, 180 cm)` —— **等于本帧飞行距离**，随帧率线性变化 |
| 直径 | 同上 L222-230 | `clamp(PixelWidth×1.1, 0.8, ADS?2.5:5.0) cm`，目标约 **1.1 屏幕像素**（V12 定的口径） |
| 寿命 | `TickComponent` 回收段 L592-593 | `Lifetime=1`；下一帧 `BirthFrame != GFrameCounter` → `Release()` → `SetVisibility(false)`。**只亮一帧，没有历史** |
| 材质 | `M_BallisticTracerVisibleV12` + `SourceAssets/GunplayVFX20260914/TracerVisibleV12.hlsl` | 侧面朝向衰减 + 两端径向发光；`Tint=(1,.63,.18)`、`Emission=14`、`DepthFade=1.0`、**已开 `ResponsiveAA`**（`build_gunplay_visibility_v12.py` L91-93） |
| 渲染环境 | `Config/DefaultEngine.ini`、`Saved/Config/WindowsEditor/GameUserSettings.ini` | 未写 `r.AntiAliasingMethod`；`sg.AntiAliasingQuality=3` → **TSR**；`r.Velocity.TemporalResponsiveness.Supported=1` 已开；未覆盖 motion blur |

现有验收合同（`BallisticPresentationAudit.cpp`），改方案时必须一起看：

- L112 真实射击必须产出光段；
- L234-240 侧向移动连射时**活跃光段 ≤ 2**、上一帧光段必须已回收（"no accumulated trails"）；
- L246 停火后活跃光段归零。

## 2. 根因

### R1 残留拖影 —— 一帧生命 + 极亮 + 时域历史（主因，与"移动时"吻合）

曳光是"亮一帧就消失"的物体，而当前 AA 是 TSR（时域重建，会复用上一帧历史）：

1. 第 N 帧光段在位置 P 留下颜色，写进 TSR 历史；
2. 第 N+1 帧该物体已经 `SetVisibility(false)`，那个位置只剩下**背景自己的速度**（静态墙面≈0），历史里的亮样本没有"物体已离开"的信息，于是被连续若干帧继续重投影 → **亮斑残留**；
3. 玩家移动时，屏幕整体历史被位移/重投影打散，这个不跟随运动的亮斑反而更明显 —— 与"移动时有明显残留拖影"一致；
4. 加重因素：池组件每帧被**重新指派**到不同的光段位置（还可能被抛壳/烟占用），它记录的"上一帧变换"与当前光段毫无关系，速度向量本来就是错的；`Emission=14` 又把这个错误样本的强度拉到很高。

> 这是**推断**，不是实测结论。第 5.1 节给了用户 1 条命令就能判定的诊断（切 FXAA 看残影是否消失）。
> 注意 V12 已经开了材质的 `ResponsiveAA`，但仍出现拖影，说明该属性不足以处理"物体消失、历史还在"这一类残留；项目在旋风技能上改用 `TemporalResponsivenessOutput` 正是针对同一类问题（`Docs/Skills/whirlwind-migration-20260920.md`、`SourceAssets/Whirlwind20260920/WindupV3/make_temporal_materials.py` L65）。

### R2 光段断续、且随帧率变形

`Length = min(Speed×Δt, 180)` 让"画出来的段"永远只有本帧飞行距离，且有 180 cm 硬上限。实测口径下的段长/空隙（cm）：

| 武器 | 弹速 | 30 fps | 60 fps | 120 fps | 144 fps |
| --- | --- | --- | --- | --- | --- |
| M4A1 / AKM / QBZ-191 / A762 / PKM | 90 m/s | 180 / **空 120** | 150 / 0 | 75 / 0 | 62 / 0 |
| M16A2 | 95 m/s | 180 / **空 137** | 158 / 0 | 79 / 0 | 66 / 0 |
| ASH-12 | 78 m/s | 180 / **空 80** | 130 / 0 | 65 / 0 | 54 / 0 |
| M1911 | 253 m/s | 180 / **空 663** | 180 / **空 242** | 180 / **空 31** | 176 / 0 |
| DW715 | 420 m/s | 180 / **空 1220** | 180 / **空 520** | 180 / **空 170** | 180 / **空 112** |

（格式：本帧画出的段长 / 未画出的空隙。速度取自目录 `base.bullet_speed`。）

- 30 fps 下**每把枪都是虚线**；60 fps 下两把手枪断成点；DW715 在 144 fps 仍有 112 cm 空隙；
- 同一把枪在不同帧率下段长能差 3 倍（54 cm ↔ 180 cm），"观感"不稳定；
- 光段只画**本帧**那一小段（贴子弹尾部），与枪口之间没有任何连线；屏幕上任何时刻只有一段，所以看不到"从枪口拉出一条光"的连续感，只有一节节跳动的亮棒。

### R3 亚像素细线 + 高自发光

目标宽度 1.1 像素、`Emission=14`：细亮线在 TSR 下本来就容易闪、容易被 bloom 涂成一片，也让 R1 的残影更刺眼。圆柱被非等比缩放到 `0.008 × 0.008 × 1.8`（约 225:1），细长管没有可读的收束形态。

### R4 每发都画，没有"曳光弹"节奏

代码对**每一颗**子弹都生成光段。真枪的曳光弹是每 3–5 发一颗；现在是连续光绳，连射时既有 R1 的叠加残影，也读不出弹道节奏。

## 3. 升级方案（分阶段，P0 先做）

### P0 消除残留拖影

| 编号 | 做法 | 代价 / 说明 |
| --- | --- | --- |
| P0-d | **先诊断**：用户现场把 `r.AntiAliasingMethod` 切到 `1`（FXAA）再打一梭 | 无改动。残影消失 → 确认是时域残留，直接做 P0-a/P0-b；残影仍在 → 改查几何与池复用（把结论回填本文） |
| P0-a | 曳光材质输出 **`TemporalResponsiveness`=1**（拒绝旧历史），做成 `M_BallisticTracerVisibleV13` | 复用旋风先例脚本；开关 `r.Velocity.TemporalResponsiveness.Supported=1` 已开。风险：完全拒绝历史可能带来细线边缘轻微闪烁（旋风案已记录同类取舍），需要用户拍板 |
| P0-b | 曳光改成**常驻条**：每颗子弹独占一个组件，逐帧**原位更新**变换，而不是每帧换池槽位 | 让速度向量真实（90 m/s），TSR 按真实运动重投影而不是留幽灵；同时是 P1 的前提。**保持"每颗子弹一条"**，所以 L239-240 的"活跃段 ≤ 2"合同不变 |
| P0-c | `Emission` 14 → **6–9**，宽度抬到 1.6–2.0 px 的核心 + 更宽柔光晕 | 残影强度与亮度同阶下降（顺带解决 R3）；亮度靠宽度和 bloom 补回 |

推荐组合：**P0-d → P0-b + P0-a → P0-c 调观感**。P0-b 是"结构性正确"，P0-a 把物体真正消失（命中/到期）那一帧的历史也清掉，两者互补。

### P1 连续、与帧率无关的光段

- 段长改为**按时间窗**而不是按帧：`TrailSeconds`（建议 0.05 s，90 m/s → 450 cm）或**固定物理长度**（建议 250 cm），并取 `max(本帧飞行距离, TrailLength)` → 相邻两帧的光段**必然重叠**，任意帧率都不留缝（消灭 L"空隙"列）。
- 锚定：光段始终是「子弹当前位置往回 TrailLength」的线段，首帧从枪口开始 → 视觉上是枪口拉出的连续光条。
- 保留"每颗子弹一条段"，因此活跃段数 = 在飞子弹数，`BallisticPresentationAudit` 的段数断言不需要放宽。
- 掉帧补偿帧（`Distance<=0`）不分段，长条长度仍然连续。

### P2 形态与画质

- **收束**：HLSL 里已有 `along` 曲线，把头部提亮、尾部渐隐（前重后轻 + 长度方向 taper），端盖发光只在朝向射手一侧保留一点，去掉"发光棒"感。
- **分档**：给一张小表（手枪短细、PKM/ASH 粗长），先做 2–3 档，不做每枪精细数值。
- **池**：曳光单独小池，避免和抛壳/烟共用组件时 `SetStaticMesh` 切换（项目已开 `r.PSOPrecaching`，池复用换网格正是冷 PSO 的来源之一）。

### P3 可选（需用户拍板，默认不做）

- **曳光弹节奏**：每 N 发画一条（建议 4），从"光绳"变成可读的"点线"。代价：连射方向反馈变稀，且需要同步改 `BallisticPresentationAudit` 的段计数断言，并说明是设计变更而不是回归。
- 停火余辉、热霾、命中端短促闪光：机制上可挂现有 FX 池，建议等 P0-P2 定稿后再评估。

## 4. 边界（本轮方案不动的东西）

- 不改弹速、伤害、射程、穿透、命中判定、后坐力与任何输入逻辑 —— 只改"画什么、画多久、怎么画"。
- 保留深度遮挡（被墙挡住的光段不显示）与真实命中点截断。
- 保留"不做历史堆积"的意图：活跃光段数始终等于在飞子弹数。
- **不用 `OutputVelocity`**：本项目火球材质已记录它与 `DepthFade` 冲突（`Docs/Skills/fireball-motion-heat-20260914.md`：`Translucent material with 'Output Velocity' enabled will write to depth buffer ... cannot read from depth buffer`），而曳光材质正是用 `DepthFade` 的。
- 材质/Niagara 改动走 `Tools/AssetPipeline` 脚本 + 已运行编辑器的批次互斥；不新建并行编辑器、不结束他人编辑器。

## 5. 验证方式（由用户执行，本轮未做）

1. **R1 诊断**：`r.AntiAliasingMethod=1`（FXAA）对比 `=4`（TSR），横向移动 + 连射，看残影是否消失。
2. **残影**：站定与横向移动各打一梭，观察弹道后方是否有不跟随运动的亮斑残留。
3. **连续性**：`t.MaxFPS 30 / 60 / 144` 各打一梭，确认光段连贯、长度不再随帧率变化。
4. **遮挡与命中**：对墙、箱子、怪物打断，确认光段在墙面处截断、不穿墙、命中点准确。
5. **性能**：确认光段数量与池占用没有增加（`ExpiredTracerSegments` 仍在增长、停火后 `GetActiveTracerCount()==0`）。
6. 改段长/寿命后需同步的审计：`BallisticPresentationAudit.cpp` L112 / L234-246；材质改动按 V13 立新资产并记录到 `Docs/Weapons/`。

## 6. 待确认

1. **R1 诊断结果**：能否先跑一次 `r.AntiAliasingMethod=1` 的对比？这决定 P0 走"时域响应"还是"常驻条 + 降亮度"。
2. **取舍**：接受 `TemporalResponsiveness` 完全拒绝历史可能带来的细线边缘闪烁吗？（旋风口径是"用户自行判断取舍"。）
3. **P3 节奏**：曳光弹要不要改成每 N 发一颗？（默认仍是每发都画。）
4. **观感方向**：想要"细亮针"还是"粗暖光条"？

## 7. 工作量与建议顺序

| 阶段 | 改动面 | 预估 |
| --- | --- | --- |
| P0-d 诊断 | 无（用户一条 CVar） | 免 |
| P0-b 常驻条 | `FPSWeaponFXComponent`（曳光独占池 + 逐帧更新）、`FPSBallisticsComponent` 传参 | 小，半天内可交付 |
| P0-a 材质时域响应 | 新材质 V13 + 生成脚本（复用旋风模板） | 小 |
| P0-c 亮度/宽度 | 材质参数 + C++ 常量 | 很小 |
| P1 段长 | C++ 常量与锚定逻辑 | 小 |
| P2 形态/分档 | HLSL + 小参数表 | 中 |
| P3 节奏 | C++ 计数器 + 审计同步 | 小（但属设计变更） |

建议按 **P0-d → P0-b → P0-a → P1 → P0-c → P2** 顺序落地，每步都能单独看效果；P3 等前面定稿后再问一次。

## 8. 实施记录（2026-09-21，本轮已落地）

按 P0-b → P0-a → P1 → P0-c → P2 实施；P3（曳光弹节奏）未做，仍是每发都画。

### 8.1 曳光改「每颗子弹一条常驻光段」

| 文件 | 改动 |
| --- | --- |
| `Source/FPSGAME/Weapons/FPSBallisticsComponent.h/.cpp` | `FFPSFlyingRound` 增加稳定 `Id`（`NextRoundId++`），每帧把 `R.Id` 交给武器特效 |
| `Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp` | 新增 `FFPSWeaponFXTracer` 与独立池 `Tracers`（上限 32，不与抛壳／烟／火花共用），新增 `OnTracerSegment(RoundId,Start,End)` 重载 |

- 同一颗子弹的每次刷新都命中同一条光段（按 Id 匹配），**原位更新**同一个组件：渲染器因此拿到真实速度向量（≈弹速），TSR 按真实运动重投影，而不是在旧位置留下幽灵。
- 光段在「本帧没有被刷新」时立刻回收——子弹命中或消失后不留历史，时序与旧口径一致（最后可见帧仍是命中帧）。
- 池满时（高速弹 + 长飞行时间）回收最久未更新的一条，不会让在飞的子弹没有曳光。
- 无弹丸的瞬时段（`ProjectileSpeedCM<=0` 的射线路径）仍是一次性段，但改为 **0.05 s 淡出**，不再一帧消失。

### 8.2 段长与锚定（P1）

`Length = clamp(本帧飞行距离, 基准, 上限)`；头在子弹当前位置，尾在其后 `Length`，且不早于枪口（`TraveledCM` 约束，光段从枪口长出来）。

| 枪型 | 基准 / 上限 | 30 fps | 60 fps | 120 fps | 144 fps |
| --- | --- | --- | --- | --- | --- |
| 长枪（78–95 m/s） | 250 / 350 cm | 260–317 cm **无空隙** | 250 **无空隙** | 250 **无空隙** | 250 **无空隙** |
| M1911（253 m/s） | 150 / 300 cm | 300 空隙 543 | 300 空隙 122 | 211 无空隙 | 176 无空隙 |
| DW715（420 m/s） | 150 / 300 cm | 300 空隙 1100 | 300 空隙 400 | 300 空隙 50 | 292 无空隙 |

- 长枪在任意帧率下都不再断线，段长也不再随帧率从 62 cm 跳到 317 cm。
- 两把高速手枪弹在 ≤60 fps 仍有空隙：单条光段无法同时满足「不断线」和「不成光柱」，这是本轮**已知残留**；要彻底消除需按帧内分段，会改动审计合同。

### 8.3 亮度与宽度（P0-c）

`Emission 14 → 7.5`；目标宽度 `1.1 → 1.7` 屏幕像素；最小直径 `0.8 → 0.9 cm`。残影强度与过曝同阶下降。

### 8.4 材质 V13（P0-a + P2 形态）

- 新资产 `/Game/Weapons/GunplayFX/M_BallisticTracerVisibleV13`，由 `Tools/AssetPipeline/build_tracer_v13.py` 从 V12 复制生成，`Tools/AssetPipeline/verify_tracer_v13.py` 回读验证。
- 回读结果：`custom=1`（描述 `Gunplay V13 tapered tracer`，含 taper）、`responsive=1` 且连接到常量 **1.0**、`blend=ADDITIVE`、`responsive_aa=True`、源标记指向 V12（可安全重跑）。
- 自定义节点换用 `SourceAssets/GunplayVFX20260914/TracerVisibleV13.hlsl`：尾部渐隐、头部提亮，端盖发光按 along 加权；参数名沿用 `Tint/Emission/Opacity/Exposure`。
- C++ 引用切到 V13（`FPSWeaponFXComponent.cpp` 的 `ConstructorHelpers`）。
- 未用 `OutputVelocity`（与 `DepthFade` 冲突的既有结论）；时域响应走 `TemporalResponsivenessOutput` + `r.Velocity.TemporalResponsiveness.Supported=1`。

### 8.5 审计同步

`BallisticPresentationAudit.cpp`：`ExpiredTracerSegments` 的语义由「每帧回收计数」改为「光段回收次数」（一颗子弹一次），stage 23 的断言因此由 `>20` 改为 `>0`；`PeakTracers>0 && <=2`、停火后归零两条保持原样——新模型下活跃光段数仍等于在飞子弹数，合同不变。

### 8.6 未完成 / 未验证

- **单文件编译通过**：三个改动过的 .cpp（`FPSWeaponFXComponent.cpp`、`FPSBallisticsComponent.cpp`、`BallisticPresentationAudit.cpp`）用 `-SingleFile` 逐个编译，均 `Result: Succeeded`、退出码 0（日志 `Saved/BuildEditor/single-*-20260921-2157.log`），说明本轮代码在真实引擎头文件与工具链下可编译。
- **完整构建曾被阻塞，随后由对方修复并完成链接**：第一次尝试时 FPSGAME 编辑器在运行，`Tools/Build/Build-Editor.ps1` 按既有守卫拒绝构建；编辑器关闭后再试两次，都在同一个**他人未提交文件**上 fatal——`Source/FPSGAME/Weapons/RuneGoldMaterialCommandlet.cpp`（untracked，构建时该文件仍在被编辑）第 9 行 include `UObject/SaveLoose.h`、第 10 行 include `EditorAssetLibrary.h`，两者在本引擎/本模块都不可用（全 `Engine/Source` 下搜不到 `SaveLoose.h`）。UBT 在第一个编译动作即 `fatal error C1083`，链接未执行。
- **现状：已链接进二进制**。对方在 22:17:14 修好该文件（改为 `UObject/SavePackage.h`，编辑器专用头移入 `#if WITH_EDITOR`），22:21:48 的构建写出了 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（对应日志 `Saved/BuildEditor/build-20260921-222152.log`，`Result: Succeeded`）；本会话随后重跑 `Build-Editor.ps1` 得到 `Target is up to date`（0 个动作，`Result: Succeeded`）。DLL 时间戳晚于本轮全部源码（最晚 21:34:20），因此**本轮 C++ 已在编辑器二进制内**，重启编辑器即可生效。
- 按项目规则未修改、未移动、未删除他人文件，也未结束他人编辑器；阻塞仅在当前对话说明（不与其他会话协调）。
- **未运行、未测试、未做画面验收**（按用户规则）。R1 的 `r.AntiAliasingMethod` 对比诊断仍未做。
- 观感微调入口（2026-09-21 第二轮起改为实时 CVar）：`fps.Tracer.LengthScale`（段长倍率，1 = 步枪 600/1400 cm、手枪 300/1200 cm）、`fps.Tracer.Every`（每 N 发画一条曳光，默认 3，第 1 发必画）、`fps.Ballistics.SpeedScale`（弹速倍率，1 = 目录 `bullet_speed`）；仍属编译期常量的只剩 `WeaponFX::TracerEmission`、`TracerPixelWidth`。背景与取舍见 `Docs/Weapons/ballistic-feel-options-20260921.md`。