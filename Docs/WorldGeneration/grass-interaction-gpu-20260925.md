# 草地交互 GPU 升级计划（踩踏 / 脚步反馈 / 爆炸压平）

日期：2026-09-25　最新状态：2026-09-27 用户反馈多轮更新仍未成功，已记入待办并暂停。v14 仅部分接入，不能作为完成版；详见 [暂停与发布记录](grass-paused-publication-20260927.md)。下方早期里程碑保留为历史，不覆盖最新用户结论。
替代方案背景：评估过 Fab《Dynamic Grass System》（见 `D:\FPS3D\_dgs_demo\` 归档的实测与评论快照），结论为不采购；改用自研 GPU 方案，理由见本文 §1。

## 1. 目标与约束

用纯 GPU 方案为丘陵世界（DynamicMesh 高度场地形 + PN_GrassLibrary 植被）补上三类植被反馈：

- **A 踩踏/压平视觉**：跟随玩家的 render target（RT）驱动 WPO，CPU 近零成本，兼容 Nanite 植被与 World Partition。
- **B 脚步反馈**：Niagara 粒子 + decal 轨迹，挂接现有 AutoFootstep 插件的唯一出口。
- **C 爆炸压平**：一次性径向 WPO impulse（RT 单次 stamp + 着色器波前展开），与 A 同一套技术。

硬约束：

1. **CPU 近零**：不做逐实例 transform 更新（DGS 路线的否决理由）；每事件仅一次 `DrawMaterial` 到 RT。
2. **不使用任何 Landscape 节点**：运行时地形为 DynamicMesh（见 `terrain-destruction-20260916.md`、`ground-material-layered-20260918.md`），地表与草材质一律走普通世界坐标采样。
3. **兼容 Nanite 植被**（`r.Nanite.Foliage=1`）与 **World Partition**：交互状态全部存在全局 RT + MaterialParameterCollection（MPC），无 per-Actor / per-Cell 状态。
4. **后台制作**：不主动启动 UE 编辑器 GUI；资产创建走 headless commandlet 脚本（`UnrealEditor-Cmd.exe -run=pythonscript`）或 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次；构建走 UBT 后台编译。
5. **默认不主动测试/验收**：交付编译状态与接入说明，验收清单留给用户（§9）。
6. 性能预算入制作（§7），遵守 `skills/ue5-performance-packaging/references/fpsgame-performance-development.md`。

## 2. 现状集成点（已勘察）

| 集成点 | 路径 | 用途 |
|---|---|---|
| 草主材质 | `Content/PN_GrassLibrary/Materials/MA_Grass.uasset`（实例 `grass_0X_YY_Mat`） | 插入 `MF_GrassDeform` 到 WPO 链（风之后叠加） |
| 风参数 MPC | `Content/PN_GrassLibrary/Materials/PN_WindParameters.uasset` | 参照其 MPC 模式新建 `MPC_GrassDeform` |
| 脚步唯一出口 | `Plugins/AutoFootstep/.../AutoFootstepEffectContext.cpp::PlayEffectBySurfaceType` | 加多播委托（§5） |
| 爆炸点（C++） | `Skills/FPSFireballProjectile.cpp::Explode`、`Skills/FPSMeteorStrike.cpp::DamageArea(bExplosion)`、`Monsters/WitchProjectile.cpp::Land`、`WorldGeneration/TerrainDestruction.*`（弹坑事件） | 调 `AddImpulse` |
| 丘陵地表材质 | 分层家族（`ground-material-layered-20260918.md`，含 `Wetness` 契约） | decal 轨迹目标；不改其分层结构 |
| 引擎 | `E:\Program Files (x86)\UE_5.8`（LauncherInstalled.dat 确认，5.8.2） | headless commandlet / UBT |

## 3. 总体架构

### 3.1 UGrassDeformSubsystem（UWorldSubsystem，新文件 `Source/FPSGAME/WorldGeneration/GrassDeform/`）

- **RT 对（ping-pong）**：`RGBA16F 1024²`，覆盖玩家周围 **48 m** 窗口（≈21 texel/m）。中心按 **4 m 网格 snap**；越格时用 recenter 材质（UV 偏移拷贝）一次性搬移内容，避免每帧抖动。
- **通道布局**：`R`=持久压平强度 0..1；`G`,`B`=弯曲方向 XY（编码 -1..1→0..1，stamp 时由事件中心算好）；`A`=impulse 世界时间戳（秒；0 表示无波前，仅持久压平）。
- **更新 pass（全部 `UKismetRenderingLibrary::DrawMaterial` 事件驱动）**：
  - `M_GrassDeformStamp`：径向 splat，参数（中心 UV、半径、强度、方向、时间戳、是否波前）；blend = max/自定义（R 取大、A 取新）。
  - `M_GrassDeformFade`：R 按 regrowth 速率衰减、A 超龄清零；**节流 4–8 Hz 且仅 dirty 时**执行（有 stamp 或 R>0 才跑）。
  - `M_GrassDeformRecenter`：窗口搬移。
- **对外 API**（BlueprintCallable）：
  - `StampTrample(FVector WorldPos, float Radius, float Strength)`
  - `AddImpulse(FVector WorldPos, float Radius, float Strength, float WaveSpeed)`
  - `SetEnabled(bool)` / `IsEnabled()`
- **MPC `MPC_GrassDeform`** 参数：`RT`（texture object）、`Center`（vector）、`WindowSize`（float）、`WorldTime`（float，每帧由 subsystem 写一次——唯一每帧 CPU 写，1 个 scalar）、`RegrowthSeconds`、`bEnabled`（static switch 驱动用 scalar）。
- **cvar**：`r.GrassDeform`（0 关 / 1 开，默认 1）；`r.GrassDeform.FadeHz`（默认 6）；`r.GrassDeform.RTSize`（512/1024/2048，默认 1024，重建 RT）。
- **控制台调试命令**：`GrassDeform.Stamp X Y Z R S`、`GrassDeform.Impulse X Y Z R S`、`GrassDeform.DumpRT`（导出 RT 到 Saved/ 供肉眼检查，仅编辑器/development）。
- **移动踩踏源**：subsystem 以 10 Hz 节流检查玩家地面投影点，水平位移累计 >0.5 m 且速度 > 阈值时 `StampTrample`（半径≈胶囊半径*0.8，强度随速度 0.3..0.7）。

### 3.2 材质侧 `MF_GrassDeform`（material function，python 脚本创建）

- 输入：世界坐标（vertex）、顶点法线近似向上因子；输出：`WPO offset (xyz)` + `flatten 0..1`（供着色器压暗/去饱和可选）。
- 逻辑：世界坐标→RT UV；采样一次；`bEnabled` static switch 关闭时输出 0（低画质编译排列零采样）；
  - 持久压平：沿 `dir(G,B)` 方向弯倒，幅度 `R * BendScale`，按顶点高度梯度（UV0 的 V 或顶点色 A，沿用 MA_Grass 现有高度遮罩约定）做枢轴；
  - 波前：`A>0` 时 `wave = (WorldTime - A) * WaveSpeed`，`|dist - wave| < Width` 内追加一次性弯倒脉冲（随 `(WorldTime-A)` 超过 Regrowth 窗口淡出）。
- 插入位置：`MA_Grass` 的 World Position Offset 链 = 现有风 WPO **之后**叠加（加算），不破坏 `PN_WindParameters` 风场。
- Nanite 注意：UE5.1+ Nanite 支持 WPO；保持偏移幅度 ≤ 草高，避免 Nanite 聚类误差；若实测伪影，回退方案=交互草网格关 Nanite（§10）。

## 4. 功能 A：踩踏/压平（M1）

M1 交付：subsystem + RT + 三个 pass 材质 + MPC + `MF_GrassDeform` + MA_Grass 接入 + 移动踩踏源 + 调试命令 + UBT 编译通过。资产创建脚本 `Tools/GrassDeform/setup_assets_m1.py` + 运行器 `run_asset_setup_m1.ps1`（headless；若检测到编辑器占用则改走 mcp 批次，脚本内判断并打印指引，不强行执行）。

## 5. 功能 B：脚步反馈（M3）

- **插件改动（最小）**：`UAutoFootstepEffectContext` 增加
  `static DECLARE_MULTICAST_DELEGATE_ThreeParams(FAutoFootstepPlayed, EPhysicalSurface /*Surface*/, const FVector& /*Location*/, const FRotator& /*Rotation*/)`，
  在 `PlayEffectBySurfaceType` 内广播（唯一出口，所有脚步 Niagara/声音都经过它）。不改 notify/trace 逻辑。
- **新组件 `UGrassFootstepFeedbackComponent`**（挂玩家 Character，或 subsystem 内监听）：
  - 订阅委托；按表面类型白名单（Grass/Dirt 类 PhysicalSurface，DataAsset 配置）过滤；
  - **RT stamp**：调 `StampTrample`（比移动源更强的单脚 splat，方向=行进方向）；
  - **Niagara**：`NS_GrassFootstepPuff`（GPU sprite，草屑+尘，≤64 活粒子，`ENCPoolMethod::AutoRelease`；制作标准读 `skills/ue5-fluid-vfx-workflow/SKILL.md`：有界池、共享调度、离线源复用）；
  - **decal 轨迹**：池化 `UDecalComponent` ×12，`M_GrassTrampleDecal`（deferred decal，投射到 DynamicMesh 地表；材质带 fade 时间参数，回收时淡出）；池满回收最旧。decal 若在该地表不生效则降级为仅 RT+Niagara（§10）。

## 6. 功能 C：爆炸压平（M2）

- 在 §2 四个 C++ 爆炸点各加一行 `GrassDeform->AddImpulse(Center, Radius*k, Strength, WaveSpeed)`（半径取各自效果半径的 0.8–1.2 倍常量系数，集中放在 `GrassDeformTuning.h`）；另暴露 BlueprintCallable 供 BP 爆炸调用。
- 视觉=单次 stamp：着色器波前环扫过 + 半径内持久压平按 RegrowthSeconds 恢复。**每爆炸 CPU 成本=1 次 DrawMaterial**。
- 与 `TerrainDestruction` 弹坑同事件源触发，保证弹坑与草压平空间一致。

## 7. 性能预算与优化（制作内约束）

| 项 | 预算 | 手段 |
|---|---|---|
| CPU/事件 | ≤0.05 ms | 单 DrawMaterial，无逐实例更新 |
| CPU/帧 | 1 scalar MPC 写 + 10 Hz 移动检查 | 无分配、无 trace（移动源用胶囊底投影，不新做 trace；脚步 trace 复用 AutoFootstep 已有异步 trace） |
| Fade pass | 1024² @ ≤8 Hz 且 dirty-only | 节流 + 条件执行 |
| 草着色器增量 | 1 RT 采样 + ~10 ALU（vertex/WPO） | static switch 低画质零采样 |
| 内存 | 1024² RGBA16F ×2 = 16 MB | cvar 可降 512² |
| Decal/Niagara | 池 12 / 粒子 ≤64 | 有界池，AutoRelease |
| Nanite/WP | 无 per-cell 状态 | MPC 全局 + 世界坐标采样 |

用户验收测量法（我们不跑）：`stat unit`/`stat gpu` 开关 `r.GrassDeform` 前后对比；`ProfileGPU` 看 MA_Grass 与三个 pass；阈值：Game Δ≤0.1 ms、GPU Δ≤0.3 ms @1080p Epic。参照 DGS demo 实测基线（`D:\FPS3D\_dgs_demo\perf_*.png`：交互 CPU Δ<0.1 ms）作为同类系统可达水平。

## 8. 交付物清单

新增（代码）：`Source/FPSGAME/WorldGeneration/GrassDeform/{GrassDeformSubsystem.h/.cpp, GrassDeformTuning.h, GrassFootstepFeedbackComponent.h/.cpp}`；插件补丁 `AutoFootstepEffectContext.h/.cpp`（委托）；爆炸点 4 处单行调用。
新增（脚本/资产，headless 创建）：`Tools/GrassDeform/{setup_assets_m1.py, setup_assets_m3.py, run_asset_setup_*.ps1}`；资产 `MPC_GrassDeform`、`MF_GrassDeform`、`M_GrassDeform{Stamp,Fade,Recenter}`、`M_GrassTrampleDecal`、`NS_GrassFootstepPuff`（路径 `Content/WorldGeneration/GrassDeform/`）。
文档：本文 + 里程碑完成时更新 §9 勾选状态。

## 9. 里程碑与用户验收清单（默认我们不测）

- **M1** 核心：编译通过；用户验收：开 `r.GrassDeform`，走路见草倒伏留痕、停步后按 RegrowthSeconds 回弹；`GrassDeform.DumpRT` 可见 splat。　**状态（2026-09-26）：代码完成且构建通过（01:01）；资产已由 headless 脚本创建完成（01:59，退出码 0）——`MPC_GrassDeform`、`MF_GrassDeform`、`M_GrassDeform{Stamp,Fade,Recenter}` 全部落盘，`manual` 为空，MA_Grass 的 WPO 自动接线成功；重跑幂等（第二次全部 skip）。用户验收项仍待用户自测。**
- **M2** 爆炸：火球/陨石/巫妖瓶/弹坑处草被环扫压平并回弹；关 cvar 后无变化。　**状态（2026-09-26 终）：代码落盘（四处单行调用 + GrassDeformTuning 系数）；合并点构建通过（02:02，Result: Succeeded，含 M2/M3/M4 与角色接线）。此前曾被并行会话 Clearwater 半成品文件短暂阻塞，其后由其自行修复。已知边界见 §10.5：48 m 窗口外（>24 m）的爆炸不产生草压平。**
- **M3** 脚步：草地表面脚步有草屑粒子+地表 decal 轨迹+更强 stamp；其他表面不触发；池不泄漏（长时间跑 decal 数 ≤12）。　**状态（2026-09-26 终）：代码落盘并通过合并点构建（编排者修了一处 using 声明与一处 DecalComponent 成员问题；组件已接入 FPSGAMECharacter 构造函数）；资产全部落盘（09:52，exit 0）：`NS_GrassFootstepPuff`、`M_GrassTrampleDecal`、`DA_GrassFootstepFeedback`（surfaces=1[SurfaceType_Default，游戏实际报告值]、puff/decal 已接线、pool=12）。⚠️ 唯一待用户核验项：Niagara 工具集 API 拒写 `Lifetime`/`Spawn Count`（读回校验捕获），发射器暂用 NE_Heat 模板默认值——请在 Niagara 编辑器确认活粒子数 ≤64，或按脚本 manual 条目里的规格手调（Spawn Count=18、Lifetime=1.4s、Loop Behavior=Once、CPUSim、世界空间）。**
- **M4** 性能/兼容收尾：scalability 低档关 deform；Nanite 开关对照无伪影；WP 流送关卡跨 cell 采样连续；按 §7 阈值出用户自测报告模板。　**状态（2026-09-26）：本轮完成——sg.FoliageQuality 门控（level 0 强制关）、用户自测模板 `Docs/Performance/grass-deform-test-template-20260926.md`；Nanite/WP 两项属用户实测项，不在代码侧。**

## 10. 风险与回退

1. Nanite WPO 伪影 → 交互草网格单独关 Nanite（FoliageType/实例级），记录于本文。
2. RT recenter 搬移缝 → 网格 snap + 搬移时 fade 暂停一帧；必要时窗口扩到 64 m。
3. Deferred decal 在 DynamicMesh 地表不生效 → 降级仅 RT+Niagara，轨迹感由 RT 压平承担。
4. 编辑器占用项目导致 headless 脚本冲突 → 走 `Tools/AssetPipeline/mcp_call_codex.ps1` 短批次；不并行写资产。
5. RGBA16F 在目标平台不支持 → 回退 RGBA8 + 方向/时间编码压缩（精度损失可接受）。

## 10.5 M1 契约冻结 v2（2026-09-26 收尾单定稿，M2/M3 必须消费此版）

- pass 材质源纹理参数统一为 **`Old`**（C++ 每次 DrawMaterial 前重绑 read 侧）；stamp 参数：`CenterUV`(vector,UV 空间)、`RadiusUV`(scalar,已归一)、`Strength`、`BendDir`(vector,0..1 已编码,HLSL 不再二次编码)、`DirStrength`、`Timestamp`；fade：`Old`、`FadeRate`、`ExpirySeconds`；recenter：`Old`、`ShiftUV`(vector)。
- MPC `MPC_GrassDeform`：`Center`(vector)、`WindowSize`、`WorldTime`、`RegrowthSeconds`、`bEnabled`、`WaveOrigin`(vector,每 impulse 变更检测后发布)。**无 RT 纹理参数**——UE 5.8 MPC 仅标量/矢量（引擎头文件实证）；RT 经 MA_Grass 的 MID 纹理参数 `GrassDeformRT` 发布（引擎唯一机制，§3.1 的 MPC-RT 表述以此为准修正）。
- 通道语义已知边界：A=逐 texel 时间戳 + 全局单一 `WaveOrigin` ⇒ 同时刻多个不同龄 impulse 的环不能共存（新 stamp 的 max() 覆盖 A）；M2 单爆炸场景可接受，多环需求留 M4 评估（GB 打包 origin 或第二张 RT）。
- 脚本版本标签 `mf-v2`/`pass-v2`：旧脚本产物必须重跑再生成。**headless 创建问题已解决（2026-09-26）**：`MaterialEditingLibrary.create_material_expression` 只接受 `UMaterial`，函数图必须走 `create_material_expression_in_function`（引擎另一入口），函数重编译走 `update_material_function` 而非 `recompile_material`；三个 pass 材质的版本标签改存 asset metadata 键 `GrassDeformVersion`（`UMaterial` 没有 `description` 属性）。MA_Grass 的 WPO 自动接线**在 headless 下实际成功**（本机实测 `patched` 含该项）。下方「M1 手工接线（如脚本未连）」保留为脚本未连时的兜底，并已补全 MF 节点图，便于人工 2 分钟复现。
- 48 m 窗口已知边界（M2 发现，M4 决定）：RT 只覆盖玩家周围 ±24 m，因此**距玩家超过约 24 m 的爆炸无法在草地上留下压平**——用户可见效果是"远处爆炸的草没反应"，而近处正常，容易误判为调用没接上；M4 决定**暂时接受**该边界（爆炸与玩家同屏通常已在窗口内，且窗口放大或第二张 RT 的成本未进预算），后续若要覆盖远距离爆炸再评估"扩大窗口"或"按爆炸点单独第二张 RT"两条路。用户自测时须先站到爆炸点 20 m 以内再触发，见 `Docs/Performance/grass-deform-test-template-20260926.md` §6。

## 10.6 M1 契约修正 v3（2026-09-26 中午，"草无反应"排障定稿；覆盖 §10.5 的 MID-RT 表述）

用户实测"草无任何反应"，排查出三处叠加断点并全部修复：

1. **RT 发布机制换代（核心修正）**：v2 的"MA_Grass 瞬态 MID + `GrassDeformRT` 纹理参数"路径**在渲染中永远不生效**——MID 从未被赋给任何渲染组件，而草实际以 `grass_0X_YY_Mat`（MI 子材质）渲染。v3 改为**持久 RT 资产对** `RT_GrassDeformA/B`（RGBA16F 1024²，脚本 `rt-v1` 创建）：MF 的两个 `TextureSampleParameter2D`（`GrassDeformRTA`/`GrassDeformRTB`）**默认值直接指向这两张资产**，默认值随 MA_Grass 继承到全部 MI 子材质，零运行时绑定；MPC 新增标量 **`ReadIsB`**（0=A,1=B），子系统每次 ping-pong 翻转时发布，MF 内 uniform 分支选读侧。`GrassDeformRT` 单参数与 MID 机制作废删除。
2. **MF 输入内部自供（mf-v4）**：旧版 `WorldPos/UpwardFactor/HeightMask` 是 FunctionInput，依赖 MA_Grass 调用点接线；实际补丁从未接这三个引脚 → 预览默认值 0 → HeightMask=0 把 WPO 输出恒置零。且 headless/桥接都无法修复接线（`UMaterial.Expressions` 对 Python 是 protected，实测拒读）。v3 起三者在 **MF 内部自供**：`AbsoluteWorldPosition`、`saturate(VertexNormalWS.z)`、`TexCoord0.V` + 标量参数 **`GrassDeformMaskFlip`**（0=用 V，1=用 1−V；若草叶倒伏方向从叶尖开始，就把它翻成 1，可在任意 MI 上覆盖）。调用节点从此只需 WPO 输出，MA_Grass 现有补丁原样可用。
3. **`r.GrassDeform.RTSize` 退役**：尺寸由 RT 资产定义；cvar 保留注册但不再重建任何东西，与资产尺寸不符时启动告警一次。

顺带修复的存量 bug：`SetEnabled(false)` 旧实现会把三个 pass MID 一并置空且无人重建，一次关/开循环后系统永久哑火；现在 Release 只解绑 RT 指针，重绑定时 `ClearRenderTarget2D` 清空两张 RT（保证禁用/重载不残留旧压平掩码）。

脚本迭代中实证的 headless/桥接 API 事实（均已写入脚本注释）：RT 工厂类名是 `TextureRenderTargetFactoryNew`（**无 "2D"**）；其 `Width/Height/Format` 无 Edit 标记，Python 视为 protected 拒设——创建后直接在资产上设 `size_x/size_y/render_target_format` 即可；`TextureRenderTarget2D` 在 5.8 Python **没有** `update_resource()`（那是 CanvasRenderTarget2D 的 API）；`b_auto_generate_mips` 同样不可设（RT 默认无 mip 链，实测无害）。

## 10.7 G1 排障定案（2026-09-26 晚，GrassDeformAudit 自驱实测；覆盖 §10.6 的"未解决"状态）

`-GrassDeformAudit` 夹具（`Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformAudit.cpp`）在 `-game` 里自驱跑完 G1 诊断序：ISM 清单（含每个草组件的材质链与 RTA/RTB 运行时解析）→ 停世界时间冻结风摆拍对照前后帧 → stamp → 双 RT ReadPixels + MPC 全参数回读 → 隔离 recenter 测试（冻结态单次搬移前后掩码对比）→ AddMovementInput 模拟行走。实测把 §10.6 之后的"草仍无反应"拆成六个叠加断点，全部修复：

1. **MF 接错主材质（根本断点）**：计划 §2 勘察认定草主材质是 `MA_Grass`（PN 包），但丘陵草实际渲染 `M_TemperateMeadow`——`Tools/WorldGeneration/build_temperate_grass.py`（09-13）从 MA_Grass 复制的独立家族（`MI_Meadow_lowGrass_*` 等），patch 从未触及它。审计 ISM 清单一行日志即定案。修复：`setup_assets_m1.py` 的 patch 目标泛化为 `GRASS_MASTERS` 双主材质列表。
2. **材质集合超限**：`M_TemperateMeadow` 活跃图已引用 PN_WindParameters + PN_BendingParameters 两个 MPC，插入引用 MPC_GrassDeform 的 MF 后超引擎"每材质最多 2 个集合"硬上限，整材质编译失败回落默认材质（灰草）。修复：变形参数并入 `PN_WindParameters`（8 标量+2 矢量，与包内 WindDirection/WindStrength 无冲突；子系统 `CollectionPath` 同步改指包集合；原 MPC_GrassDeform 资产弃置留盘）。
3. **recenter 材质 HLSL 非法**：`return UV - float2(ShiftUV);`——UE 的 HLSL 不允许以 3/4 分量矢量构造 float2（"too many elements in vector initialization"），`M_GrassDeformRecenter` 自始编译失败，每次窗口搬移画默认（黑）材质**清零整张掩码**——这就是 v1 以来"行走后掩码消失"的元凶。修复：显式 `ShiftUV.xy`。
4. **recenter 采样符号反**：目标像素应采样 `uv + ShiftUV`（特征的新 uv 是 u−Shift），原减号让内容每次搬移反向多偏 2×。修复：加法 + 第二趟零偏移纯镜像（原实现两趟同位移=双重搬移）。
5. **MF 的 Custom 节点无入口调用**：`GrassDeform_Evaluate` 节点代码只有函数定义没有 `return`（Custom 包装函数返回 0），`GrassDeform_WorldToUV` 节点跨节点调用另一个 Custom 里定义的函数（各节点独立作用域，解析不到）——掩码、参数、编译全正常但 WPO 恒 0。修复：Evaluate 体尾补入口调用+return；WorldToUV 内联公式。
6. **调用节点 GUID 陈旧**：函数重建会重铸 FunctionOutput GUID，主材质里缓存的调用节点输出引用悬空（"Missing function output connection 'WPO'"整材质编译失败）。修复：脚本每轮强制重存双主材质刷新调用节点。

顺带修复（实测未触发但静态可证）：`UpwardFactor=saturate(VertexNormalWS.z)` 在竖直草片上≈0 会把弯倒量乘零——mf-v6 起改常数 1（HeightMask 已按叶高做枢轴）；审计夹具墙钟调度（slomo 冻结时世界钟停走）、`slomo` 是作弊命令在 -game 被拒需走 `WorldSettings->SetTimeDilation`、移动输入需 `bForce` 走世界系（-90° 俯仰控制旋转下会把输入当地面钻）。

实测结论基线（mf-v8 前）：stamp 8300+ texels、MPC 全参数正确、RTA/RTB 在渲染 MI 上正确解析、RECENTER VERDICT 8307→8305（掩码在窗口搬移后存活）。**mf-v8（断点 5 修复）后的最终视觉确认待空机复测**——上次复测被并行编辑器（15 GB）内存抢占触发引擎 RefCount 断言崩溃，非本系统代码问题。复跑：`UnrealEditor.exe FPSGAME.uproject /Game/GameMaps/L_TemperateHills_Initial -game -windowed -ResX=1280 -ResY=720 -GrassDeformAudit -nosplash`，产物在 `Saved/GrassDeform/`（audit_report.txt + Audit/*.png + rt_*.png）。

契约版本现为 **mf-v8 / pass-v3**；资产重建一律重跑 `Tools/GrassDeform/run_asset_setup_m1.ps1`（编辑器占用时走 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript Tools/GrassDeform/setup_assets_m1.py`）。

## 10.8 恢复开发：mf-v10 / pass-v4（2026-09-26）

用户要求继续开发；本轮读取现有源码、SKILL、已保存制作日志与历史进度，没有启动游戏、截图或自驱夹具。§10.7 的“唯一剩余嫌疑是 UV.y”不是已排除其他路径的结论：当前作者代码仍存在以下断点。

- mf-v9 的 Custom Evaluate 内含裸 HLSL 函数定义；Custom 本身已经被引擎包装成函数，再加调用/return 不能解决嵌套函数问题。作者 runner 采用 NullRHI，保存成功也不能证明目标 SM6 着色器已生成。本轮改为直接函数体、显式 SampleLevel 0、D3D12 后台编译，逐个处理材质编译返回的错误列表。
- mf-v9 把 HeightMask 置为 1 会平移整株。现改为实例空间顶点高度减实例局部包围盒最小 Z，转换为世界高度向量，以此弯曲；根部零高度不动，兼容不同草高和实例缩放/坡向。保留原风 WPO，两个实际主材质同时接入。WPO 位移上限 100 cm，材质 bounds 预算 140 cm。
- Opaque Emissive 是 RGB，原 float4 第四分量不是 RT 时间戳输出。RT 现明确只消费 RGB（R 压平、GB 径向方向）；最近一次爆炸的世界坐标、时间、半径、强度和速度直接由 PN_WindParameters 传递，不依赖 Alpha，也不因 recenter 改变波源。
- 原 stamp 的方向强度一直为 0，初次黑底 GB 被解码为 (-1,-1)。现每个被盖章像素计算径向方向；初始、清空和恢复到零均使用 GB=(.5,.5)，范围外不改方向。
- 队列原来保存入队时的窗口 UV，Tick 随后移动窗口，导致边界帧盖在错误位置。现存世界 XY，在 drain 时按最终窗口换算 UV。recenter 单次复制后提升读侧，下一 pass 完整覆盖另一侧。
- 原代码每个 stamp 都重启 fade 倒计时，连续移动会让旧草痕不恢复；fade 也按固定步长而非实际经过时间衰减。现独立累积游戏时间、先 fade 后 stamp，新脚印和窗口移动不推迟旧草恢复。
- 原 cvar 改变只清队列，IsEnabled 未读该值；现三门共同控制，关闭清 RT/波前，开关状态在未建立窗口时也可发布。编辑器世界不再创建子系统，避免它重置游戏使用的 RT；踩踏增加已有移动组件的着地条件。

作者脚本按命名节点原位更新，并保留 FunctionOutput GUID；调用节点显式刷新后实际编译和保存两个主材质。UE 5.8 的 get_material_expressions / get_material_function_expressions / get_material_property_input_node 可在后台使用，旧“读不到所以只能手工接”的说明已从 SKILL 更正。历史断开节点不删除，避免启动加载时 rooted 表达式被 MarkAsGarbage 引发断言。

**本轮制作时进一步定位到的实际资产问题：MF_GrassDeform 存有两个同名 WPO 输出。** 一开始只更新按名字找到的第一个，另一个仍连接历史 Custom；目标 SM6 编译实际报 `function definition is not allowed here` 和 `GrassDeform_Evaluate` 未声明。现保留两个既有输出 GUID、把所有同名 WPO 输出都接至 GrassV10.Bend，避免旧调用引用继续执行旧函数。回执列出 FunctionOutput_1 / FunctionOutput_0 的真实输入，均为 GrassV10.Bend；Flatten 指向 GrassV10.Flatten。先前“加 return 就修好了”的历史结论应以此编译证据更正。

制作入口仍为 Tools/GrassDeform/run_asset_setup_m1.ps1，自动写 SourceAssets/GrassDeform20260926/ 下的备份与逐资产回执。脚步粒子和贴花沿用 09-26 已保存的专门修正（见 footstep-black-blocks-20260926.md），不重跑旧 M3 模板。48 m 窗口与单活动爆炸波前仍是边界。本轮只完成制作和必要构建，视觉与玩法留给用户测试。

### 本轮实际交付

- 普通 DLL 构建成功：`Saved/BuildEditor/build-20260926-195459.log`。首次构建遇到现有药水组件 FStreamableHandle 的 class/struct 前向声明冲突，按引擎定义仅改一行为 struct 后完成构建。
- D3D12/SM6 后台作者退出 0：`Saved/Logs/grass-v10-author-output-05.txt`。制作期间重设 Custom 输入会产生暂时的 missing UV 警告，最终三个 pass 和两个主材质的显式编译错误列表均为空。
- 9 个资产已保存：PN_WindParameters、两张 RT、MF_GrassDeform、三个 pass、MA_Grass、M_TemperateMeadow。回执 `SourceAssets/GrassDeform20260926/authoring-20260926-200029.json`；修改前副本在该目录的 BeforeV10-* 下。
- 未启动 UE 编辑器界面、游戏、PIE、截图或 GrassDeformAudit，不宣称视觉和玩法已验证。现有草实例沿原材质引用使用本轮资产，用户重新运行游戏确认踩踏、恢复与爆炸反馈。

## 11. 里程碑派单约定（历史，不作为当前委派授权）

编码由子代理 **deepseek-v4.1-flash** 执行（派发对：`provider: qwen-token-plan-individual` + `model: deepseek-v4.1-flash`，见 WORKFLOW.md §11 已验证对；用户口语"deepseekflashv4.1"即指它；裸模型名一律启动失败返回 null）。每里程碑一单、顺序依赖（M2/M3 依赖 M1 文件，M4 收尾）。每单返回结构化报告：`{files_created, files_modified, build_status, deferred_runs, notes}`；编排者（本会话）在单间做代码Review 再放下一单。不主动 commit；未提交工作保留供用户审查。

## 早期手工接线已退役

原附录已归档到 trash/grass-paused-20260927/Docs/WorldGeneration/grass-manual-wiring-retired-20260927.md。它使用的第三 MPC、Alpha 时间与旧 Custom 接法已失效，不得用于重建。当前保留源码及未完成状态见 [暂停与发布记录](grass-paused-publication-20260927.md)。
