# 随机地牢与主泵房源码发布

本次整理已认可的房间美术迭代、随机拼接、接口修复、宝箱侧室和主泵房手脑首领接入。源码宿主与 Git 根是 `D:/FPS3D/FPSGAME`，发布目标为 `allang2208/3D-FPS` 的 `main`。本次只做仓库发布所需检查，不启动游戏、截图、渲染或多种子测试。

## 当前实现

固定起点保留标准通道、工作间、仓库柜与神像。普通池为 Distribution、Drainage、ShoredBreach、VentilationLoop、FreightTransfer；每组 3–5 间后接联通通道。宝箱在可放置的普通房旁以 10% 概率尝试，先占位再开侧门。三条支线汇入唯一 Boss 主泵房，入场生成现有手脑，成功生成后封门，击败后开门；失败、死亡与离场有清理及重试路径。

最近一次开发接入已保存 `/Game/GameMaps/L_Dungeon_Randomized`；固定编辑器种子 92247 的制作回执包含 299 个模块、1 间宝箱房、1 间 Boss 房。模块数包含大量通道及转角，不是战斗房数。此次发布不重新生成关卡，不把旧保存记录当成新的游戏验收。

## 可重建源与本机依赖

- 正式原生代码：`Source/FPSGAME/Dungeons`。旧 `Source/FPSGAME/Dungeon` 仍有角色存档兼容引用，未按废案删除；生产地图使用前者。
- 起点与美术母版：既有 DungeonWorkbenchKit、DungeonAtmosphereV2、DungeonRoomInteriors、DungeonRuinEarthwork，以及本次墙面、铁门、水体、粘液与房间扩展作者脚本。
- 房间生成链：`DungeonRoomShells20260922` → `DungeonRoutes20260922`，依次叠加 `DungeonTreasure20260922`、`DungeonVentFreight20260922`，最后应用 `DungeonRouteRepairs20260922`。完整目录由 `DungeonRoutes20260922/Scripts/build_catalog.py` 组合；增量安装保留地图现有目录。
- Boss：先制作并导入 `DungeonBossHall20260922`，再经项目桥执行 `DungeonBossIntegration20260923/Scripts/install.py`。安装之前需完成相应原生 Editor 构建并加载 DLL。已有完整本地素材时不重复全链制作。
- 公开内容包含作者脚本、配置、来源说明和 C++，不包含 `.uasset/.umap`、FBX、Blender、贴图、原始几何提取数据和本机导入回执。重建依赖应从各批次 README 的合法来源与本机资产恢复，不能只凭 Git 克隆声称获得可直接运行的完整工程。
- Fab 神像、工坊工具与土方等仍按各自许可证使用；公开路径和配方不代表原资产允许再分发。被判废的 5080 生成物不重新进入资源池。

地牢目前调用的事件性能采集接口处于并行开发中。本次用 `DungeonPerformanceScope.h` 在编译时适配：有新版接口时沿用现有事件记录，旧版接口只保留 Unreal 原生 trace，不强制引入未发布的性能面板、图标和武器改动。地牢准备阶段仍通过 `TransitLoadingSubsystem` 接入现有加载页。适配文件是本次发布新增源码，未做新的引擎构建或游戏测试。

## 退役归档

本次将 16 个文件移至 `trash/dungeon-random-boss-retired-20260923`，包括被用户退回的 `DungeonGenerationV1` 配方目录，以及已经完成用途的一次性源码补丁、旧 Live Coding 组合入口、安装诊断和 Boss 素材恢复脚本。逐文件原路径、归档路径、大小、SHA-256、原因与替代入口见 [归档清单](../AssetArchives/dungeon-random-boss-retired-20260923.json)。trash 内容不进入 Git。

此前 11 类 5080 废案继续保存在 `trash/dungeon-5080-rejected-20260922`，见 [5080 退役记录](dungeon-5080-retirement-20260922.md)。保留当前作者源及其必要上游，不凭日期删除已被后续制作引用的中间版本。

技能经验同步到工程与个人 `ue5-pcg-building`、`ue5-monster-workflow`：分别维护完整房间语义、接口和占位规则，以及 Boss 入场、封门、奖励和生命周期边界。
