# 高炉工作黑烟（2026-09-24）

按 [流体特效工作流](../../skills/ue5-fluid-vfx-workflow/SKILL.md) 制作：给工作中的高炉炉顶加黑烟，落实工作流全部既有手段（随风飘动、随机散布、翻滚密度、接地近似、距离/画质分级、有界池），不新造流体模拟。

> **v2（2026-09-24 晚，用户实测"没精准匹配出口、效果不够写实"后的整改）**
> ① 发射口改为**网格实测喉口**：Blender 径向射线剖面（`SourceAssets/FurnaceSmoke20260924/measure_throat.py` → `Saved/furnace_throat.json`）量得炉喉＝以 manifest `ChargingMouth(-18,0)` 为心、**半径 18.4cm** 的竖直天空圆（碗内底 z≈184、凸缘环 18.4→26cm 实心、顶 220）。C++ 改 `Body->GetComponentTransform().TransformPosition((-18,0,208))`——旧版"世界 AABB 顶面中心"XY 偏口心 18cm 且不随炉子 Yaw 转，是错位根因。
> ② 运动学重写为浮力烟柱模型：出喉喷射 150 cm/s **指数衰减**至终速 78 cm/s（旧匀加速像喷泉）；出生改**喉盘面积均匀**（sqrt 半径×0.82；旧为偏心方形抖动）；爬出凸缘前保持窄柱（smooth 门控），之后锥形扇开＋双频翻卷随粒径增长；粒径 24cm 起步（**小于喉口 36.8cm**，"从洞里挤出"）sqrt 生长至 ~90cm；烟色压暗（.016→.086）逐粒子明暗分层；额定 13→16/s、寿命 2.6–3.6s、散尽窗 3.9s（峰值 ~66 粒/柱，有界预算内）。

> **v3（2026-09-24 深夜，用户"下雨时烟被随机方向的风快速吹散、加快消散、改变消散方式"）**
> 雨量门 `User.Rainfall`（0..1，= `AFPSWeatherManager::GetEffectiveRainIntensity`，5Hz 与风同拍写入）串起资产与 C++ 两侧：
> ① **随机方向阵风（C++）**：炉烟注册条目打 `bOwnWind`，共享风扫跳过、由 `UpdateFurnaceSmoke` 自写 `User.Wind = WindAt(基风含屋檐遮蔽) + RainGust`；`RainGust` 用无理数比正弦叠加出**平滑伪随机方向与脉动强度**（周期分钟级不露循环，含小幅竖直剪切），幅值 ×雨量，合成钳 260 cm/s。
> ② **吹散（资产，全按年龄纯函数）**：逐粒子双频撕裂摆动（频率/相位各走一路种子，幅值随年龄 1.8+9·a 增长、带小幅下压＝雨点打散）；风响应 ×(1+2.2·R)；浮力上升 ×(1−0.45·R)（湿烟爬不高）。
> ③ **加速消散**：淡出 hold 0.55→0.15 随雨量前移、整体 alpha ×(1−0.28·R)、出生寿命 ×(1−0.38·R)、摊薄增速 ×(1+0.5·R)、 SpawnRate ×(1−0.25·R)。雨量=0 时全部因子回到 v2 恒等（**零回归**）。
>
> **v4（2026-09-24 深夜，用户雨测反馈两点）**
> ① **"没随风飘散"＝构建未落地，非逻辑错**：用户 23:12 重启编辑器时，v3 雨天 C++ 从未编译（DLL 停在 22:22:48，序列 10s 轮询漏抓关闭窗口）——截图跑的是纯 v2（恒定天气风单向）。序列轮询改 **1s＋连续两次无编辑器采样**，确保抓窗。
> ② **出生黑烟边界/线条感过重**：小(24cm)、浓(α .44-.60)、近黑(.016)的卡片重叠描出扇贝状轮廓；上段消散灰反而真实。用户要求**统一到消散段观感**。改：出生色 .016→**.050 灰**（与顶段 .088 同族，只留轻渐变）、α **.44+.16→.26+.12**（重叠不再压出暗缝）、出生尺寸 **24→27cm**（大团边缘曲率低、轮廓弱）、淡入 **.07→.22 归一化年龄**（不"啪"地以满不透明出现＝无锐利首帧边）、出生尺寸下限系数 .72→.82。晴天/雨天表达式同受此软化。

## 任务记录

- **事件与接触面**：高炉构件 `blast_furnace` 工作＝有在炼任务或炉内存料（同 `AVoxelBuildWorld` 护炉谓词 `FindSmelting||FuelAt>0`，即"有料随挂钟烧"定稿口径的可视表达）。发射口＝实测喉口（见上 v2；v1 的"包围盒顶+8cm"已废弃）。
- **观察距离**：近（<35 m 接触探测）到中远（85 m 分量硬上限；60–85 m alpha 渐隐；渲染器距离剔除 85 m）。高炉是村庄/露天大件，主看 2–30 m 侧影。
- **主体与装饰层**：单层烟柱（主体即全部要求，v2 浮力模型）：喉盘出生（面积均匀 r≤15 cm）→ 出喉喷射 150 cm/s 指数衰减到终速 78 cm/s（τ=0.7 s，爬出凸缘前保持窄柱，smooth 门控后才锥形扇开）→ 双频翻卷随粒径增长 + `User.Wind` 积分漂移（随风飘动，τ=0.55 s 起步滞后）→ sqrt 生长、变浅灰、淡出。灰度层次由复用材质内的 Mantaflow 密度 + 逐粒子 Seed 翻卷/镜像提供，不做整片一色。
- **生命周期**：起烟 ~0.7 s 补烟；停燃 2.2 s 限流断供 + 末团 3.9 s 散尽后才 `Deactivate()`（与枪口持续烟同一语义，突然拔烟禁止）。构件脱落（`IsFalling`）即断供。
- **风/坐标空间**：发射器 local space＋分量恒等旋转 ⇒ 局部轴＝世界轴；v2 前风走共享 `ConfigureSmoke`→`WindAt`（天气风×0.45、屋面遮蔽 ×0.12、`User.Wind` 0.2 s 调度刷），粒子位置里做时间积分 → 高段随风倾斜、矮段竖直。v3 起炉烟条目 `bOwnWind`：同一 `WindAt` 基风 ＋ 雨天阵风由炉道自写（避免共享扫与阵风互相覆写），枪口/爆燃等其余烟行为不变。
- **随机散布**：逐粒子 `seed/var/u2` 三路 `Particles.UniqueID` ×黄金比 + `Engine.System.RandomSeed` 相位派生（爆燃烟已验收范式）：喉盘方位/半径、初速衰减、尺寸、旋转、透明度各自取值；不同炉子（不同系统实例）图案不同。
- **受保护的玩法**：冶炼数值、存档、UI、输入完全未动；烟不注册碰撞、不投影、不影响导航。

## 运行接入与预算

- 单一入口：`UFluidPresentationSubsystem::UpdateFurnaceSmoke()`（5 Hz 限流，挂在既有共享 Tick；无每炉 Actor Tick、无每帧全场遍历）。
- 构件经既有 spawn 委托/关卡装载登记（上限 32 座），**同时至多 6 个烟组件**（池满先置换"已断供散尽"里离视点最远的一炉，否则本炉暂不起烟）；组件挂在炉构件上随其销毁，`Deinitialize` 统一清理。
- 烟量/细节走共享预算：每 2.5 s 一次 `ConfigureSmoke(FX,16)`（令牌桶 72/180s 分配 `User.DetailReduction` 乘进 SpawnRate；风与接触平面同次登记）；接触近似复用 `User.SmokePlane0..4`（近处 35 m、0.2 s 轮询 ≤6 项×2 平面、共用 12 次/帧查询额度）——屋下烟会被压平，不穿屋顶（工作流同款近似）。
- 峰值单柱 ≤66 粒（v2：16/s×3.6 s + 补发余量，`max_particles_per_plume` 见回执）；CPU 发射器；纹理复用既有 8×8 图集（BC 无 mip 方案不变）；预载为 `OnWorldBeginPlay` 异步软引用（热路径无同步 Load）。
- 画质分级复用 `AllocateDetail`（低画质系数 0.4/0.65、35 m 外减半、85 m 外 0）。

## 源与资产

- 作者脚本：`Tools/Fluids/author_furnace_black_smoke.py`（幂等：稳定 metadata 标识 `Fireball.Assignments.*`/`FluidContact.*`/`FurnaceSmoke20260924`；只编译保存目标包；首稿 `EmitterSpawnScript` 自定义 `SpawnGroupCount×Engine.Environment.DeltaTime` 编译失败——SetParameters 表达式不绑定该外部变量——已改为项目验证过的 **SpawnRate 模块**并在脚本内自动退役旧模块）。
- 密度源：复用 `T_MuzzleSmokeMantaflowV14`（64 帧 Mantaflow，R 通道），材质复用已验收的 `/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke`（逐粒子 Seed 翻卷/镜像/边缘侵蚀/径向收边/深度收口）。不新增烘焙。
- 新资产：`/Game/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke`（922 KB，commandlet 编译保存成功，回执 `SourceAssets/FurnaceSmoke20260924/assets.json`、日志 `Saved/furnace_author2_run.log`）。
- 运行时源码：`Source/FPSGAME/WorldGeneration/FluidPresentationSubsystem.{h,cpp}`（FFurnaceSmoke 登记数组、FurnaceTemplate 软引用异步预载、UpdateFurnaceSmoke；无新增每帧遍历）。

## 构建与状态（如实）

- v2 状态（已达成）：用户实测确认黑烟可见、喉口对齐（"成功了"）。
- v3 状态（进行中，如实）：雨天阵风＋吹散/快散耦合两侧已改源（C++ RainGust/bOwnWind/User.Rainfall；资产 rain 门表达式与 Rainfall 参数声明）。**资产重作与构建由 `Tools/Fluids/run_furnace_v2_sequence.ps1` 排队**——编辑器关闭后自动重作（须 `FURNACE_SMOKE_SAVED`）再 `Build-Editor.ps1`；不覆盖运行中编辑器的已加载资产、不强关他人编辑器。
- 未运行游戏/PIE，无观感与性能验收：晴天＝v2 恒等；雨天形态请用户实测（可用天气调试命令切换下雨验证），参数（阵风幅度、撕裂、各雨量因子）在 `RainGust`/作者脚本表达式内。
