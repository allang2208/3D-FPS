# 随机地牢升级：归档与源码发布

发布宿主 `D:/FPS3D/FPSGAME`；目标 `https://github.com/allang2208/3D-FPS.git` 的 `main`。遵守 WORKFLOW 第 8 节，保留共享工作区与其他任务的修改，不切换或重置当前分支。

## 本机成果与制作入口

- 任务图、多门共享房壳、地下终点和短连接修正：[V4/V5 接入](dungeon-v4-complete-20260926.md)、[失败种子修复](dungeon-layout-failure-20260927.md)、[算法排查](dungeon-algorithm-audit-20260927.md)。历史 41 次纯规划检查不能替代游戏测试，本轮未重跑。
- 所有连通门口的精英铁闸：[门洞与铁闸](dungeon-elite-grille-20260926.md)。作者源 `DungeonEliteGate20260926`，读取实际端口宽高，沿用通道闸门造型。
- 传送门移除、神像赐福与朝向、重新布置的厚墙破洞：[神像逻辑](dungeon-shrine-blessings-20260927.md)、[房间 V2](dungeon-shrine-room-v2-20260927.md)。`DungeonShrine20260927` 保留赐福目录和材质/安装恢复入口；V2 承担当前房间外观，不能把整个旧目录当废案删除。
- 宝箱落地、楼梯灯位置与密度：[宝箱制作](../../SourceAssets/DungeonTreasure20260922/README.md)、[楼梯灯](dungeon-stair-lighting-20260927.md)。`Tools/Dungeon/remove_treasure_floor_plate.py` 是现有资产的定向接入入口，宝箱作者配置已同步去除铁板。
- 墙、柱和大型障碍避让：[碰撞记录](../Monsters/monster-wall-obstacle-collision-20260927.md)。小装饰仍允许无碰撞。
- 排水、通风、货运设备组合及状态：[设施房间](dungeon-facility-scenes-20260927.md)。九款共享组合件，配方在 `DungeonFacilityScenes20260927`。
- 女僵尸退出，感染犬、大/小手加入：[刷新池](dungeon-spawn-pool-20260927.md)。自然刷新小手与召唤小手的寿命和奖励分别处理。
- 走动卡顿：[现有证据](../Performance/dungeon-walking-stutter-20260927.md)。没有有效的对应帧 CPU/GPU trace，不宣称已归因或修复。

## 归档

96 份文件，共 4,661,949,336 字节（约 4.34 GiB），已移动至本机 `trash/dungeon-upgrades-20260927/`。逐文件原路径、目标、大小、SHA-256、原因及保留替代物见 [归档清单](dungeon-retired-20260927.json)。先核对所有源/目标路径，再移动并逐文件回读散列；96 份均一致。

归档内容包括有对应当前 `.blend` 的自动 `.blend1`、主泵房细化前快照、神像/楼梯/目录修改前备份，以及已完成的一次性编辑器状态、兼容性探查和会话操作脚本。当前模型、FBX、材质源、制作与安装脚本、许可、保存回执和必要旧输入保留。没有归档正在使用的 UE 包，trash 不公开提交；将来的制作仍可生成新的回退快照。

## Git 发布范围与依赖边界

公开目录/配方、作者与导入脚本、算法检查工具、文字记录、署名和 SKILL；同时公开可独立编译的 `AuthoredDungeonCatalog`、`AuthoredDungeonRoomScenes`、`MonsterObstacleCollision` 三组辅助源码。

**这次 Git 提交不能单独重建本机完整运行行为。** 生成器、遭遇、神像、奖励和障碍接入依赖工作区尚未发布的手怪、存档、状态显示及移动接口。共享文件还包含其他任务的改动，不能将整份共享文件夹带发布。

相关 21 份运行文件的修改另存为 [地牢运行交接补丁](Publication20260927/dungeon-runtime-handoff.patch)，基础提交、文件散列和缺失接口列在 [交接清单](Publication20260927/runtime-handoff.json)。小手本轮改动为 [地牢小手增量](Publication20260927/flesh-hand-dungeon-member.patch)，其基线是已经公开的 [怪物源码交接](../Monsters/Publication20260927/new-runtime-sources.patch)。补丁位于 Docs，不参与公开树编译；需与依赖接口共同接入，不要在当前完整宿主重复应用。

补丁与配置保留实际实现，不能把文件存在或 Git 推送成功等同于公共 main 已完成游戏接入。源文件未移动、未回滚，本机已保存资产及 DLL 不受本轮发布整理影响。

## 本机资源恢复

恢复地图 `GameMaps/L_Dungeon_Randomized` 及生成器 ExternalActor、当前 `Content/Dungeons` 房壳/铁闸/神像/楼梯/组合件、`Content/Monsters` 怪物与共享材质、动画、导航依赖；同时恢复所需 SourceAssets 的 Authored、原始输入、manifest 和 Receipts。

完整宿主应先具备相应运行接口和基础 DLL，再按作者批次执行必要导入与目录保存。目录重建顺序为 RouteRepairs → Spawn → Composition → FacilityScenes，神像目录由自己的扩展层维护。回执门控是本机已安装状态，Git 不包含回执与 UE 资产，不能把源码克隆当作已安装工程。

二进制、Blender/FBX、模型/PBR、贴图、密集几何数据、导入回执和原始日志保留本机。已有素材许可继续适用；模型可商用不自动授权原件再分发。公开神像署名见 [Diana](../../ThirdPartyNotices/GODDESS_STATUE.md) 与 [雕像套件](../../ThirdPartyNotices/STATUE_SET.md)，并保留它们的历史制作状态日期。

## SKILL 与检查范围

经验分别沉淀到 PCG 的共享房壳/占位/连接预算、怪物的刷新池继承/小手生命周期/精英铁闸，以及性能的进入加载与走动卡顿分段归因。相关个人技能与工程镜像同步，不把特定房间数值写成通用要求。

本轮执行用户授权的发布检查：归档散列、精确暂存差异、文本/脚本语法、文件大小、敏感信息、源码依赖与远端 SHA 回读。未重新构建、导入、启动 UE 或做运行/视觉/性能测试。此前正式构建和资产保存证据保留在各制作文档中。
