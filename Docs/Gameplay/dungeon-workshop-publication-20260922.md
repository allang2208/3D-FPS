# 工作间阶段收尾与恢复（2026-09-22）

用户决定工作间开发先到这里。本次只整理废案、同步制作经验、提交并推送源码，不继续修改场景外观，不启动游戏、截图或渲染。以前文档中的预览、回执和阶段描述均属于对应日期，不能视为本次重新验收。

## 当前保留结果

- 地图：`/Game/GameMaps/L_Dungeon_Prototype`。
- 工作台：`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit`；实例 `DGN_WorkbenchKit_Main` 使用 `BP_Workbench_InUse`，另保留 Idle、Abandoned 两种组合件变体。29 个网格组件，桌面接缝及油壶／清洁剂瓶已进入配置与作者源。
- 货架：`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopRackPolish`；`DGN_Room_WS_RackContents` 使用 `SM_WSRack_Stock`，`DGN_WSDetail_Markings` 使用 `SM_WSRack_Markings`。连续线缆、同表面标签、固定种子及离线落定的 39 个散件保留。
- 最新完整可编辑场景：`SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonRooms_WithWorkbenchKit.blend`。这是本机制作文件，不在公开 Git 内。
- 现有保存回执：工作台 `2026-09-21T23:42:50.989934`，货架 `2026-09-22T08:58:19.063271`；均为接入保存记录，不能据此宣称游戏、视觉或性能通过。

组合件变体尚不等于地牢程序生成完成。本阶段只维护场景及可复用布景，未在本次收尾中新增地图拓扑、PCG 注册、战斗、事件或存档逻辑。

## 当前制作入口

工作台作者参数见 `SourceAssets/DungeonWorkbenchKit20260921/Config/workbench.json`；源对象与材质映射在 `Config/sources.json`，周边实例在 `Config/surroundings.json`，货架可编辑源覆盖关系在 `Config/surrounding-sources.json`。货架种子与布局见 `SourceAssets/DungeonWorkshopRackPolish20260922/Config/layout.json`。

恢复下列本机依赖后，工作台可用 `Scripts/build.py --assets-only --assemble-room-source` 制作模型及完整可编辑源；移除 `--assets-only` 才会经项目桥导入并保存 UE。货架对应 `DungeonWorkshopRackPolish20260922/Scripts/build.py --assets-only`，移除该参数会更新 UE 的两组网格与实例。`--materials-only` 是工作台的材质接入路径，不代表外部模型重建。

这些命令需要本机 Blender 5.1、Python 3.11 及已有源文件。`--assets-only` 仍会生成／覆盖作者输出，不是只读检查。此次收尾未执行这些构建命令。

## 保留的依赖链

| 本机目录 | 保留原因 |
| --- | --- |
| `DungeonWorkshopDetail20260921` | 货架复用其基础几何辅助函数、材质清单、标签图集和旧标记源 |
| `DungeonWorkshopTools20260921`、`DungeonWorkshopSculpt20260921` | 台面、灯具、固定件与整场景作者链的上游源 |
| `DungeonWorkshopSurface20260921` | 表面材质、标签与细节模型来源 |
| `DungeonWorkshopFabTools20260921` | 用户选择的 10 件工具原件、PBR 图集、适配与导入记录 |
| `DungeonWorkshopBenchPolish20260921` | 灯线、材质父级和完整场景装配输入 |
| `DungeonAtmosphereV2_20260921`、`DungeonRoomInteriors20260921`、`DungeonRuinEarthwork20260921` | 走廊、房间及土坡场景上游 |
| `DungeonIndustrial20260920`、`DungeonProps20260920` | V2 仍引用的女神像导入回执与资产；旧布局记录只作历史来源 |

上述目录的有效 `.blend`、导出、贴图、作者清单、输入快照和导入回执均保留本机。旧版本日期、隐藏状态或名称带 candidate 都不自动意味着废案。旧 UE 包及隐藏恢复实例没有在本次清理中批量移动；它们与保留的上游恢复数据一同留存。旧原型脚本不是当前工作间入口，勿用其重建覆盖现行布局。

## 废案归档

已将 38 个文件、7,102,360,003 字节移入 `trash/dungeon-workshop-20260922/`：16 个已被当前 `.blend` 替代且没有源脚本引用的 `.blend1` 自动备份、17 个被用户否决的发动机生成文件、5 个已完成使命的一次性导入／恢复／清理脚本。另复制保存退役前的发动机生成配置。

完整记录见 [archive-manifest.json](../../SourceAssets/DungeonWorkshopPublication20260922/archive-manifest.json)：逐文件包含原路径、目标路径、大小、SHA-256、归档原因和保留替代物，移动后已读回核对。没有删除文件，也没有释放磁盘空间；只是移入同盘归档。

当前 `DungeonRoomInteriors20260921/assets.json` 已移除 `repair_motor`，细化脚本也移除其专用面数分支。这样全量 V2 安装的前置依赖不再要求已否决的发动机源文件。退役的一次性脚本包含固化旧外部 Actor 包名的保存恢复逻辑，不应继续作为通用接入入口。

## Git 与素材边界

本次发布作者脚本、布局与组合件配置、制作文档、来源说明、归档索引和 SKILL。项目桥的 Python 批次接入与限长回执是制作入口的公共依赖，一并纳入。其他任务的未提交玩法、UI、武器、配置和技能修改不属于此次提交范围。

**公开 Git 不是完整工程备份。** 以下内容保留本机，不提交原始素材：

- UE `.uasset`／`.umap`、外部 Actor 包、Blender、FBX、GLB、贴图、截图、下载包及缓存。
- Fab 工具包、Quixel 表面和 RuralAustralia 土石等第三方源文件。商品免费、用户已下载或可用于游戏，都不等于获准公开再分发原文件。
- 本机原始 API 回执、下载元数据、调试日志和大型输入快照；工作台必要的作者配置单独按清单发布。

原件来源与本机恢复位置见 [provenance.json](../../SourceAssets/DungeonWorkshopPublication20260922/provenance.json)。原始资产许可依各来源及账户取得记录，本文不额外授予再分发许可。

从 Git 克隆后还必须恢复获许可的本机 SourceAssets、Content、相应插件和必要回执才能接入现行场景；不能只凭脚本宣称可以完整复建。现行工作间的恢复优先使用已保存组合件及周边定义，不回放历史场景排列覆盖新结果。

## SKILL 沉淀与检查范围

`asset-model-workflow` 增加成组布景入口；`ue5-pcg-building` 增加 [可复用室内组合件](../../skills/ue5-pcg-building/references/reusable-interior-assemblies.md)，包括支撑面与锚点、局部重建、自然线缆、贴牌闪烁、受约束随机、离线物理落定和 OFPA 保存归属。个人技能与工程镜像同步这些新增内容，不覆盖各自已有其他修改。

按用户明确要求执行本次归档与推送检查：精确路径、移动散列、完整暂存差异、空白错误、体积、敏感信息、素材许可边界及远端提交范围。未运行游戏测试、视觉验收、截图或性能测试，场景效果交由用户测试。
