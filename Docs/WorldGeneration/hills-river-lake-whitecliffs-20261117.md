# 丘陵自然河曲、终点湖与白崖采石场

2026-11-17，承接已认可概念 `SourceAssets/HillsRiverLakeConcept20261117/ConceptV1`。用户要求先落地自然河曲与终点大湖，再做白崖石林／废弃采石场；保留现有村庄位置、进村道路与世界种子，后台制作，用户自行测试。缺少美术先从 Quixel 获取。

后续按用户截图反馈，取消进村路线单独抬高的路堤，保留原路线、村庄位置与种子，改为沿丘陵自然衔接；见 [进村路线自然衔接](hills-natural-village-approach-20261117.md)。

## 白崖采石场直达指令

在单人／主机的丘陵场景加载完成后，控制台输入 `fps.Hills.VisitQuarry`。命令定位当前世界种子的采石场下方运输路，面向白崖与采石台地，复用现有目的地分块加载、碰撞就绪和角色胶囊落点检查；不切换地图、不更换种子。当前种子没有生成白崖，或地标资源尚未就绪时，会显示原因并保留当前位置。

指令仅用于 Development／Editor，在进入丘陵时注册。实现位于 `TemperateHillsVisitQuarry.inl`，接入 `TemperateHillsStreaming.cpp` 的既有直达流程。源码前副本、构建回执在 `SourceAssets/HillsQuarryVisit20261117`；本批未自动执行传送或游戏验收。

本指令的 `FPSGAMEEditor` 于 2026-11-17 19:04、`FPSGAME` 于 19:05 后台构建完成，均返回 0；二进制已落盘，传送效果由用户进入游戏后测试。

## 生成接入

- 保留原排水、原林下水域与 V3 村庄选址过程。村庄确定、原黄色生态边界建立后，复制不可变数值计划，再调用 `BuildRiverLake`。村庄选址、朝向、平地、缓坡和连接路不重新计算，种子及 WorldId 不改、不重写正式存档。
- 4 m 保护掩码覆盖村庄整形边缘、原入口到谷地接入点及进村连接道路；保护核心直接读取改造前高度。保护带外才改河道、湖盆与采石台地。
- 河曲以原排水弧长为基础，做宽尺度平滑，再添加种子确定、长度和振幅不同的侧向河曲。振幅受曲率尺度限制，避免逐点随机抖动；保留源头与边界排水身份。每 2 m 重采样，重建原 64 m 空间索引。
- 终点湖目标约 260×180 m，岸线含不等宽湖湾及半岛。下游水面连续降低至同一湖面，湖后保留较窄的泄水段。湖盆中心水深上限约 1.4 m，浅岸渐变；这不新增游泳或船只系统。
- 河湖共同使用裁切水面，避免湖面与河流透明网格叠加。水面接触沿射线穿越的 2 m 格子检查同一组裁切三角形，复用已有水花、火焰遇水及脚步水体接口。
- 地形高度／碰撞、湖岸生态、地图与远景都沿原 `FPlan` 采样入口读取新形状。小水坑继续使用独立有限预算，避开新湖岸及采石区。

## 白崖与采石场

- 湖侧确定性选取约 230×180 m 区域，避让保护区、水岸及地图边界。三级台地累计高差约 18.5 m；中间保留 6 m 核心宽度的连续运输坡道。
- 核心减少树木并转为石质地表；外围保留林地过渡。Quixel 崖壁作外圈石林与后方采石壁，碎石作低矮弃料堆。木吊架和残破工棚按认可设计定尺建模，保留真实门洞和未封闭断口；另接 Quixel 老木绞盘。
- 原始采石崖壁扫描带褐色矿物染色，新增独立材质将基础色调整为浅暖灰石灰岩，同时保留扫描裂隙、法线和遮蔽；绞盘维持旧木与铁件原有 PBR。
- 少量地标网格按资产分组为 ISM，保留跨湖远景，不受 120 m 近处岩石 PCG 生成半径限制。地标占地仍进入植被避让；不作为普通石头采集对象。
- 新网格启用 Nanite 和静态复杂碰撞；扫描岩体降低回退几何预算，带真实门洞的自制工棚与吊架保留完整回退。4K 扫描源保留，运行纹理最高 2K。正式目录 `/Game/WorldGeneration/TemperateHills/WhiteCliffs`，仅新增数组写入原生境 DataAsset。

## 素材与制作入口

Quixel 免费领取及下载记录：`SourceAssets/HillsRiverLake20261117/Receipts/fab-actions.jsonl`。原始下载在 `D:/FPS3D/VaultCache/FabLibrary`。

- [Quarry Cliff A](https://www.fab.com/listings/5c019f10-e69f-4945-8b45-c6e2d8c16f8a)
- [Quarry Cliff B](https://www.fab.com/listings/9caa4be4-3b5b-4d55-a3de-2fdc9e4e5bd6)
- [Small Limestone Rocks Pack](https://www.fab.com/listings/09676e2a-5131-4474-9095-8b31e99192f9)
- [Historic Medieval Castle Winch Wood Old](https://www.fab.com/listings/d6d814b3-b1b0-4e83-9d20-418ac005dd19)

原生主体：`TemperateHillsRiverLake.cpp`、`TemperateHillsWhiteCliffs.cpp`。制作入口：`Tools/WorldGeneration/WhiteCliffs/author_quarry.py`、`import_quarry.py`、`Import-Quarry.ps1`。可编辑 Blender 与 FBX 在 `SourceAssets/HillsRiverLake20261117/Authored`。

构建：`Tools/WorldGeneration/Build-HilltopVillage.ps1 -Batch HillsRiverLake20261117`。后台构建和导入使用原有互斥，不结束其他会话的进程。

## 交付状态

源码、Blender 与 FBX 已制作。`FPSGAMEEditor` 于 2026-11-17 17:04、`FPSGAME` 于 17:14 后台构建成功，均返回 0。

17:17 无界面导入完成并返回 0，6 个网格、配套 PBR 材质／纹理及原生境 DataAsset 的新数组已保存，`Receipts/assets.json` 的 `complete` 为 `true`。首次导入的 Power 表达式 Python 属性写法已改为显式指数节点；失败日志保留在 `Logs/import-attempt1.log`，最终执行记录为 `Logs/import-engine.log`。

构建回执位于 `SourceAssets/HillsRiverLake20261117/FPSGAMEEditor-build.json` 和 `FPSGAME-build.json`；实际保存路径及网格尺寸在 `Receipts/assets.json`，后台进程结果在 `import-process.json`。保存前的原生境 DataAsset 副本位于同批 `Before/DA_TemperateHillsStreaming.uasset`。

没有运行游戏、生成审计、截图或验收测试。编译和资产保存不代表实际种子的画面、碰撞或联机测试通过，交由用户测试。


2026-11-18 整理：本页历史截图、旧宿主和过期备份已移入 trash；当前路径与散列见 [归档发布记录](../Publication/HillsScenery20261118/README.md)。后续状态以 [待办](hills-scenery-todo-20261118.md) 和 [最新完成记录](hills-closure-20261118.md) 为准，不将历史缺口重复记为当前通过。
