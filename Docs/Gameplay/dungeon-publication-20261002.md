# 主题地牢开发收尾与源码发布（2026-10-02）

本轮发布本对话的焚化处理厅与停尸房、数据档案中心、解剖教学剧场、烟气净化站、货运仓库，以及三条固定主题路线、错层坡道、翻越修正、出征面板和全战斗房封门改动。当前运行代码已在公共主线具备基础文件，本轮直接提交其增量和新增文件，不再叠加旧版运行交接补丁。

## 当前入口和制作链

正式地图为 `/Game/GameMaps/L_Dungeon_Randomized`。三条核心为货运转运间 → 货运仓库 → 地下车站、排水间 → 隔离病区 → 解剖教学剧场、破损支护室 → 焚化处理厅 → 净化站；各路核心前后各 1–2 间基础设施房。档案中心是共同终点，清除任意完整路线与档案中心后进入 Boss。

主目录是 `SourceAssets/DungeonRoutes20260922/Config/catalog.json`。每个新主题目录的 README 标明当前入口；扩展链由 `DungeonRouteRepairs20260922/Scripts/extend_catalog.py` 接房间，再由 ThemedRoutes 接 SplitLevels，最后限制货运专用房资格。部分扩展读取本机成功安装回执后才启用；公开仓库不附带这些回执，不应伪造回执来跳过真实资产导入。

恢复合法本机素材后，按各目录的作者脚本、网格导出、资产导入、生产目录安装顺序处理。样板已退役，不再运行历史独立地图安装器。生产目录引用的上游房壳、材质、灯具、医院扫描血迹及家具依赖仍需恢复。三份 catalog 是对应重建入口的快照，不是三套不同路线算法。

## 废案与保留物

本轮新增归档 **112 份、560,266,172 字节**，位于 `trash/dungeon-closeout-20261002/`：85 份改造前快照、11 份 Blender 自动上次保存、16 份已完成的样板退役、作者迁移或编辑器上下文脚本。逐文件原路径、归档路径、大小、SHA-256、原因和保留替代物见 [归档清单](Publication20261002/archive-manifest.json)，移动前后散列一致。

此前各房间样板清理属于已完成历史，本轮不重复恢复或执行退役脚本。历史文档中的 `retire_subject`、`editor_target_state` 和 `retire_warehouse` 等路径现在应按归档清单查找，仅作回溯。正式 Blender 源、仍参与重建的初版母件/助手、FBX、纹理、生产 UE 包和安装回执保持原位；旧日期或 V1 名称不等于废案。没有删除整个 Design 目录，也没有批量移动生产 Content。

## 技能沉淀

- [主题路线与房间闸门](../../skills/ue5-pcg-building/references/themed-routes-and-room-gates.md)：固定组合、货运专用池、错层几何与预算、末分支回溯、alive/pending 清房、门动画期间阻挡及分阶段 ISM 碰撞。
- [特殊房间制作](../../skills/ue5-pcg-building/references/special-dungeon-interiors.md)：标牌共面闪动、真实机械连接、柜体变体、贴墙与地面标线、材质 Nanite 使用标记。
- [场景开发标准](../../skills/ue5-pcg-building/references/scene-development-standard.md)：统一翻越、控制台预览，以及用户确认并正式接入后的同次样板清理。

- [出征面板真实内容](../../skills/ue5-ui-umg-slate/references/expedition-live-content.md)：奖励候选共享掉落表、行前准备读取实时数据、有界异步缩略图及发布依赖。

本轮新增内容已同步个人技能与工程镜像。其他任务的技能差异保持原样。

## 公开范围和状态

发布清单见 [文件散列清单](Publication20261002/published-files.json)。包含 C++、作者 Python/PowerShell、轻量配置/清单、文档和技能；来源与二进制恢复边界见 [素材说明](../../ThirdPartyNotices/DUNGEON_THEMES_20261002.md)。原始下载、字体、Blend/FBX、贴图、UE 包、缓存、日志、回执和 trash 不随本轮推送。拉取 Git 不能替代完整本机内容恢复。

全房间闸门的历史 Editor 基础 DLL 已构建成功，详见 [封门交付记录](dungeon-all-room-gates-20261002.md)。本次仅进行用户授权的归档散列与仓库发布检查，不重新构建、不打开 UE、不运行游戏、种子回归、渲染或性能验收。最新封门行为仍由用户在游戏内测试。
