# 裸皮感染犬：Meshy 重建

> 2026-09-25 整理：下文保留当时制作/诊断记录，旧路径不再表示现役入口。当前模型、动作、归档映射和恢复顺序见 [感染犬发布记录](InfectedDogPublication20260925.md)。

2026-09-24，用户否定旧狼换皮 V2 的粗糙外观，明确要求“按标准管线，走 meshy 工作流”。

## 当前制作路线

1. 使用 imagegen 内置工具生成同一裸皮犬的三个独立视角：前侧、左侧、后侧。细长裸尾、清晰肩胛/四肢结构、自然局部皮褶、低饱和病变绿、无毛片。参考图是概念输入，不代表实际 3D 产物。
2. 首个 Meshy 7.1 多图候选：2K 几何、4K 纹理、PBR 开启、移除烘入光照、关闭生成后的自动减面，保存原始高模。按当日官方文档预计 35 积分；实际以余额和任务 consumed_credits 为准。
3. 任务完成立即下载 GLB、FBX、PBR 贴图及服务预览，保存参数、任务 ID、来源、散列与余额记录。密钥只存在临时进程环境，任务回执剥离签名 URL 查询串。
4. 实际模型经用户选定后，冻结母版，再进行局部修整、游戏拓扑/UV、犬科骨架权重适配和 UE 接入。用户随后明确要求先尝试 Meshy 四足模板；当前改走官方 OpenAPI 的 `animation_type: quadruped`，详见下方记录。

保留已恢复的原 Run、转向、咬击等动作以及现有六维/感染三阶段机制。当前 V2 游戏资源保留作恢复点，本阶段不替换蓝图，不主动启动游戏。

## 文件

- 工作目录：`SourceAssets/InfectedDogMeshy20260924`
- 三视角参考：`References/01_front_oblique.png`、`02_left_profile.png`、`03_rear_oblique.png`
- 请求配置：`meshy_settings.json`
- 生产脚本：`meshy_pipeline.py`；临时凭据会话：`meshy_session.py`
- 生成回执与下载：`Meshy/candidate01/`

## 官方约束来源

- [多图生成参数](https://docs.meshy.ai/en/api/multi-image-to-3d)
- [积分价格](https://docs.meshy.ai/en/api/pricing)
- [自动绑骨限制](https://docs.meshy.ai/en/api/rigging)

## 状态

首个模型候选已生成成功并完整下载：`01a0d354-0532-73e3-816b-0ba74bfd089d`，端点 `/v1/multi-image-to-3d`，服务状态 `SUCCEEDED`，进度 100。任务实际消耗 35 积分，提交前余额 2038 积分，完成后余额 2003 积分；前后余额回执均已保存。临时凭据会话已退出，脚本未将密钥写入配置或持久环境。

`SourceAssets/InfectedDogMeshy20260924/Meshy/candidate01/downloads/` 已保存 13 个服务产物：GLB、FBX、5 张 PBR 贴图（基础色、金属度、粗糙度、法线、自发光）和 6 张服务生成的实际模型预览。`downloads.json` 记录各文件大小、SHA-256 和去签名来源 URL；`response.json` 保留任务回执。输入图完整提示词和来源见 `References/prompts.md`。

下载曾受本机 DNS 错误解析影响而中断；客户端通过 DoH 查询文件主机，并在单次下载中使用 SOCKS 本地解析和 curl `--resolve` 恢复连接，保留 HTTPS 主机名及证书校验，没有修改系统或代理设置。复用同一个任务继续下载，没有重复提交或额外生成消费。`download_error.json` 是已恢复的历史失败记录，最终文件清单以 `downloads.json` 为准。

首次生成阶段的交付：实际 Meshy 候选已落盘，当时尚未制作重拓扑、下颌/口腔分件、蒙皮骨架或 UE 导入资产。后续用户授权继续重拓扑及绑骨，当前进度见文末“本地绑定与权重”。服务自带预览不是 UE 游戏内效果。

来源：参考图为本任务使用 imagegen 生成的原创输入，3D/PBR 为用户提供的 Meshy 账户 API 生成结果；保留服务来源，不将其标注为第三方免费资产或宣称未经确认的账户授权等级。

生成参考图、生成 3D、用户选定、绑定与 UE 接入分别记录，不将参考图当作成品模型展示。

**最新阶段**：用户要求“继续完成工作”后，已继续制作下颌/口腔、21 个目标动作及 UE 接入。早期阶段的“未制作/未导入”说明仅记录当时状态；当前交付详见文末 CompletionV2。

## 后续适配约束

以下 Wolf 目标骨架是先前的本地适配方案。若采用 Meshy 四足骨架，应保留其原始绑定，另做旧犬科动作的骨链映射/重定向；不能将现成 Wolf 动画直接指定给不兼容的新骨架。

- 原骨架目标为 `/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf_Skeleton`。原狼只提供尺度、关节和动作适配参考，不再作为最终可见身体表面。
- 现有动作引用可从 `SourceAssets/InfectedDogRealisticSkinV2/appearance_before.json` 取回；Run/RunTurnLeft/RunTurnRight 使用 WolfV1 原动作，普通咬击使用既有 WolfV2 WeightShift。用户否决的 Gallop V3 不再接入。
- 生成姿态为闭口静立；后续制作需要处理上下颌、口腔/牙齿分件和咬击张口空间。不得把闭口生成网格直接绑到开口狼参考姿态。
- 生成后的高模保留；另做适合关节弯曲的游戏网格和局部权重，尤其肩肘、后膝/跗关节、颈根和尾根。不承诺仅自动转移权重就达到成品动作质量。
- 骨架参考姿态和现有动画不因换皮重写；如果新身体无法合理适配，先修目标网格或明确调整方案，避免再次出现用户已否决的四肢错位。
- 原模型 V2、六维属性、感染阶段、F6 稳定 ID 在新母版选定并完成接入前保持当前引用。

## Meshy 四足模板尝试（2026-09-24）

用户明确要求“尝试用 meshy 的四足动物模板绑骨”，授权在 candidate01 上继续制作该绑定候选。本轮范围是服务重拓扑、四足模板绑骨和结果落盘，未要求 UE 替换或动作验收。

- 官方网页教程列出 `Quadruped Dog`；[OpenAPI 定义](https://docs.meshy.ai/openapi.json) 的 `RiggingRequest.animation_type` 枚举为 `biped` / `quadruped`。公开说明页面仍写人形限制，和机器可读定义不一致。完整定义快照保存为 `SourceAssets/InfectedDogMeshy20260924/meshy_openapi_20260924.yaml`，以真实提交与服务回执判定本次结果。
- 原始 GLB 的索引计数为 383,356 三角面，超过接口 320,000 面上限（说明页面采用更保守的 300,000）。保留原高模，先通过 `/v1/remesh` 生成 `quad`、目标 50,000 多边形的副本，格式 GLB/FBX。
- 副本成功后通过 `/v1/rigging` 提交，明确传入 `animation_type: quadruped`，`height_meters: 1.0`。该高度仅为此绑定候选的整体高度，不代表已经按 UE 角色胶囊定标。
- 生产脚本 `meshy_quadruped.py`，目录 `Meshy/candidate01_quad50k` 与 `Meshy/candidate01_quadruped_rig`。每阶段保存请求、任务 ID、服务回执、下载散列与前后余额；失败不自动改走人形，不重复提交已有任务。
- 当前状态：Meshy 重拓扑成功并保存 8 个服务产物，任务 `01a0d363-3cb2-7671-bb86-23d29502718e`，实际消耗 5 积分；四足绑骨 POST 返回 HTTP 422，姿态识别失败，未生成绑骨任务或骨架文件。详细对照请求及网页/API 流程差异见 [API 排查记录](InfectedDogMeshyApiDiagnosis20260924.md)。
- 用户要求网页由自己操作、继续排查 API。之后的网页登录回复不代表授权恢复网页操作；本轮只完成 API 诊断及文件记录。

## 本地绑定与权重（2026-09-24）

用户进一步明确“那你来完成绑骨和权重设置”，已使用 Blender 5.1.2 后台完成本地绑定及实际模型导出，不再等待 Meshy 四足接口。

- 输入为 Meshy 重拓扑任务的真实四边面 FBX，保留其表面、UV、自定义角点法线和 PBR。根据新犬自身形态设置独立参考姿态，没有将旧狼身体恢复为可见网格。
- 已制作 39 根骨骼（38 根变形骨），覆盖身体、四肢、头颈、双耳和六段尾链。权重采用骨热初始求解、解剖区域隔离、关节邻接平滑、脚掌权重整理及四影响归一化。
- `SourceAssets/InfectedDogMeshy20260924/LocalRig/` 已保存可编辑 `.blend`、带骨骼/权重 `.fbx` 和 `.glb`、纹理、完整骨骼制作记录及旧 Wolf 的语义映射表。不是仅提交制作脚本。
- 母版有 49,678 顶点、49,989 多边形，其中 48,297 四边面；游戏导出沿用 Meshy 原始 99,360 三角面表面，以对应位置传递权重。
- 当前闭口模型的上下吻部随 Head 整体运动；尚无独立下颌/口腔，不支持把现有绑定直接当作张口咬击成品。旧动作也尚未重定向。
- 当前交付范围是本地身体绑定及权重，未执行 UE 导入/替换、动作或游戏测试、验收渲染。旧 V2 与六维/感染玩法接入不改。

详细使用说明：[LocalRig/README](../../SourceAssets/InfectedDogMeshy20260924/LocalRig/README.md)。生产工具：`Tools/InfectedDog/author_meshy_local_rig.py`。

## CompletionV2：下颌、动作及 UE 接入（2026-09-24）

用户明确要求“继续完成工作”，已补齐先前身体绑定阶段留下的攻击器官与引擎接入。

- 在同一 Meshy 身体上切开唇线，增加下颌骨、上/下口腔内壁、舌头与 36 枚牙齿；嘴角后方保留连通皮肤并过渡权重。总骨骼 41 根，新增的非变形 `Wolf_-Head` 挂点保留现有战斗代码的头部定位合同。
- 从实际现役 WolfV1 与 WolfV2 BiteWeightShift 导出源动作，完成 21 个目标动作的 60 Hz 烘焙；继续使用旧 Run/左右转向，未恢复 Gallop V3。新下颌沿源口吻骨的时序驱动，按闭口参考校准并限幅至 42 度。
- 已通过后台 commandlet 制作并保存 `/Game/Monsters/InfectedDog/MeshyV2` 下的新网格、独立 Skeleton、PhysicsAsset、皮肤/口腔/牙齿材质、LOD 设置和目标动作。LOD0 保留近景表面，另制作 45%/16% 三角面预算的两级远距 LOD。
- 正式 `/Game/Monsters/InfectedDog/BP_InfectedDog` 绑定 `DA_InfectedDogMeshy_AnimationSet`。复制既有动作合同与命中窗口；步幅参考速度按新模型前后位移比例调整。六维、感染阶段、F6 ID、AI 和角色移动数值保留。
- 原始 Meshy 文件、V1 身体绑定、旧 V2 外观均保留。`CompletionV2/Before/BP_InfectedDog.uasset` 和 `appearance_before.json` 保存这次切换前的恢复点。
- 本轮未打开交互 UE 编辑器，未启动 PIE、游戏测试、动作预览或验收渲染。资产保存和接入已经执行，尚不代表视觉、接地、穿模及布娃娃已获验收。

完整源文件、制作过程和当前保存回执见 [CompletionV2/README](../../SourceAssets/InfectedDogMeshy20260924/CompletionV2/README.md) 及同目录 `installation.json`。当前引擎实际运行版本记录于本轮 commandlet 日志为 UE 5.8.3。

## F6 显示“生成成功”但不可见：根骨骼单位修复（2026-09-24）

用户要求排查并确认面板提示成功但看不到感染犬。运行日志中的 `BP_InfectedDog_C_0/1/2` 已启动怪物行为树，F6 的注册、生成和 AI 初始化已执行。静态网格范围高 100 cm；动画求值暴露了首次错误：绑定根骨骼缩放约 100，而全部新 FBX 动画的根关键帧缩放为 1。Blender 容器保存的米/厘米转换在骨架导入与动画单独导入之间丢失，模型随动画缩成 1/100，头部待机高度仅约 0.754 cm。

- `Tools/InfectedDog/meshy_animation_units.py` 在导入后将根缩放对齐绑定根，保留动画时长、旋转、位移和所有子骨轨道。重复执行不叠乘；`install_meshy_completed.py` 已接入此处理。
- `fix_meshy_f6_scale.py` 已实际修复并保存 MeshyV2 下全部 21 个动作。修复前资产保存在 `CompletionV2/BeforeF6RootScale`，保存回执为 `CompletionV2/f6_scale_repair.json`。没有放大 Actor、改胶囊或绕过生成条件。
- 在独立后台进程重新加载保存后的资源，针对 21 个动作的起点、中点和终点，分别读取源数据与运行时压缩数据，共 126 个采样。根缩放与绑定根误差为 0；压缩待机头部高度恢复至约 75.373 cm。结果保存在 `Saved/InfectedDogMeshy/F6ScaleReadback.json`，修复和读取 commandlet 均正常退出。
- 本次只执行用户要求的不可见问题诊断及相关资产读取，未启动新的编辑器/PIE、未生成预览，也未进行战斗或整体动画验收。F6 画面由用户再次查看。

## Fox Run V1：只替换奔跑（2026-09-24）

用户选定第一款 Mesh2Motion Fox Run，要求先替换奔跑观察。已从官方 CC0 动画文件的 `Run` 提取循环，按现有裸皮感染犬的参考姿态、肢长和脚掌位置重定向，在 Blender 后台以 60 Hz 烘焙并导出独立 FBX/可编辑 Blend。

- 已通过现有编辑器的互斥桥实际导入并保存 `/Game/Monsters/InfectedDog/MeshyV2/FoxRunV1/A_InfectedDogMeshy_FoxRunV1`，并保存正式 `DA_InfectedDogMeshy_AnimationSet` 的新引用。
- 只更新 `Run`、`RunTurnLeft`、`RunTurnRight`；左右转向沿用同一新循环，由角色转向驱动。其他动作，包括 `AttackRunBite`，保留现有引用和命中窗口。
- 新动画步幅参考 `run_speed` 为 607.832372 cm/s，角色实际追击速度、其他混合参数不变。导入时已执行现有根单位适配，将根缩放 1 恢复为绑定根约 100。
- 模型、皮肤、权重、骨架、六维与感染逻辑均未修改。旧动作、替换前的数据资产备份和引用快照保留。
- 本轮未启动新编辑器、PIE、游戏测试、预览或渲染；用户自行查看游戏表现。

来源许可、母版、生产入口、保存回执及恢复说明见 [FoxRunV1/README](../../SourceAssets/InfectedDogMeshy20260924/FoxRunV1/README.md)。此处为当前奔跑来源，覆盖上文 CompletionV2 的旧 Run 接入状态。

## 后续：受击血液与 Godot 原动作适配

用户反馈 Fox 跑姿仍不自然，并提供受击血液方块截图。已修复共享血迹材质的 HLSL 保留字编译错误及 Substrate Coverage 漏接，保存正式资产；奔跑改为 Godot 原始 Gallop 对裸皮犬的直接适配 GodotRunFitV2，保留模型、权重与其他动作。两项已后台落盘并完成本次授权的针对性数据回读，未运行游戏验收。当前奔跑入口和根因分析以 [本轮修复记录](InfectedDogRunBloodFix20260924.md) 为准，FoxRunV1 仅保留为历史版本。

## GodotRunNaturalV3：继续细化奔跑自然度

用户反馈 GodotRunFitV2 有所改善，要求再优化得自然一些。已在同一原始 Gallop 上制作 V3：平滑源控制轨迹，稳定支撑期足端行程和脚掌朝向，柔化后跗关节到达腿长限制时的过渡，收敛身体与头颈起伏，增加肩胛配合和沿原动作的尾链延迟。循环仍为 17/30 秒，烘焙提升至 120 Hz；没有改绑骨、权重或其他动作。

新动画 `/Game/Monsters/InfectedDog/MeshyV2/GodotRunNaturalV3/A_InfectedDogMeshy_GodotRunNaturalV3` 已通过现有编辑器互斥桥导入、完成根单位适配并保存。正式 AnimationSet 的 Run、RunTurnLeft、RunTurnRight 已更新；动画步幅参考速度为 286.754932 cm/s，角色移动速度和其余游戏参数保留。

GodotRunFitV2 和切换前数据资产备份均保留。本轮未执行测试、预览、渲染或 PIE，制作与保存完成，实际自然度由用户试玩确认。当前入口、参数和落盘记录见 [GodotRunNaturalV3/README](../../SourceAssets/InfectedDogMeshy20260924/GodotRunNaturalV3/README.md)。

## 犬科基线认可及狩猎升级（2026-09-25）

用户随后确认 NaturalV3 基本成功，可作为四足犬科模板，并要求参照突变体 3 优化感染犬的飞扑提前量、普通 / 飞扑判定及寻路索敌。已保留当前模型与动作，完成原生狩猎配置、共享寻路适配、常规 Editor 构建及正式感染犬蓝图保存。具体范围、参数与未测试边界见 [感染犬狩猎升级](InfectedDogHunting20260925.md)。
