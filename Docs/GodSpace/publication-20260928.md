# 主神空间整理与源码发布 · 2026-09-28

本轮按用户要求归档废案、沉淀技能，并发布到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。唯一工作目录为 `D:/FPS3D/FPSGAME`；遵循 `WORKFLOW.md` 第 4–8 节，精确暂存，不夹带共享工作区其他改动。本文不是完整二进制备份或新的视觉验收记录。

## 当前状态

- 正式关卡仍为 `/Game/GameMaps/DayNight_Lighting`，主神空间布局已保存。保留丘陵；水池与草地测试地图及其自动传送门已退役。出生旋转使用具名 pitch/yaw/roll，仓库与丘陵门复用场景锚点。
- 下方连续海洋采用现有 Clearwater 喷泉波谱，近处网格位移与法线、中远处低成本衔接；不新增水体交互或模拟。当前制作资产已保存，没有本轮帧率测量。
- 下方云海最终未获用户认可，已隐藏。保留共享天气、天空、云实例及被引用的父材质/噪声，完整重建配置 `CLOUD_SEA_VISIBLE=False`。旧大地与固定补色不是恢复目标。
- 深蓝地毯 V2 已获用户明确认可，复用库内 Carpet 01，浅层 POM、配套高度/法线与受限细节采样已保存。
- 连续金属收边已导入并保存：主路 7 道、两侧各 3 道横条，端点/转角连通，细倒角与专用缎面金属；保留地毯。新结构为 8404 三角形，原为 5396，新增一个材质槽。本轮之前完成了用户要求的拼缝几何检查，尚未作游戏观感确认。

## 本机保留依赖及恢复顺序

1. 从合法本机备份恢复当前地图及其 World Partition 外部对象（如有）、`Content/Props/GodSpaceLayout20260927`、既有罗马柱廊/亭子/栏杆/喷泉/祭坛/仓库/传送门、`SubstrateMaterials` 织物、现有天空/天气/水体素材。不要用历史地图覆盖当前主场景。栏杆共享资产 `SM_RomanRail_200` 还包含本轮之前保存的简单盒碰撞修复。
2. 保留本目录的 `GodSpace_Layout_V1.blend`、`Exported` 库组件及 `exported_meshes.json`；它们是完整结构作者链的输入。`Integration/placements.json` 是当前作者布局参数，`saved_hub_inputs.json` 是需要从本机恢复的初始天空输入。旧 Preview 只表示历史 Blender 构图，不代表当前 UE 外观。
3. 地毯：恢复 `Integration/CarpetSources/T_Carpet_01_N.tga` 及合法的 `SubstrateMaterials/Textures/02_Upholstery/Textiles/T_Carpet_01_*`，用 `author_carpet_relief.py` 生产配套贴图，再由 `build_navy_carpet.py` 编译/保存。对应源/参数在 `carpet_relief.ush`。现有保存资产可以直接恢复，不必为恢复重新制作。
4. 金属条：保留 `Integration/FloorTrim/Structure_Before.blend`、`inputs.json` 和原始 FBX，它们是局部修订的必要输入，虽叫 Before 也不能归档删除。`refine_floor_trim.py` 产生 `Structure_TrimV2.blend`/FBX；`install_floor_trim.py` 为当次增量接入，带原资产散列与脏包保护，不能对已完成资产盲目重跑。全量出口 `export_accepted_layout.py` 已调用同一局部修订，`import_assets.py` 恢复四个槽及地毯 UV 密度。
5. 海面：恢复 `SourceAssets/ClearwaterWater20260926/waves.json` 与现有水体贴图。`build_reused_ocean_spectrum.py` 从该波谱产生 `OceanSwell.hlsl`，`author_distant_ocean.py` 生成网格；`import_distant_ocean.py`/`ocean_mesh_budget.py` 完成材质和网格预算。Git 中保留已生成的 HLSL；原始波谱及其他任务的制作链可能需从本机另行恢复。
6. 地图入口 `apply_map.py` 和 `configure_cloud_sea.py` 均需要原有本机依赖；默认云海保持隐藏。不要为了恢复海面重新开启云海。后台制作沿用 `run_background.ps1` 的进程占用与批次互斥；已有编辑器时使用既有 MCP 批次，不另起进程覆盖已加载包。

## 归档

本次移动 **48 个文件，421122297 字节** 到 `trash/godspace-publication-20260928/`，逐文件散列均匹配。清单：[godspace-20260928.json](../AssetArchives/godspace-20260928.json)。内容包括被替代的大地制作链/纹理、旧云密度与补色分支、未选 Carpet 02、旧波浪候选、旧结构导出、自动备份及已执行完的源码补丁器/源快照。

本次没有移动任何 UE 包。当前云海被隐藏仍存在资产引用，故不按废案搬空 Content；喷泉、天气、当前地毯与当前模型作者输入保持原位。过去的地图退役/备份路径只代表历史记录，不承诺这些旧备份仍完整存在。

## 公开内容、许可与检查边界

- 公开本任务六个运行源码文件的路由/锚点/云层高度保护，以及 `DefaultGame.ini` 中草地测试地图 cook 条目的删除。共享配置的其他改动保持未暂存。
- 公开当前作者脚本、HLSL/USH、布局参数、说明、48 文件散列清单与 SKILL；仅提取本次忽略规则及资源恢复段落，不提交其他任务的修改。
- 模型、材质包、贴图、FBX/Blend、密集采样、原始源码快照、构建/MCP 回执、预览与 trash 保留本机。现有 Fab/Epic 素材的使用权不等于原资源的公开再分发权。
- 云 HLSL 引用 Takram 的高度整形/侵蚀思路，保留作者署名、锁定提交来源及完整 MIT/依赖许可文件；其 WebGL 源参考与纹理不随本次发布。工程和个人 SKILL 同步本次新增内容，其他差异不覆盖。
- 仅执行用户要求的归档与发布检查：精确清单、暂存差异/空白、文件大小、敏感信息、许可、未发布历史以及远端回读。没有为整理重新构建、启动 UE、运行游戏或截图。既往构建与资产保存记录分别见各功能文档。
