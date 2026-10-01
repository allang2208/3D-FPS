# 废弃解剖教学剧场：正式入池与样板退役

用户认可剧场主体、木座席及照明后，要求复用此前血迹到解剖台，并接入随机生成。正式模块为 `AbandonedAnatomyTheatre`，生成地图为 `/Game/GameMaps/L_Dungeon_Randomized`；当前房型池为原五间加五间独立废弃设施，共十种。

## 解剖台血迹

直接引用医院／停尸房已有的 `/Game/Dungeons/IsolationWard20260929/BloodScan/M_WardBlood_Quixel`，共享扫描贴图，没有新增材质或下载素材。台面三块血迹的完整扫描边长为 58、50、38 cm，分别旋转 12、-27、68 度，保留扫描比例。投射中心距地 105.2 cm、投射半深 2.5 cm，覆盖台面且不会延伸至地面。

血迹使用现有 `runtime_actors.type=decal` 装配，在房间变换下随解剖台一同旋转／平移；没有增加随机重试、每帧更新或环境伤害。位置属于作者固定布景。

## 随机房间合同

- 保留约 28 × 24 m D 形厅、四排座席、四路楼梯、2.16 m 观察廊、中央 8 × 8 m 净空及辅助设备。最新圆角木座席资产和中央 2400 流明／14 m 半径灯光来自用户认可的已保存地图。
- 正式配置含 36 个静态部件实例、9 盏局部灯、3 块台面血迹和 10 个有界曝光体积。保留两盏投影灯、原始作用半径、距离／渐隐和角色字段，沿用现有生成器灯光调度；原样板无界曝光按房间占地裁为有界体积。
- 两个外接口位于作者坐标 X=±16 m、Y=-10 m，宽 3 m、高 2.8 m、地面标高不变。占位使用前厅矩形、七条保守圆弧条带及两个门斗，计入顶棚、墙厚和真实高度，不整体缩放房间。
- 9 个出生锚点位于中央净空区，避开座椅、台面、梯面及栏杆；沿用档案中心的敌人混合配方，数量 4～6，接既有封门遭遇。
- 按 run seed + 模块 ID 一次性抽取 30% 候选资格，最多一间，路线 `Approach`。仍受实际几何与路线限制，30% 不表示最终出现率。

## 已保存资产与退役

增量合并当前生成器目录，保留其余九种房间，保存实际外部 Actor 包 `/Game/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH`，并同步 `SourceAssets/DungeonRoutes20260922/Config/catalog.json`。依赖网格、木材和血迹材质均写入生成器硬引用。

生产模块及可重用扩展器位于 `SourceAssets/DungeonAnatomyTheatre20261001/Pool20261001/Config/module.json` 和 `Scripts/extend_catalog.py`；重建链 `DungeonRouteRepairs20260922/Scripts/extend_catalog.py` 在已有档案中心之后叠加该模块。后续重新安装使用 `Pool20261001/Scripts/install_pool.py`，不依赖样板。

样板地图、临时封口网格／FBX、两份旧地图备份、专用安装与捕获脚本共 12 项已移到 `trash/anatomy-theatre-subject-retired-20261001/`，逐文件源路径、目标路径及 SHA-256 见其 `manifest.json`。移除出征菜单项、MapsToCook 和样板专用返回分支；God Space／丘陵的共享返回逻辑保留。作者配置改为生产阶段，主几何作者不再生成临时封口。

实际资产保存记录在 `Pool20261001/Receipts/install.json`，归档状态在 `Receipts/completion.json`，必要原生构建结果在 `Receipts/native-build.json` 和 `Receipts/native-build.log`。本次不进行随机种子回归、PIE、视觉渲染或运行验收，由用户测试。
