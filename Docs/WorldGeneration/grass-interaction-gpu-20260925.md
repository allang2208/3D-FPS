# 草地交互 GPU 升级计划（踩踏 / 脚步反馈 / 爆炸压平）

日期：2026-09-25　状态：计划已批准，M1 派单中
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

## 11. 里程碑派单约定

编码由子代理 **deepseek-v4.1-flash** 执行（派发对：`provider: qwen-token-plan-individual` + `model: deepseek-v4.1-flash`，见 WORKFLOW.md §11 已验证对；用户口语"deepseekflashv4.1"即指它；裸模型名一律启动失败返回 null）。每里程碑一单、顺序依赖（M2/M3 依赖 M1 文件，M4 收尾）。每单返回结构化报告：`{files_created, files_modified, build_status, deferred_runs, notes}`；编排者（本会话）在单间做代码Review 再放下一单。不主动 commit；未提交工作保留供用户审查。

## M1 手工接线（如脚本未连）

`Tools/GrassDeform/setup_assets_m1.py` 会创建全部 M1 资产，但 **MA_Grass 的 WPO 接线可能无法自动完成**：`unreal.MaterialEditingLibrary.get_material_property_input_node` / `get_material_property_input_node_output_name` 只在**已打开材质编辑器**的会话中可用，headless commandlet（`-run=pythonscript`）里读不到现有 WPO 链。脚本在这种情况下按设计**保持 MF_GrassDeform 未连接、不猜测重连**（盲改共享草主材质会丢掉风场 WPO，影响全部草实例）；它会在 `GRASS_DEFORM_M1_RESULT` 的 `manual` 列表里说明。

先确认是否真的需要手工接线：

1. 跑 `Tools/GrassDeform/run_asset_setup_m1.ps1`（编辑器占用时改走 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript Tools/GrassDeform/setup_assets_m1.py`）。
2. 看输出的 `GRASS_DEFORM_M1_RESULT`：`patched` 含 `MA_Grass WPO += MF_GrassDeform` 即已自动接好，本节其余步骤可跳过；`manual` 里出现 WPO 相关条目才需要往下做。

手工接线步骤（编辑器内，一次即可）：

1. 打开 `/Game/PN_GrassLibrary/Materials/grassMaterials/MA_Grass`。
2. 在图表空白处右键，搜索并添加 **GrassDeform**（即 `MF_GrassDeform`，位于 `/Game/WorldGeneration/GrassDeform/`）。
3. 找到当前连到 **World Position Offset** 的那个节点（现有风场 WPO 输出，通常来自 `PN_WindAnimation` / `PN_WindParameters` 链路），**不要删除它**。
4. 添加一个 **Add** 节点，把它的 Description 命名为 `GrassDeformWPOAdd`（脚本自动接线时也用这个标记来判断"已接好"，可避免重复叠加）。
5. 连线：现有风场 WPO 输出 → Add 的 **A**；`MF_GrassDeform` 的 **WPO** 输出 → Add 的 **B**。
6. 把 Add 的输出 → 主节点的 **World Position Offset**（替换原先直连的那条线）。
7. `MF_GrassDeform` 的其余输入按需接上：世界坐标（`WorldPos`）、顶点法线近似向上因子（`UpwardFactor`，取顶点法线的 Z）、高度遮罩（`HeightMask`，沿用 MA_Grass 现有的高度遮罩约定，UV0 的 V 或顶点色 A）。这三个是函数输入引脚，未连时会用预览默认值。
8. 应用/保存 MA_Grass，编译材质，确认草仍然随风摆动（说明风场链未被破坏），再继续。

### M1-A 手工重建 `MF_GrassDeform`（仅当脚本未能创建该资产时）

2026-09-26 起脚本已能在 headless 下完整创建 `MF_GrassDeform`（见 §10.5），正常情况下**不需要**本节。只有脚本报错、或该资产被删除且脚本无法运行时，才按下面手工复现；目标是最小可用版本，节点不多，约 2 分钟。

资产：`/Game/WorldGeneration/GrassDeform/MF_GrassDeform`（描述写 `mf-v2` 以便脚本识别为最新版）。

**函数输入**（`FunctionInput` 节点，三个）：

| 引脚名 | 类型 | 说明 |
|---|---|---|
| `WorldPos` | Vector3 | 顶点世界坐标 |
| `UpwardFactor` | Scalar | 顶点法线 Z（0..1） |
| `HeightMask` | Scalar | 高度遮罩，沿用 MA_Grass 约定（UV0 的 V 或顶点色 A） |

**函数输出**（`FunctionOutput` 节点，两个）：

| 引脚名 | 类型 | 说明 |
|---|---|---|
| `WPO` | Vector3 | 世界位置偏移 |
| `Flatten` | Scalar | 持久压平量 0..1（供着色器可选使用） |

**节点图**（共 1 个 RT 采样 + 4 个 Custom 节点）：

1. `Custom` `GrassDeform_WorldToUV`，输出 **Float2**，输入引脚依次 `WorldPos`、`Center`、`WindowSize`：
   ```hlsl
   return (WorldPos.xy - Center) / WindowSize + 0.5;
   ```
2. `TextureSampleParameter2D`，参数名 **`GrassDeformRT`**（必须与 `GrassDeformParams::GrassMaterialRT` 一致），UV 接节点 1 的输出。输出用 **RGBA**（A 通道是 impulse 时间戳，只用 RGB 会静默关掉波前）。
3. `CollectionParameter` **`bEnabled`**（来自 `MPC_GrassDeform`）。
4. `Custom` `GrassDeform_Gate`，输出 **Float4**，输入引脚依次 `Enabled`、`Sample`：
   ```hlsl
   return Enabled > 0.5 ? Sample : float4(0, 0, 0, 0);
   ```
   连线：节点 3 → `Enabled`；节点 2 的 **RGBA** → `Sample`。
5. `Custom` `GrassDeform_Evaluate`，输出 **Float3**，输入引脚依次 `WorldPos`、`UpwardFactor`、`HeightMask`、`SampleUV`、`WindowSize`、`WaveOrigin`、`WorldTime`、`RegrowthSeconds`、`BendScale`、`WaveSpeed`、`WaveWidth`、`MaxOffset`、`DeformSample`，函数体为脚本 §`FUNCTION_CODE` 中的 `GrassDeform_WorldToUV` + `GrassDeform_Evaluate` 两个函数（整段粘贴即可；入口是 `GrassDeform_Evaluate`，`Flatten` 是它的 `out` 参数）。
6. `Custom` `GrassDeform_FlattenOut`，输出 **Float**，输入引脚 `Sample`，函数体 `return Sample.r;`。

**其余输入引脚固定接法**：

| Evaluate 引脚 | 来源 |
|---|---|
| `SampleUV` | 节点 1 的输出 |
| `DeformSample` | 节点 4 的输出 |
| `Center` / `WaveOrigin` | `MPC_GrassDeform` 的 `Center` / `WaveOrigin`（CollectionParameter，vector） |
| `WindowSize` / `WorldTime` / `RegrowthSeconds` / `WaveSpeed` | `MPC_GrassDeform` 同名 scalar（CollectionParameter） |
| `BendScale` / `WaveWidth` / `MaxOffset` | ScalarParameter，默认 `28.0` / `90.0` / `34.0`（留在函数上，便于材质实例覆写） |

**输出连线**：节点 5 → FunctionOutput `WPO`；节点 6 → FunctionOutput `Flatten`（节点 6 的输入来自节点 4）。

**注意**：Custom 节点的输入引脚名要与上表**逐字一致**（HLSL 里按名字引用），引脚顺序也要一致（生成代码按声明序传参）。做完后按 MA_Grass 那一节第 3–6 步接入 WPO 链。

验收提示（用户自测）：接好后开 `r.GrassDeform`，走路见草倒伏留痕、停步后按 `RegrowthSeconds` 回弹；`GrassDeform.DumpRT` 导出 RT 应能看到 splat。若走路无反应但 `GrassDeform.Status` 显示 `enabled=1 assets=1`，多半就是本节第 3–6 步没有接上。
