# M 系列整理、源码发布与恢复（2026-10-08）

本次整理本对话的楼梯移动、螺柱攻击、四只高面数怪物接回及局部修复、悬钟/伏窥者死亡和移动调速成果。源码真源为 `D:/FPS3D/FPSGAME`，发布到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。只补齐本轮尚未发布的源码、工具、配方、记录及 SKILL；部分角色实现已随先前主线提交发布，不重复覆盖。共享文件中的其他会话 APS 寻路、UI、武器及未发布玩法不在本次提交内。

## 当前制作结果

| 范围 | 当前版本与恢复说明 |
|---|---|
| 地面移动 | M10/M25 跨阶与导航 40 cm，M14 独立 125/300 cm 导航，保留跨阶 Mesh 平滑与足端支撑；见 [楼梯修订](m-series-ground-traversal-20261006.md) |
| 螺柱撕咬 | V21：探嘴 0.5 s、突伸 0.25 s、0.8 s 闭合命中；原蓝图、音效和动画已保存；见 [V21](SpiralPillarM14BiteV21.md) |
| 螺柱下砸 | V22：0.35 s 前摇、0.2 s 砸落，命中存活玩家眩晕 2 s、受碰撞约束击退 5 m；见 [V22](SpiralPillarM14SlamV22.md) |
| 螺柱旋转 | 在 V20 上额外扩大 25%，外侧有效半径 248.625 cm，起手 308.75 cm；见 [范围修订](SpiralPillarM14WhirlwindRange20261007.md) |
| 螺柱几何 | TeethRemeshV4，LOD0/1/2/3 为 251981/101737/41965/17801 三角面；见 [完整口部修复](m14-teeth-remesh-repair-v4-20261007.md) |
| 其余三只几何 | AnatomyRepairV5：M10 202805/79083/30241/11765，M09 274092/123960/64650/52030，M08 233324/88500/34500/13798；见 [结构修复](three-remesh-anatomy-repair-v5-20261007.md) |
| 悬钟死亡 | V26：从实际节点向下找支撑，空中节点不因绑定高度低而固定；见 [重力修复](hanging-bell-death-gravity-v26-20261007.md) |
| 伏窥者死亡 | V13：地面死亡约 0.77 s 动画前段后交软体，墙/顶/空中立即下落；见 [死亡衔接](lurker-m08-death-lead-v13-20261007.md) |
| 沉匣/涡电匣移动 | 两者 110 cm/s；M10 自有移动/原地转向 72/60 deg/s，M25 150 deg/s，动画和补步同步；见 [移速翻倍](coffer-movement-double-20261007.md) |
| 盲祷者/螺柱移动 | M07 步行/追击 82/168 cm/s，M14 112 cm/s、75 deg/s；保留源步幅、相位和走跑上限；见 [调速落盘](m07-m14-movement-tuning-20261007.md) |

以上是作者导出与已有保存/构建记录，不是本次重新测出的运行效果或帧率。四只软体尸体均只保留已重绑的 LOD0。共享定姿 LOD 刷新代码支持多 LOD PoseableMesh，当前尸体资产未使用该扩展。

## 减面恢复顺序

1. 从合法完整备份恢复四只原模型及加工母版、正式骨架/物理/动画、当前软体代理和贴图。对应母版为 M14 `ProductionV15/Authoring/M14_SupportSkin_v15.blend`、M09 `ArmContinuityV16/Authoring/M09_ContinuousArms_V16.blend`、M10 `SurfaceRigV5/Delivery/M10_SurfaceRigV5_Editable.blend`、M08 `CanineRigV03_20261004/M08_CanineRig_Skin_V03.blend`。路径根由作者工具明确指定，不能用原始生成模型替代这些后期结构。
2. 四个用户 GLB 当前在 `SourceAssets/AlienGeometry20261006/RemeshV3/<ID>/Input/` 留有副本；缺失时作者工具从用户 `Downloads/重拓扑` 指定文件名读取。它们来自 Meshy 原始模型直接减面。
3. 需要重建时，以 Blender 后台执行 `Tools/MonsterAI/read_blender_geometry_sources.py`，生成 `BlenderV2/source_inputs.json`；再按物种执行 `author_meshy_remesh_v3.py -- <ID>`，产生保留 rig、权重、修形及 UV 的中间 Blend、纹理和元数据。不是重新生成动画。
4. 当前几何用 `Tools/SpiralPillarM14/author_teeth_remesh_v4.py`（M14）和 `Tools/MonsterAI/author_anatomy_repair_v5.py -- <ID>`（其他三只）制作。V4/V5 仍读取 V3 的 Blend、材质记录以及 V3 公共函数，不能整包归档 V3。离线完成全部几何和 FBX 后再进入 UE。
5. 新环境缺少 RemeshV3 材质时，先按 V3 导入阶段恢复配套材质，再用 `Invoke-MeshyRemeshV3.ps1 -Species <ID> -Stage import -Revision M14TeethV4` 或 `AnatomyRepairV5` 保存当前网格；活体正式路径保留。已完成当前修复的环境不要再运行旧版全量导入覆盖网格。
6. import 阶段输出精确 UE 坐标 `surface.bin` 和当前 `cage.json`；用 `embed_meshy_remesh_v3.py <ID> <当前修订根目录>` 离线制作表面绑定，再以同一入口 `-Stage corpse` 保存尸体与死亡引用。M14 代理来自 ProductionV19；其他三只来自 `SourceAssets/MonsterSoftCorpse20261005`。尸体、独立骨架、DataAsset 和动态法线材质是一套交付。

活体正式路径分别为 `/Game/Monsters/SpiralPillarM14/SK_M14_SupportSkin_v15`、`/Game/Monsters/M10Mawcrawler/SurfaceRigV5/SK_M10_SurfaceRig_V5`、`/Game/Monsters/HangingBellM09/V04/SK_M09`、`/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03`。新尸体位于 `RemeshV4Teeth/SpiralPillarM14` 与 `AnatomyRepairV5/<ID>`，不得回绑旧高面数尸体。

## 动作、蓝图与地图恢复

- M14 撕咬由 V15 母版制作 V21，V22 下砸继续读取 V21 Blend 内的原 V13 动作。两套 JSON 时序位于 `Tools/SpiralPillarM14`，音效作者与动画作者共用参数。依次通过 `Import-BiteV21.ps1`、`Import-SlamV22.ps1` 导入；保留其他攻击和当前低模资产。
- 楼梯制作入口 `Tools/MonsterAI/produce_m_series_ground_traversal.py` 保存三只蓝图和 DayNight/随机地牢地图导航，依赖当前 C++ 与 SupportedAgents 配置；不得把地图导航生成当作游戏通路验收。
- 范围、M10/M25 调速、M07/M14 调速依次由 `Complete-WhirlwindRange20261007.ps1`、`Complete-CofferMovement20261007.ps1`、`Complete-M07M14Movement20261007.ps1` 构建/保存。蓝图已有覆盖，只有编译原生默认值不能恢复完整结果。
- M09/M08 死亡为原生修订，不需重做动画；对应 `Build-DeathGravityV26.ps1` 和 `Build-DeathLeadV13.ps1`。构建不主动启动/重启 GUI 或运行游戏。
- 几何/移动只读排查工具保留供用户明确要求时使用，不放入默认导入或发布执行链。

## 归档与来源边界

39 个退役文件，共 1,192,843,083 字节，已移至本机 `trash/m-series-retired-20261008/`，逐文件 SHA-256 读回一致。清单见 [归档元数据](m-series-retirement-20261008.json)。其中包含中止 UE 内减面的 2 个脚本、2 个 LOD 参数资产、源包快照与过程记录，以及 V21 的一份 `.blend1` 自动备份。当前正式包未引用这两个 LOD 参数路径；没有移动现用模型、动画或 V3/V4/V5 重建输入。trash 本体不提交。

模型/PBR 来自用户 Meshy 原输入及其减面输出；M08 动作供体边界沿用 [Bonehead 来源说明](../ThirdParty/Bonehead-M08.md)。M14 新声音使用现有 AudioV01/AudioScout 的本地 CC0 Freesound 素材与原创合成层，具体来源记录仍在各 ProductionV21/V22 的 `Records/audio_authoring.json` 和原 AudioV01 中。脚本只描述处理配方，不公开这些素材或密集姿态数据，不把使用许可等同于原资产再分发许可。

公开原创 C++、Python/PowerShell 作者及导入器、小型时序 JSON、历史排查数据、文档与技能。GLB/FBX/Blend、纹理、声音、UE 包、密集绑定、DLL、日志和当前保存回执留在本机合法备份；仅克隆 Git 不能恢复可运行的完整内容。个人与工程镜像中的非人形减面、移动时钟、死亡交接和几何预算参考同步更新。

## 发布范围与未测试边界

本轮只执行用户要求的仓库整理、归档散列、提交差异/敏感信息/大小/依赖检查和远端读回。不启动 UE、重新导入、构建、游戏测试、截图或渲染。此前各项交付回执已记录必要构建与实际保存；本次精确提交子集没有独立编译或游戏验收，由用户测试。
