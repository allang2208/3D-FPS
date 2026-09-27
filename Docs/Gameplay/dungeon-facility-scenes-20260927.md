# 废弃设施房间组合扩展 — 2026-09-27

本轮把排水、通风和货运房间扩展为「现有房壳 + 功能设备组合 + 废弃状态」。保留现有普通房池、房间刚体尺寸、门洞和三路地下终点规则；不通过复制整间房来增加每种设备布置。

## 玩家可见变化

| 房间家族 | 三种功能布置 |
| --- | --- |
| 排水 Drainage | 泵组检修、过滤回收、应急供电 |
| 通风 VentilationLoop | 滤芯更换、风道拆换、风机供电 |
| 货运 FreightTransfer | 待运货物、装卸维修、备件周转 |

每种布置再选择中断检修、撤离废弃、应急封存三种环境状态之一，改变一组小道具及原有灯具亮度（100%、90%、85%）。这些是环境叙事布景，尚未增加维修交互、供电开关或封锁事件。

本轮为九种功能布置及其状态组合，不是新增二十七间独立房间。既有排水桥位和通风房壳/主门配方继续参与生成。单局只出现实际选中的家族及布置，不保证一次出现全部组合。

## 生成与空间约束

- `AuthoredDungeonRoomScenes` 在路线规划完成后，按地牢种子、模块序号和家族派生独立随机流，分别选择设备配方和状态。装饰变化不消耗路线规划随机流。
- 同一家族连续选择时，在有多个候选的情况下避开上次使用的配方及状态。没有场景配方的模块继续使用原数据。
- 选择结果写入布局节点的 `scene_recipe_id`、`scene_state_id`，图根记录 `room_scene_version=1`；目录模板本身不被运行时修改。
- 设备使用作者确定的房间局部摆放位置，按现有桥面、门口和可选侧门布局留出通行区域。`scene_keep_clear` 将设备占位交给原有散落装饰避让流程，避免杂物再占同一位置。货运台上摆放高度为 60 cm。
- 选中的零件继续走现有资源准备、分帧装配、实例化、导航准备及灯光调度流程，没有新增房间 Tick。

## 模型与成本

新增九款可复用组合件：泵组、过滤架、配电柜、维修台、货物垛、风管托架，以及备件盘、废弃面板、隔离标架。源模型由本项目 Blender 作者脚本制作，复用现有磨损金属、木材、橡胶等材质；没有新增外部下载资产或纹理库。

六种大设备带作者 UCX 简单碰撞，共八个凸包；三种小道具不参与碰撞、导航和投影。网格采用 Nanite，保留完整 fallback，并使用 Simple And Complex 查询模式。模型及材质均已保存。

每间适用房间最多添加两个大设备组合件和一个状态组合件，共三个网格组件。零散地面物品上限降至 8，物品簇上限降至 2，不增加灯具数量。这里的组件上限不等同于实际 draw call 数量。

## 制作与接入入口

批次目录：`SourceAssets/DungeonFacilityScenes20260927/`。

1. `Scripts/author_assemblies.py`：后台 Blender 制作九款 FBX、可编辑 `.blend` 和源清单。
2. `Scripts/prepare_recipes.py`：制作 `Config/scene-recipes.json`。
3. 必要原生构建：`AuthoredDungeonRoomScenes.cpp`、`AuthoredDungeonGenerator.cpp` 和装饰集成。
4. `Scripts/background_install.py`：适用的 UE Python commandlet 依次执行导入和配置保存。已有编辑器时使用现有 MCP 批次互斥，不另起进程覆盖已加载或未保存资产。

导入回执按源文件散列保留本批资源归属；不会用导入成功代替实际资产保存。无界面导入直接读取 BodySetup 的碰撞数组，因为 `StaticMeshEditorSubsystem` 在 commandlet 中不可用。

`install.py` 从地图当前生成器的目录增量更新，保留其他目录字段和硬引用，保存目标生成器 ExternalActor，然后写回 `DungeonRoutes20260922/Config/catalog.json`。不调用生成预览、PIE 或测试。当前已生成的布局不会在安装时被重建，下一次进入地牢生成新布局时使用新配置。

目录重建链 `DungeonRouteRepairs20260922`、`DungeonComposition20260926` 已挂接本批扩展；仅在本批 `Receipts/install.json` 为 `map_saved` 时恢复场景配方。旧路线安装器也收集场景配方及状态网格的硬引用。本轮没有运行旧安装器的生成预览流程。

## 已落盘与未测试范围

- `FPSGAMEEditor` 常规构建日志 `Saved/BuildEditor/build-20260927-181044.log` 包含两份本轮 C++ 的编译及基础 DLL 链接，结果 Succeeded，耗时 19.35 秒；并非只停留在 Live Coding 补丁。
- `Receipts/import.json`：`meshes_saved`，九款网格已保存。
- `Receipts/install.json`：`map_saved`，目标地图 `/Game/GameMaps/L_Dungeon_Randomized` 的生成器配置和引用已保存。
- `install-commandlet-02.log`：Python 执行成功，后台进程退出码 0。

遵照用户规则，本轮没有启动游戏、生成测试布局、运行多种子回归、截图、渲染或性能采样；实际视觉、通行和战斗体验由用户游玩测试。构建与保存成功不代表这些项目已验收。

此前走动/转视角卡顿尚无对应帧的 CPU/GPU 采样归因。本轮通过复用资源、限制组件和杂物成本控制扩展规模，没有改写资源流送架构，也不宣称卡顿已修复。
