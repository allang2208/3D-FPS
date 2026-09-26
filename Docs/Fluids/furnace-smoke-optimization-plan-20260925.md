# 高炉运行烟雾优化升级方案（2026-09-25）

按 [流体特效工作流](../../skills/ue5-fluid-vfx-workflow/SKILL.md) 与其[效果制作配方](../../skills/ue5-fluid-vfx-workflow/references/effect-recipes.md)、
[制作管线](../../skills/ue5-fluid-vfx-workflow/references/production-pipeline.md)、[运行接入与预算](../../skills/ue5-fluid-vfx-workflow/references/runtime-budget.md) 制定。
现状基线＝[高炉工作黑烟 2026-09-24](furnace-black-smoke-20260924.md) 的 v4：单层浮力烟柱（喉口锚定、雨天阵风吹散、软化出生），
运行时单一入口 `UFluidPresentationSubsystem::UpdateFurnaceSmoke()`（5Hz），资产 `NS_FurnaceBlackSmoke`（CPU 发射器、复用枪口图集 `T_MuzzleSmokeMantaflowV14`＋`M_RollingImpactSmoke`）。

## 0. 现状盘点与问题定义

| 维度 | v4 现状 | 观感/技术缺口 |
| --- | --- | --- |
| 层次 | 单层烟柱＝全部主体 | 无内芯翻卷层与事件层；近景（2–15 m）大卡片"贴片感"、内部密度运动不足 |
| 状态表达 | `bWorking` 二值（有任务或存料）→ SpawnRate 目标二值 16/0 | 炉子三轴升级、批量、火力强弱在烟上完全不可见；点火/熄火只有匀 ramp |
| 流体动画源 | 复用枪口 64 帧 Mantaflow 图集 | 枪口域尺度小、翻卷频率快；90 cm 炉烟卡片采样它＝细碎高频卷，与慢浮力柱形态语言不符 |
| 运动 | 出喉喷射指数衰减＋双频翻卷＋风积分（τ .55） | 无竖直风剪切剖面、无绕轴 swirl、无喷发节奏；高段与低段风响应同幅 |
| 雨天 | v3/v4 雨量门（阵风、撕裂、快散、软化） | 保持；新增层必须 R=0 恒等（零回归） |
| 预算 | ≤6 组件、峰值 ≤66 粒/柱、ConfigureSmoke(16)、85 m 剔除 | 保持池/组件上限不变；新增层次走**同组件内多发射器**，不新增组件池 |

受保护面（不动）：冶炼数值/存档/批量结算、燃料合同、UI、输入、伤害与导航；烟不注册碰撞、不投影。
观察距离：近 2–15 m 侧影与炉口、中 15–35 m、远 35–85 m 渐隐剔除（沿用）。

## 1. 目标层次（技能"分层与定时"口径）

| 层 | 内容 | 触发/寿命 | 距离与画质门 |
| --- | --- | --- | --- |
| L0 主体烟柱 | v4 现层，保持已认可形态；仅接 `User.Heat` 调色/调密度 | 工作期间持续；停燃 2.2 s 断供＋3.9 s 散尽（不变） | 全距离（60–85 m 渐隐不变） |
| L1 内芯翻卷层（新） | 同组件第二发射器：大卡（出生 40→110 cm）、慢速（.6×主体）、深灰低 α、独立种子/镜像/flipbook 相位错开；只填柱体内侧 | 与 L0 同生同灭；速率 ≤6/s、寿命 ≤2.5 s | <35 m 且 EffectsQuality≥中；池满/低画质先裁本层 |
| L2 炉口事件层（新） | 点火冷启动：`BurnStartTicks/FireStartTicks` 年龄 <4 s 时浅灰白蒸汽相（亮色、快散、低浮力抑制）混入转黑；批量完成/投料：SpawnRate 短脉冲＋≤12 粒一次性 puff | 事件驱动，脉冲 ≤1.2 s | <50 m；脉冲受共享细节令牌 |
| L3 火星层（可选，P3） | 炉口稀疏火星上飘即灭 | ≤8/s、寿命 ≤.9 s | <15 m 且高画质；默认关 |

原则：先保主体轮廓与运动方向可读再加层；"加强"不靠加灯、不靠全局加粒子——L1/L2 的粒子预算从 L0 的冗余里让（L0 额定 16/s 在低热档下调）。

## 2. 状态驱动（用既有数据，不改玩法）

`FVoxelSmeltingJob{ProgressSeconds,BurnStartTicks,BatchCount}` 与 `FVoxelFurnaceFuel{FuelSeconds,Level,FireStartTicks,FuelLevel,BatchLevel}` 已够：

- **连续火力 `User.Heat`(0..1)**（5Hz 与风同拍写）：`Heat = clamp( 有任务? .55+.15·min(BatchCount,5)/5 : .0 , …) + 燃料段年龄因子`；空闲火种（有燃料无任务）=.25 档薄烟，满批量在炼=1 档浓黑烟；L0 的 SpawnRate 目标由 `16·Lerp(.45,1,Heat)`、颜色深度与 α 由 Heat 门控（表达式纯函数，R=0/Heat 档各自恒等回 v4）。
- **点火年龄 `User.Ignition`(0..1)**：`now−BurnStartTicks(or FireStartTicks)` 归一化 4 s；资产端把出生色从蒸汽灰白插值到炭黑、浮力与消散速度同步过渡；熄火段反向走余烟色。
- **完成脉冲**：`ProgressSeconds` 跨越 `recipe·BatchCount/速度倍率` 的整批边界（C++ 侧记录上一拍进度比较，无新事件系统）→ 一次性 `User.Puff`=1 衰减写 1.2 s。

## 3. 流体动画源升级（路线选择记录）

- **选**：离线 Mantaflow 专烘炉烟密度图集 `T_FurnaceSmokeMantaflowV1`（慢速大尺度翻卷域，64 帧、8×8、R 通道、BC 无 mip，合同同[图集数据合同](../../skills/ue5-fluid-vfx-workflow/references/production-pipeline.md)）；沿 `bake_mantaflow_foundation.py` 族离线烘，`SourceAssets/FurnaceSmoke20260925/` 存 .blend/参数/帧清单。L0/L1 改采新图集（SubUV 格内 UV 先恢复再切图集）。
- **不选**（记录理由）：Animated SVT／Geometry Cache／Niagara Fluids 2D-3D——观察距离 2–30 m 侧影不需要体积视差与即时流场交互，并发/显存/流送成本无正当理由；接触近似继续 `User.SmokePlane0..4`。
- 烘不出来或窗口不足时的 P1 兜底：同图集不同 flipbook 相位/镜像/尺度档做 L1（形态语言改善减半但零新资产）。

## 4. 运动精修（作者脚本增量，全部年龄纯函数）

- 竖直风剪切：`WindEff = Wind·(0.55+0.9·saturate(z/260cm))`（低段滞后、高段倾斜更甚；与既有 τ 积分串联）。
- 绕轴 swirl：切向分量幅值随年龄 0→6 cm/s 缓入、双频相位逐粒子种子；只加方向不加粒子。
- 喷发节奏：SpawnRate 乘 `1+0.18·sin(2π·t/2.7s+seed)` 低频调制（团块感，不增总量：均值不变）。
- 雨天：以上各项幅值 ×(1−0.3·R) 或与 v3 撕裂项同门；**R=0 全部恒等 v4（零回归）**。

## 5. 预算与分级（对齐 runtime-budget 规则）

| 项 | 数值 |
| --- | --- |
| 组件/池 | 不变：≤32 登记、≤6 烟组件、池满置换最远已散尽炉 |
| 峰值粒子/柱 | L0 ≤66（不变）＋L1 ≤15＋L2 puff ≤12 ⇒ ≤93；ConfigureSmoke 请求 16→18（令牌桶 72/180s 内） |
| 触发频率 | 仍 5Hz 单入口；无新 Actor Tick、无每帧全遍历；完成脉冲比较在既有 5Hz 拍内 |
| 纹理 | 新图集 1024²·BC4·无 mip ≈ +1 MB 驻留；旧枪口图集引用在本 NS 内解除（他处引用不动） |
| 距离/画质 | L1 <35 m 且中画质以上；L2 <50 m；L3 <15 m 高画质；`AllocateDetail` 低画质系数沿用（L1/L2 先被裁） |
| 热路径 | 无同步 Load（软引用异步预载不变）、无 GPU 回读、无材质运行时编译 |
| 随机 | 逐粒子种子沿用 UniqueID×黄金比派生流，不碰战斗随机序列 |

## 6. 源与资产修改清单

- C++：`Source/FPSGAME/WorldGeneration/FluidPresentationSubsystem.{h,cpp}` 仅 `UpdateFurnaceSmoke` 内：Heat/Ignition/Puff 计算与 `User.*` 写入、完成边界记忆字段（`FFurnaceSmoke` 加 `LastProgress`/`Heat`）。
- 作者脚本：`Tools/Fluids/author_furnace_black_smoke.py` 增量扩展（新稳定 tag `FurnaceSmoke20260925.*`；重跑前无条件退役上一轮 assignment tag——已知坑）；改前复制 `NS_FurnaceBlackSmoke` 原件为 `NS_FurnaceBlackSmoke_V4` 留底。
- 烘焙：`Tools/Fluids/bake_furnace_smoke_v1.py`（新，沿 foundation 族）＋`SourceAssets/FurnaceSmoke20260925/`。
- 序列：`Tools/Fluids/run_furnace_v2_sequence.ps1` 族排队（编辑器空窗：author→compile→save→`Build-Editor.ps1`；1s＋连续空采样抓窗，不强关他人编辑器）。
- 文档：本案＋`furnace-black-smoke-20260924.md` 增补 v5 段。

## 7. 阶段划分（每阶段独立可交付可回滚）

- **P0 对账与留底**：`verify_ns.py`/`assets.json` 核对磁盘 NS 是否已含 v3/v4 表达式（v4 状态段历史上曾"构建未落地"）；复制 V4 留底；记录基线散列。
- **P1 状态驱动＋L1/L2（无新烘焙）**：C++ Heat/Ignition/Puff＋资产内芯/事件发射器（兜底图集方案）；编译落地。
- **P2 专烘图集换源＋运动精修**：离线烘焙窗口内完成；L0/L1 切新图集；剪切/swirl/节奏上线。
- **P3 可选**：L3 火星层、分级微调、文档收尾。

## 8. 验收口径（用户规则：默认不自动测试）

- 不跑 PIE/截图/性能采集；实机观感由用户确认：晴天近景分层与内芯翻卷可读、点火蒸汽→黑烟过渡、整批完成脉冲、熄火余烟、雨天与 v4 无回归、远距分级无突变。
- 性能测量仅在用户明确要求时按 runtime-budget 固定条件采样；未采样只报实现预算，不承诺 FPS 数字。

## 9. 性能专章（与优化同权重）

- **CPU/tick**：保持单一 5Hz 入口、无新 Actor Tick、无每帧全遍历。每炉每拍新增成本＝若干算术＋一次 `FindSmelting` 指针读（bWorking 已读）＋一次 double 比较（完成边界）；`FFurnaceSmoke` 仅 +12 B（`LastProgress` double＋`Heat` float）。tick 内不新增容器/分配/字符串拼接（`User.*` 参数名为编译期常量）。
- **GPU/透明覆盖**：近景最坏（10 m 侧影）L0+L1 合计屏幕覆盖目标 ≤8%；L1 α 上限 .18、仅 <35 m、且乘既有 `User.DetailReduction`；L2 puff 一次性 ≤12 粒。不新增灯/投影/体积雾开关，`SetCastShadow(false)` 保持；不触碰光追/Lumen/纹理流送全局策略。
- **采样与纹理**：P1 不新增纹理（L1 复用现图集不同相位/镜像）；P2 新图集 1024²·BC4·无 mip ≈ +1 MB 驻留，仅本 NS 改采样，枪口图集他处引用不动。SubUV 切图集前先恢复格内 UV（管线合同）。
- **池与并发**：L1/L2 为同组件内发射器 ⇒ 组件池/≤6 上限/置换策略零变化；峰值 ≤93 粒/柱仍受 `ConfigureSmoke` 令牌桶约束（请求 16→18）。
- **分级矩阵**：

  | 距离＼画质 | 低 | 中 | 高 |
  | --- | --- | --- | --- |
  | <15 m | L0 | L0+L1 | L0+L1+L2(+L3) |
  | 15–35 m | L0 | L0+L1 | L0+L1+L2 |
  | 35–50 m | L0 | L0 | L0+L2 |
  | 50–85 m | L0 渐隐 | 同左 | 同左 |

- **恒等锚点（零回归）**：`在炼任务∧燃料燃烧中 ⇒ Heat=1` 时 L0 的 SpawnRate/色/α 与 v4 逐式恒等；`Rain=0` 时全部新表达式退化为 v4。空闲火种 Heat=.25、熄火段走既有 2.2 s/3.9 s 曲线不变。
- **测量协议（仅用户要求时执行）**：固定地图/种子/机位/分辨率/画质/前台模式；对比 炉开/炉关、近/远 四组的 Game/Draw/GPU 帧时与慢帧分布；记录活跃粒子、透明覆盖、组件数、纹理驻留与几何查询次数；未采样只报实现预算。

## 10. 实施分工与编码任务包（交子代理执行）

- **派发目标（2026-09-25 实测定稿）**：`provider: qwen-token-plan-individual` ＋ `model: deepseek-v4.1-flash`
  （用户口语"deepseekflashv4.1"即此；裸名与 workbuddy 路由的 deepseek 对均启动失败）。
  失败 ident 清单、核对顺序与探针方法见 [WORKFLOW.md §11 子代理模型目标与派发](../../WORKFLOW.md)。

- **T1 留底**：`Content/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke.uasset` 文件级复制留底到
  `SourceAssets/FurnaceSmoke20260925/backup-NS_FurnaceBlackSmoke-V4.uasset`（放 Content 外，避免包名冲突）；记录散列。
- **T2 C++ 状态驱动**：`FluidPresentationSubsystem.{h,cpp}` 仅 `FFurnaceSmoke`＋`UpdateFurnaceSmoke` 内：
  Heat/Ignition/Puff 计算与 `User.Heat/User.Ignition/User.Puff/User.L1Gate` 写入（5Hz 同拍）；完成边界用 `LastProgress` 比较；不碰冶炼结算/存档。
- **T3 作者脚本**：`Tools/Fluids/author_furnace_black_smoke.py` 增量：声明新 User 参数；L1 内芯发射器与 L2 事件发射器（门控 Heat/Ignition/Puff/L1Gate）；重跑前**无条件退役**上一轮 assignment tag（已知坑）；新稳定 tag `FurnaceSmoke20260925.*`；R=0∧Heat=1 恒等锚点写进表达式注释。
- **T4 构建**：编辑器空窗则 `Tools/Build/Build-Editor.ps1`；被占用则如实记录阻塞，不强制结束他人编辑器、不跨对话协调。
- **T5 资产执行（可选窗）**：仅当编辑器空窗且序列脚本可用时走 `run_furnace_v2_sequence.ps1` 族重作 NS；否则标"待执行"并保留脚本与留底。
- **T6 文档**：`furnace-black-smoke-20260924.md` 增 v5 实施段；本案状态回填。
- **完成定义**：T1–T4 绿（或阻塞有因）＋T3 幂等可重跑＋玩法合同零改动＋零回归锚点在表达式内；T5/T6 视窗口如实标注。

### 10.1 执行状态回填（2026-09-25 22:3x，子代理执行）

| 任务包 | 状态 | 事实 |
| --- | --- | --- |
| **T1 留底** | ✅ 完成 | 文件级复制到 `SourceAssets/FurnaceSmoke20260925/backup-NS_FurnaceBlackSmoke-V4.uasset`；前后 SHA256 一致 `2061B6EB…E2E36`（969207 B）；回执 `backup-manifest.json` |
| **T2 C++ 状态驱动** | ✅ 源码完成，⛔ 未编译 | 仅 `FluidPresentationSubsystem.{h,cpp}`；Heat/Ignition/Puff/L1Gate 写入；`FFurnaceSmoke` +`LastProgress`/`PuffAt`/`Heat`；批边界复用既有 `JobTotalSeconds`；无新增遍历/容器/分配；无新自由符号（Unity 前缀要求不适用） |
| **T3 作者脚本** | ✅ 源码完成，⛔ 未执行 | `author_furnace_black_smoke.py`：声明 4 个新 User 参数；L1 `FurnaceSmokeCore`（≤6/s、≤2.5s、40→110cm、.6×、α≤.18、独立种子/镜像/相位）；L2 `FurnaceSmokeEvent`（Ignition 蒸汽相、Puff 一次性）；`retire_tags()` 无条件退役全部旧 tag 且新 tag `FurnaceSmoke20260925.*`；`ast.parse` 通过；`DeltaTime`/`smoothstep` 零出现 |
| **T4 构建** | ✅ 完成（空窗后收尾） | 子代理首报阻塞属实（PID 27164）；空窗后首编报其笔误 C3861（`UWorldSubsystem` 无裸 `GetGameInstance()`），主代理改 `GetWorld()->GetGameInstance()` 链；`Saved/BuildEditor/build-20260925-223752.log` **Result: Succeeded**，DLL 已链接 |
| **T5 资产执行** | ✅ 完成（序列空窗内） | headless 重作回执 `FURNACE_SMOKE_SAVED`（22:33:54）；`NS_FurnaceBlackSmoke.uasset` 落盘 2270858 B（v4 留底 969207 B）；孤儿作者进程自行退出、未强杀 |
| **T6 文档** | ✅ 完成 | 本文 §10.1 ＋ `furnace-black-smoke-20260924.md` v5 实施段与 v5 状态段 |

- **恒等锚点数值验证**：`Heat=1` ⇒ SpawnRate 门 `(.55+.45·1)=1.0000000000`、色门 `(1−.40·(1−1))=1.0000000000`、α 门 `(.55+.45·1)=1.0000000000`，三处与 v4 逐式恒等。
- **零改动面确认**：冶炼数值/存档/批量结算/UI/输入/伤害/导航合同未触碰；未新增同步 Load、灯、投影、碰撞、导航影响。
- **待办（空窗后一次做完）**：① `Tools/Build/Build-Editor.ps1`（前台，编辑器关闭后）；② `Tools/Fluids/run_furnace_v2_sequence.ps1`（或先 author 后 build），须见 `FURNACE_SMOKE_SAVED` 回执才算资产落地。
- **并行现场**：本工程工作区存在大量其他对话的未提交改动（289 文件），本次仅改 3 个文件（上述 C++/脚本/文档），未做任何全库清理、回滚、暂存或提交。

## 11. 回滚与风险

- 回滚＝C++ 还原两文件＋NS 用 T1 留底经序列脚本重作；分层全在表达式门控内，单层出问题可把对应 Gate 常量置 0 热退档。
- 风险：作者脚本重跑踩 Unity/VectorVM 已知坑（DeltaTime 不可引用、smoothstep 无内建、tag 退役）——T3 约束已列；资产重作需编辑器空窗，与并行任务窗口冲突时按序列排队不强关。
