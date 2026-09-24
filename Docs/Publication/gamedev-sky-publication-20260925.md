# 方形祭坛、出征面板、传送门、宝箱与天空资源发布

2026-09-25 按用户要求整理本次对话成果。只发布作者脚本、C++ 面板接入、恢复说明与可复用技能；保留共享工作区中其他任务的修改。没有启动或重启 UE、运行游戏、截图或做性能／视觉验收。

## 发布与本机恢复

| 内容 | 源码入口与恢复顺序 | 本机依赖／状态边界 |
| --- | --- | --- |
| 中央方形祭坛 | [制作说明](../../SourceAssets/SquareAltar20260922/README.md)；author_square_altar → import_materials → import_mesh → register_prefab | 原项目 defense_base 参考与白石纹理；恢复 `/Game/Props/SquareAltar20260922` 和建造调色板。不是大型主神空间迁移 |
| 出征面板与祭坛入口 | [面板规划](../UI/expedition-panel-plan-20260922.md)、`Source/FPSGAME/UI/ColdSteelExpedition*`、PlayerController 及相关面板互斥；place_hub_altar | 只开发面板，不迁移解锁、钥匙、奖励、队伍或存档；按 E 交互。历史祭坛摆放最后记录为地图保存受阻，保留 pending 记录，不声称本轮已保存或实机通过 |
| 传送门 | [制作与接入说明](../../SourceAssets/GamedevPortal20260922/README.md)；原源 → export_portal → import_portal_materials → import_portal_meshes | 恢复 `/Game/Props/GamedevPortal20260922` 及祭坛白石纹理依赖；既有目的地、E 交互和加载逻辑保留，模型接入代码已在先前地牢发布中进入主线 |
| 探险宝箱与连续开盖 | [首次迁移／动作上游](../../SourceAssets/GamedevTreasureChest20260922/README.md) → [空心结构及材质修订](../../SourceAssets/GamedevTreasureChest20260923/README.md) | 恢复 `Props/GamedevTreasureChest20260922`、原骨架与 Opening 动作；保留 `treasure_chest_assets.json`、地牢配置和关卡引用。独立于仓库箱，不增加奖励或持久化开箱状态 |
| HDR 压缩 | [BC6H 制作记录](../Performance/sky-hdr-bc6h-20260924.md)、`Tools/Weather/compress_sky_hdr_bc6h.py` | 恢复本机 PWL 七张 HDR 和相关 NaturalV2 材质。已保存原分辨率 BC6H；4.69 GiB → 0.586 GiB 为理论纹理数据估算，不是本轮显存或 FPS 实测 |

宝箱修订重制顺序为 `make_surface_maps.py`、`rebuild_chest.py`、`install_finished_chest.py`，静态构建补完入口为 `finish_static_build.py`。保留 20260922 的 `Authored/GamedevTreasureChest_UE.blend`，新网格脚本还依赖其骨架与材质。首次迁移的旧几何不能在修订后再次覆盖运行资产。

关卡、模型、贴图、音频、完整材质／蓝图 `.copy` 导出、网格／姿态数据、成功制作回执与备份留在本机，未据用户持有素材推定公开再分发许可。`Content/`、`Saved/`、`trash/` 沿用现有发布边界；本次新增 SourceAssets 精确忽略规则，只放行四个有效道具制作目录的 Python 和 Markdown。源码仓库无法单独恢复完整可玩画面。

## 归档与保留

54 个文件共 1,554,921 字节移至 `trash/gamedev-sky-retired-20260925/`，逐文件检查移动前后 SHA-256。包括已取消的大型主神空间制作源、被最终厘米／轴向版本替代的传送门导入尝试、失败或空的宝箱／祭坛调用记录、HDR 失败属性读取与失败诊断输出。完整原路径、目标、大小、散列、退役原因和保留替代物见 [归档清单](gamedev-sky-archive-20260925.json)。trash 内容不公开提交。

保留方形祭坛正式作者源、最新保存阻塞证据、传送门最终导入记录、宝箱骨架与动作上游、修订前目标包备份、七张 HDR 压缩前备份和成功回执，以及尚未确认原因的 M4／天空排查现场。没有按文件日期或候选名称批量淘汰内容。

## 沉淀与尚未解决的问题

个人 SKILL 与工程镜像同步了三份专题：旧项目道具与材质数组写回、HDR 常驻预算和诊断动作对流送的影响、运行天空／相机覆盖与太阳反射方向归因。它们记录可复用步骤和证据边界，不把保存成功写成视觉认可。

- [M4 低清排查](../Performance/m4-texture-residency-diagnosis-20260924.md)：故障未稳定复现，恢复后的 4K 驻留快照不证明已修复。
- [主场景反向亮斑](../Weather/main-hub-highlight-diagnosis-20260924.md)：相机 LensFlare 已为 0；HDR 高亮与天空／反射方向可能脱节，根因未经比较确认，未提交所谓双太阳修复。
- 祭坛旧回合的主场景保存失败保留为历史阻塞证据；本轮不重开编辑器补做场景操作。

本轮检查范围是 Git 发布：精确内容、差异、大小、敏感信息、许可边界与未发布历史。既有构建／保存结果引用各制作记录；不重新运行游戏测试、Cook 或性能采样，由用户测试实际效果。

发布共享源码时同时带入工作区已有的必要闭合修正：PlayerController 弹药输入分支缺少的右括号与重复条件，以及 `SceneTestPortal.h` 中主线实现已使用的 `OpenDestination`／`DungeonTravelTimer` 声明。未带入弹药滚轮取消选择等并行行为变更；这两处修正与本次出征／传送门代码一同记录，未重新编译。
