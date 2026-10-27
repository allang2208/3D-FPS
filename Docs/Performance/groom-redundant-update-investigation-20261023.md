# 毛发重复实例与未变化输入更新排查

日期：2026-10-23。范围为当前项目源码、配置、本机 UE 5.8 源码和已有 2026-10-22 地牢采样/崩溃日志。没有修改游戏或引擎代码，没有编译、启动 UE、运行 commandlet 或测试。

## 结论

1. 当前原生创建链与配置中没有发现同一角色重复创建同一 Groom、或换发型后旧 Groom 继续注册渲染的证据。
2. 已确认本机毛发更新入口没有按最终姿势相等来跳过插值；具有形变资源、通过可见性/阴影条件的实例仍走更新。这是可研究的缓存机会，不能据此把旧采样全部插值耗时认定为冗余。
3. 确认一个配置 API 使用问题：项目调用 `SetEnableSimulation(false)`，却未开启该方法要求的 `SimulationSettings.bOverrideSettings`。旧崩溃日志明确记录调用未生效的警告。此前“玩家毛发物理模拟已关闭”的结论应修正为“代码尝试关闭，但实际仍取决于资产设置”。这不等于已经证明模拟在运行。
4. 帽子/头盔遮盖的头发仍保留隐藏投影资格。其不可见不代表不参与 GPU 工作，直接取消该资格也不能宣称画质不变。

## 1. 实例、配置与生命周期

| 项目 | 当前证据 |
| --- | --- |
| 原生创建入口 | 项目 C++ 中仅 `FPSPlayerBodyAppearance.cpp` 创建 `UGroomComponent`；`FPSGAMECharacter.cpp:261` 创建一份原生 PlayerBody 组件。未读取运行中的蓝图组件树，不把此结果扩展为所有运行时实例的绝对计数。 |
| 实际外观配置 | `Content/ColdSteelData/player_body.json:5021` 起为 Jason：固定眉毛、睫毛各一套；`curly_fade` 再加一套头发，总计三套；`bald` 只有前两套。各组合按 asset + binding 核对，没有重复条目。当前该配置无发布的 `body_variants`。 |
| 相同请求 | `FPSPlayerBodyAppearance.cpp:85` 对已应用或仍加载的同一外观直接返回；123–128 行使用请求代号、取消旧 handle 和回调代号判断，过期回调不能重新创建旧发型。 |
| 切换外观 | 156 行先逐个 `DestroyComponent` 并清空 `HeadGrooms`，随后才创建替代组件。 |
| 销毁语义 | 本机 `ActorComponent.cpp:2153` 的 DestroyComponent 会注销组件、移出 Actor 的实例/拥有组件集合并标记销毁；`GroomComponent.cpp:3559` 的 OnComponentDestroyed 会释放毛发资源。不存在“这里只调用 DestroyComponent，因此一定遗留在实例数组里继续渲染”的问题。 |
| 历史日志 | 崩溃日志中，DayNight_Lighting 与 L_Dungeon_Randomized 各出现 GroomComponent_0、1、2 的一次模拟设置警告。它们属于不同地图，不应算为同一场景六份毛发。日志不是完整实例清单。 |

GPU 清单里的多份 `Hair.TransmittanceNodeData`、`Hair.CompactNodeData` 是标记为 Transient 的渲染资源条目，没有 Groom owner 身份；不能据同名资源条目数量推断重复角色毛发或物理显存泄漏。

## 2. 未变化输入仍进入更新的路径

- `FPSPlayerHeadAnimInstance.cpp` 使用 CopyPoseFromMesh 跟随身体，脸部仍保留 RigLogic。角色不移动不能等同于头部/表情最终顶点不变。
- `GroomComponent.cpp:3757` 的 TickComponent 在 RegisteredMeshComponent 存在时标记渲染变换，提交变换/LOD命令；部分 buffer swap 模式还标记动态数据。没有最终姿势相等判断。
- `GroomManager.cpp:1325` 令 `bNeedDeformation = Strands.DeformedResource != nullptr`，它表示存在形变资源，并非本帧输入发生了变化。
- 1437 行的绑定三角形更新、1565 行的发丝插值与 1700 行的切线更新，按绑定类型、形变资源、cache 等条件执行，没有和上一帧最终形变输入比较。
- 3314 行按 IsShown / IsShadowCast / 隐藏时的间接照明贡献剔除实例，已经完全不贡献画面的实例并非必然还走全部 GPU 渲染流程。

因此，安全缓存要同时覆盖最终头部形变（骨骼、Morph、RigLogic、Mesh Deformer）、模拟/缓存状态、绑定资源、LOD/流送曲线数量，以及当前/上一帧位置和运动矢量。视角改变可能暴露新曲线；世界变换、灯光和阴影需求也不能被“骨骼没变”一并冻结。只停组件 Tick 无法替代这套渲染侧条件。

## 3. 模拟开关调用未生效

项目 `FPSPlayerBodyAppearance.cpp:185` 对新建的原生 UGroomComponent 调用 `SetEnableSimulation(false)`，但没有设置 override。

本机 `GroomAssetPhysics.h:408` 默认 `bOverrideSettings = false`。`GroomComponent.cpp:2027` 的 SetEnableSimulation 仅在 override 开启时改变 solver 设置，否则只打印警告；1534 行 IsSimulationEnable 在未覆盖时读取资产设置。

历史证据：

`Saved/Crashes/UECC-Windows-9254CCF046A53FBAD9F3D784B424156C_0000/FPSGAME.log:3236–3238`

这三行明确指向地牢 FPSGAMECharacter_0 的 GroomComponent_0/1/2，提示必须先启用 override 才能启停模拟。当前 Saved/Logs/FPSGAME.log 也包含相同警告。

修正 API 使用前需要明确各资产实际有效的模拟状态。若资产原本启用了动态模拟，直接强制关闭可能改变当前发丝运动，不能自动归入无损优化。本轮没有加载资产到 UE，也不把调用失败推断成资产模拟必定开启。

## 4. 遮盖后的头发仍保留投影资格

`FPSPlayerBodyAppearance.cpp:233–236` 先给所有头部组件应用世界身体阴影策略，再按 `covers_scalp_hair` 隐藏头发。`FPSBodyEquipment::ApplyShadowFlags` 同时设置 CastShadow 与 bCastHiddenShadow，因此遮盖头发没有单独撤销隐藏投影资格。

当前配置中 blue_mage_hat、steel_armet、ranger_feather_hat、field_hat 都声明覆盖头发。本机 `PrimitiveSceneProxy.cpp:1609` 的 IsShadowCast 允许隐藏投影组件绕过普通游戏隐藏判断；毛发管理器又以阴影资格保留实例，可能继续形变与体素化。

这是明确的保留更新路径，但不是“确认可以无损删除”的证据：帽子与头发的实际投影、透光和间接光贡献仍可能不同。第一人称 OwnerNoSee 的普通头发更需要保留自身阴影。

## 5. 旧采样重新按完整 GPU 帧统计

来源：`Saved/MantisCrashHallDiagnosis20261022/trace/ordered/gpu-scopes.jsonl`；窗口沿用 `gpu-analysis.json`，只计完整 Graphics GPU Frame 内的事件。

| 范围跨度 ms / 完整 GPU 帧 | 首波前 172 帧 | 首波后 5–10 秒 77 帧 | 最后窗口 200 帧 |
| --- | ---: | ---: | ---: |
| Hair | 1.244 | 5.935 | 5.782 |
| HairInterpolation(Strands) | 0.616 | 4.188 | 3.907 |
| HairStrandsInterpolationCurve | 0.209 | 2.156 | 1.932 |
| HairStrandsVoxelization | 0.157 | 1.461 | 1.593 |
| HairStrandsVisibility | 0.440 | 0.242 | 0.239 |
| CommitHairRayTracingGeometryUpdates | 0.192 | 0.289 | 0.215 |

各范围存在嵌套，不能相加。HairInterpolation 大范围平均出现次数为 0.884 → 1 → 1 次/帧；HairGuideInterpolation 为 2 → 2 → 2 次/帧。这不支持“整个毛发阶段每帧重复执行了数倍”的说法，但每个范围内部可包含多个实例，不能由范围次数推断实际 Groom 数量或发丝工作量相同。

旧报告记录的 Jason head 网格为一份；逐 Groom 组件身份、有效模拟状态、发丝点数与姿势是否变化均未导出，buffer_observation 也不是毛发输入变化记录。因此目前不能量化静止缓存的命中率、精确归因到某套毛发，或承诺可回收 4.188 ms。

## 后续优先级

目前无需凭猜测删除“重复毛发”。若继续优化，先补齐实际 Groom 身份、有效模拟状态与最终形变变化记录，利用用户后续采样确认目标；对已确定的完全静止输入，再做保留全部画面贡献的形变缓存。不要直接关闭全部 Tick、隐藏毛发阴影、RBF或物理模拟来冒充去重。
