# M-10 沉匣整理与源码发布（2026-10-03）

按用户授权从唯一开发仓库 `D:/FPS3D/FPSGAME` 发布到 `https://github.com/allang2208/3D-FPS.git` 的 main。遵循 `WORKFLOW.md` 第 4–8 节及并行发布规则，只精确暂存 M10 内容，普通非强制推送；保留其他任务的源码和索引修改。

## 本轮成果

当前运行模型为 SurfaceRigV5，62 骨、眼口几何层次／口腔及组织修形、十段动作；RearGasV7 为八秒后躯攻击。V10 保留 1.5 m 咬击突进、提速转身及扩大／加快的淡绿原地毒雾；V11 让超出毒雾范围的远后方目标恢复导航追击；V12 增加多脚坡面／腹部支撑与逐脚落地，修订锁脚、抬脚、补步和膝面。F6 入口保持“沉匣 M-10”。

公开 M10 原生类、动画节点、制作／导入配方、共用 BT／战斗路由、眼球暴击入口、毒雾派生接口、导航配置与两份 SKILL 参考。M10 专用文件保留当前版本的状态／攻击时钟复制；共享受击组件的其他联机、玩家身体、生存和技能修改不夹带。

**公开接入边界：** 嚎叫受击后的 SAN／致残依赖尚未发布的玩家生存模块。该段保存为 [接入补丁](M10Integration/README.md)，没有应用到公共 `FPSCombatHealthComponent.cpp`；本机完整工程已接入，纯源码克隆不能宣称具备完整嚎叫副作用。原模型、材质／声音等资源也需恢复。

## 归档

共 20 个确认退役文件，391,004,827 字节（约 372.89 MiB），移入 `trash/m10-retired-20261003`。原路径、目标、大小、SHA-256、原因与替代物见 [逐文件清单](../AssetArchives/m10-retired-20261003.json)。移动前校验授权绝对路径，移动后每份散列一致。

归档包含三份 Blender 自动备份、已完成的一次性 PIE／编辑器脚本、两份空传输输出，以及被 V7 替代的 V6 四秒动作源／FBX／合同和旧混合导入脚本。V6 导入器原路径改为仅制作烟雾依赖，禁止重新绑定旧动作／18 秒冷却。本轮没有重新执行该整理后的导入器，现存正式 Content 和历史导入包保留本机恢复，未搬动 UE 包。

V1→V2→V3→V4→V5 的可编辑 Blend 与输入仍逐级被读取；V6 烟雾仍被 V8→V10 复制。不能按版本号移走这些制作输入。正式重建不读取 trash。

## 本机恢复顺序与来源

1. 恢复用户提供的 `Meshy_AI_M_10_Mawcrawler_1003020804_texture.glb`，原件副本及纹理在 RigV1；三视图参考在 References。无公开二进制再分发许可核准，不发布原图、生成图、Meshy 模型或其密集采样。
2. `RigV1/read_source_geometry.py` → `author_weights.py` → Blender `build_rig.py`。保留其 GLB／纹理、NPZ 和输出合同；作者脚本生成小型骨架／动作参数，不必依赖公开密集数据。
3. 依次运行 TurningV2 `author_turns.py`、CombatV3 `author_eye_regions.py`／`author_bite.py`、HowlV4 `author_howl.py`、SurfaceRigV5 `prepare_surface.py`／`build_surface_rig.py`；最后从 V5 制作 RearGasV7 `author_rear_gas.py`。旧阶段 Blend 保留是为了当前重建，最终绑定和游戏动作使用 V5/V7。
4. 常规 native 构建后，依序恢复 RigV1 材质／蓝图、V2/V3/V4 基础接入、V5 当前模型／动作、V6 仅烟雾、V7 后方动作、V8 淡绿效果、V10 扩散及 BP 数值。V9/V11/V12 是原生修订，无额外导入。RigV1 `produce_navigation.py` 恢复地图 M10 导航。分阶段脚本运行会临时使用历史绑定，完成整条链后才能算当前版本。
5. 共享依赖：手脑嚎叫 `/Game/Monsters/HandBrain/Audio/S_HandBrain_howl`；百目 SmokeVisibilityFixV21 图集／烟雾与 WorldSmokeV19 目盲 HLSL；既有怪物 BT、尸体预算、毒蛆中毒、玩家状态和 Niagara 制作桥。原图集、声音、模型和授权 Content 沿 `Docs/AssetSetup.md` 留本机，不公开再分发。
6. 最终资产：`/Game/Monsters/M10Mawcrawler/SurfaceRigV5`、`RearGasV7`、`FX`、`LocalGasV8`、`CombatPaceV10`，以及原 `BP_M10Mawcrawler`／AI 蓝图、材质和纹理。导航仍为半径 225 cm、高 450 cm 的保守胶囊规格，视觉低矮不等于能穿过低净高通道。

## 发布检查和事实边界

本轮只做归档和授权的推送检查：完整暂存差异、空白错误、文件范围／大小、敏感信息、许可边界、未推送历史及远端回读。未启动 UE、游戏、渲染、性能采样或重新构建。

此前 V12 本机 Editor/Game 构建均成功，回执在 `TerrainFeetV12/delivery.json`；源动作定点诊断不是运行验收。V12 地形／形变仍待用户测试，公开子集未单独构建。实际提交／远端 SHA 和检查记录保留在本机 `SourceAssets/M10ChenXia20261003/Publication20261003`。
