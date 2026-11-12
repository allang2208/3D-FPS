# 密林绿色地被与 Quixel 苔藓地表

用户反馈局部密林缺少密集绿色植被、地面仍偏浅色干土。本轮只调整现有温带丘陵中的密林生态覆盖和地表材质，沿用当前世界种子与异步生成。

## 已获取的两套 Quixel 扫描

- Quixel Megascans **Mossy Forest Floor**，扫描编号 `vfylbge`。
- Fab：https://www.fab.com/listings/31b154e8-dea5-49c8-9b29-6362fe1a4a8d
- 本轮获取时 Personal 和 Professional 均显示 USD 0。通过 Fab 官方公开的纹理文件下载接口取得 2K 完整包，无需 computer use。
- 原包 `SourceAssets/HillsRainforestFloor20261111/mossy_forest_floor_vfylbge_2k.zip`，45,485,390 字节，SHA-256：`510641fdf99661680972e233f048a9b446d15d93b4cc88b303e37868aa689acb`。
- 原始元数据的扫描区域为 1 × 1 m，植物细节含苔藓、三叶草、细枝及小型地被；来源为瑞典森林，接入目标是湿润绿色林地的视觉表现，不将其描述成热带物种。
- Quixel **Jungle Ground**（`tjckaf3g`）的 [Fab 页面](https://www.fab.com/listings/900d3556-9897-488a-98dc-4d6c1e9a55d5)。已从 Fab 取得 2K 贴图包，扫描范围为 2 × 2 m。元数据标注热带丛林，内容含泥土、枝条和落叶。下载回执在 `Receipts/jungle-download.json`。
- 两套原始贴图分别保留在批次 `Source/` 和 `JungleSource/`；BaseColor 保留原色，Normal 保留原始方向。AO / Roughness / Height 打包到 RGB，Height 按原图 1–99 百分位归一化用于地表混合与积水低点，不修改原始扫描文件。

## 生成调整

- `RainforestGrassDensityMultiplier`：1.55 → 1.95；密林草地遮阴抑制：0.40 → 0.20。配置和原生默认值同步。
- 低草斑块底覆盖由原先 `0.28 + 0.72 × Clump` 渐变至密林内部 `0.68 + 0.32 × Clump`。
- 密林低草不再被整片蕨类／灌木生境再次大量删去；真实树根、灌木与蕨类核心、石块、水位、道路、坡度及多点贴地筛选仍走现有生成关系。
- 密林低草在树荫中缩小幅度降低，保留原始候选网格、种子、候选 ID 和数量上限；没有增加全地图枚举密度、生成距离或草地生成任务预算。
- 高草和花仍保留林缘／采光空隙分布。密林以外的草地规则未改。

## 材质接入

- 新纹理位置：`/Game/WorldGeneration/TemperateHills/WetForest/Textures/` 下的 `T_RainforestMoss_{BaseColor,Normal,ARH}` 与 `T_JungleGround_{BaseColor,Normal,ARH}`，运行时上限 2048，允许纹理流送。
- 正式地面 `M_PebbleShoreGround` 和基础母材质 `M_TemperateGround` 同步接入。密林内部覆盖浅色干土，林缘按现有生态 mask 渐变，陡坡、河岸和主路径保留原地表。
- 使用同一组随机平移三角网格采样 BaseColor、Normal 和 ARH，减少重复铺砖感；三角网格的每个角选取一套来源，以 1 m 苔藓和 2 m 热带落叶泥土形成自然斑块。混合边界在相邻三角形间连续，各贴图使用同一个选择，法线不做错误的随机旋转。
- 区域外在采样前分支退出；共享 wrap sampler。增加 6 张 2K 图，不新增参数集合或 WPO 风动。
- 湿度控制苔藓暗化和粗糙度；现有浅积水仍在新表层之后混合，新区域的积水低点改读两套扫描混合后的高度。河流水材质和水潭资产不变。
- 低草材质 `M_TemperateMeadow` 的密林配色增强至湿润绿色，同步处理 BaseColor 与 SubsurfaceColor；区域外沿用旱草配色。
- 正式重建入口仍调用 `Tools/WorldGeneration/forest_wet_materials.py`，本次修改已进入该共用模块。不要用旧版全场景重建入口覆盖材质。

## 落盘和交付

增量导入／保存入口：`SourceAssets/HillsRainforestFloor20261111/author_assets.py`；批次互斥包装：`run_background.ps1`。保存六张新增纹理、两份地表母材质和一份草母材质，备份位于本批次 `Backups/`。不保存地图或玩家存档。

`FPSGAMEEditor Win64 Development` 于 2026-11-11 18:48:46、`FPSGAME Win64 Development` 于 18:50:02 后台构建成功，退出码均为 0。回执位于批次 `Receipts/*-build.json`。

资产保存结果以批次 `Receipts/assets-authored.json` 为准。本轮不主动运行游戏、自测、场景截图或性能验收；草地的实际覆盖、视觉效果与开销由用户进场测试。近处草丛仍在入场后分批生成，应待附近植被补齐后观察。
