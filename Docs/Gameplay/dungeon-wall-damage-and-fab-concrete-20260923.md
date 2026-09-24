# 地牢剥落随机化与指定 Fab 混凝土

> 2026-09-24 后续修复：本页记录的砂浆基层/粘结层“不启用视差”方案已由 [墙面凹凸后续修复](dungeon-wall-relief-followup-20260924.md) 替代。当前两个砂浆实例恢复 9 月 22 日的完整配套表面并采用实例空间投射；破墙混凝土截面仍沿用本页的 Fab 扫描材质。

用户指定 `Angled Concrete Wall Section with Heavy Damage`，仅复用其表面材质，保留现有地牢建筑轮廓、瓷砖风格、门洞、地板与玩法。

## 实际来源

- Fab 商品：<https://www.fab.com/listings/0b06ec58-10ec-4c1c-8755-310e08fdbc33>，MICROBACKLOT。
- 已下载缓存：`D:/FPS3D/VaultCache/FabLibrary/Angled_Concrete_Wall_Section_with_Heavy_Damage-0b06ec58/fbx`；实际缓存位置来自 Launcher 的 `VaultCacheDirectories` 配置。
- 使用 8K UDIM 1003、1001 中的裸露骨料区域，排除墙漆、图集外延和空白。三个通道同时采用相同的最小误差拼接边界，生成一套 1024² 的底色、法线、ORM；没有把颜色亮暗假充成高度图。
- 原素材与 UV 图集不覆盖、不公开提交。来源坐标、原文件散列、处理方式及输出记录在 `SourceAssets/DungeonWallDamage20260923/Sources/provenance.json`。

## 剥落机制

旧 `corridor_surfaces.py` 在三段固定样板中选起点，再顺序重复铺设，导致破损位置和轮廓容易被识别。

新作者算法 `natural_wall_damage.py` 用有疏有密的簇群构成破损区，混合局部撞击、沿墙脚扩散的损坏和小缺口，允许完整墙段。各簇由多个大小、方向不同的区域组合，再以连续扰动改变边缘；不按固定间距盖同一个图案。

逐块瓷砖按区域覆盖决定完整、脱落或边缘残留。残留仅接在完整邻砖附近，并保留已认可的陶瓷厚度、釉面图集 UV、微小断口和连接至基层的粘结层。基层是连续网格，门洞和破墙缺口仍经过裁切，宝箱连接段的 15 cm 收口与 4 cm 退让继续保留。

普通房、带侧门版本、连接段和宝箱房按表面族制作三份网格，进入地牢时独立抽取，并避免同一种表面连续抽到同一版。随机流独立于路线和杂物生成，不改变房间选择或 Boss 路线。固定起始区另外制作八面墙皮；固定区当前不随每次进入重新抽取。Boss 大厅特殊切口和地下楼梯保留原有几何。

运行时复用既有资产预载、分阶段装配与 ISM 路径，只选择现成网格，不运行布尔切割、采样场或逐帧随机。

## 材质及性能范围

- 新主材质：`/Game/Dungeons/WallDamage20260923/Materials/M_FabExposedConcrete`。
- 三个实例分别用于破墙混凝土截面、脱落后露出的基层和粘结砂浆；陶瓷本身的釉面与断面不替换为混凝土。
- 使用局部实例空间三向投射，按厘米控制尺度，降低不同模型 UV 拉伸；非金属反射、扫描粗糙度和法线分别输入，附带轻微大尺度色差。
- 仅三张共用 1K 贴图，保留纹理流送；不把四套 8K UDIM 常驻进地牢，不启用逐像素多步视差。
- 新墙皮使用 Nanite、显式切线和完整回退几何，保留碰撞策略；未改地面承重、导航或光照基线。
- 目录及源导入器接入持久映射，后续重建继续使用新配置。保存前保留旧目录、地图以及逐材质槽 before/after 记录。

## 制作、构建与接入

制作入口位于 `SourceAssets/DungeonWallDamage20260923/Scripts`：`author_variants.py`、`author_fixed_and_reward.py`、`prepare_scan_textures.py`、`create_materials.py`、`import_meshes.py`、`install.py`。

`Receipts/materials.json`、`meshes.json`、`install.json` 分别记录实际保存状态；只有 `install.json` 的 `stage=map_saved` 才代表地图完成接入。

本次原生修改只在 `AuthoredDungeonGenerator.cpp` 增加表面变体选择，不新增反射类型。必要 Editor 构建发现已有 `CombatStatusFormula.h` 缺少被现有函数使用的 `InspireAtk` 成员，补回默认值 1 后 Editor 构建成功（`build-editor-02.log`）。Game 构建期间独立的战斗/UI 源文件仍在变更，出现集合类型与实现不同步的错误，相关输出保留在 `build-game*.log`；不改动这些并行功能。

前次 Game 构建（`build-game-03.log`）因 `ColdSteelFormulaBonuses.cpp` 与头文件集合类型不同步而失败。并行修改完成后，本次必要构建 `build-game-04.log` 返回 `Target is up to date`、`Result: Succeeded`；`Binaries/Win64/FPSGAME.exe` 已是当前源码对应的构建产物。

当前已实际保存三张纹理、一个主材质、三个材质实例和 77 份墙面网格（23 类随机表面各三份，加八面固定起始墙皮）。不是仅生成导入脚本。

用户允许结束当前游戏后，原编辑器与游戏已退出；接入改由后台 commandlet 完成，没有重新打开编辑器或游戏。`install-commandlet-02.log` 记录 23:06:46 地图文件落盘、23:06:49 外部 Actor 包保存结束、23:06:50 安装脚本成功返回。`Receipts/install.json` 已为 `map_saved`：83 个模型的矿物材质槽已更新，77 份墙面网格引用已接入，包含 23 类随机表面与八面固定起始墙皮。运行目录 JSON 同步保存。

该 commandlet 的退出阶段仍有异步距离场任务运行，23:06:57 报告内存不足，最终进程退出码为 3；这发生在地图、外部 Actor 包、配置及保存回执落盘之后。不能将其表述为一次干净退出。安装脚本随后改为分批绑定并释放旧网格，延迟加载新变体，减少再次接入的资源峰值；此脚本改进未追加重跑或测试。本次保存结果以已完成的包保存记录和 `map_saved` 回执为准。

未启动 PIE、游戏、截图、场景渲染或验收测试。制作与编译记录不代表画面已获用户验收。
