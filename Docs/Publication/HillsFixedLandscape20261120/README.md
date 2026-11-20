# 固定丘陵地形、采石场与植被恢复说明

这张 1,024 × 1,024 米的丘陵使用固定种子 `1518277816` 和生成版本 `3`。地形按 256 个地块保存。游戏档案各自保存采伐、修复等进度。接续此前的河湖与采石场版本时，可先查阅工程依赖与旧版接入记录。[工程资产恢复](../../AssetSetup.md) · [丘陵河湖与树簇前置](../HillsScenery20261118/README.md)

## 恢复已制作的版本

从完整本机工程或备份恢复表中各项。UE 的 `/Game` 对应工程 `Content`；本机目录联接指向 `F:/FPSGAMEData/Content`。清单给出三份地图数据、正式植被配置、本轮衍生材质与网格、石灰岩制作源及 11 个直接供体的相对路径、大小和 SHA-256。安装第三方包时一并恢复其材质父级、图集、材质函数及启用的插件。按原路径恢复已有 UE 包可保留构建所用内容签名。[本机资产指纹](asset-recovery.json)

| 要恢复的内容 | 位置和来源 |
| --- | --- |
| 地形、水位和采石场摆放 | `Content/WorldGeneration/TemperateHills/FixedLayout/{Hills.layout,Quarry.dressing}` 和 `FixedTerrain/Hills.terrain`。三份文件取自同一次烘焙，后两项关联布局校验值。 |
| 植被与装饰配置 | 同目录 `DA_TemperateHillsStreaming.uasset`，以及 `WetBank/`、`Canopy/`、`GroundPalette/` 下的专用包。保留地图 `/Game/GameMaps/L_TemperateHills_Initial` 与其引用的原有草、树、石、材质及 PCG 图。 |
| 欧洲黑桤木 | 两株湿岸幼树取自 Quixel European Black Alder 的 `/Game/BlackAlder/Geometry/SimpleWind`。两种远冠取自工程已挂载的 `/CitySamplePCG/BlackAlder` 下 Field 01、04 的第 6 级 LOD。幼树材质复用 City Sample 的夏、冬叶片图集。[Quixel 官方资源包](https://www.fab.com/listings/9de7ce19-5813-42d2-a5f0-5e6447006f72) |
| 石灰岩、河砾与枯枝 | 扁、长石灰岩取自 Quixel `udqhfcyva` 扫描的两个独立掉块。保存 `SourceAssets/HillsQuarryRockLayout20261119` 的原 FBX 与 `SourceAssets/HillsGroundPalette` 的两份低模。材质使用丘陵 `WhiteCliffs/Materials/M_LimestoneSpoil`。另外三种河砾与枯枝从工程现有 `/Game/NiagaraExamples/StaticMesh` 读取。 |
| 林下与岸上地被 | Project Nature `/Game/PN_FoliageCollection/Meshes/groundPlantMesh` 的 05、10、13 号供体用于湿林，09 号用于岸上。恢复原图集和材质实例，保持绿色林下与旱地黄草的分区。 |

公开恢复材料提供源码、制作配方和指纹。完整 UE 工程所需的原始扫描、商业素材、FBX、贴图和衍生 UE 包从有相应权限的本机备份或原供应商取得。

## 从制作输入重建

公开仓库的丘陵宿主早于本机版本。先恢复上一阶段的丘陵、植被和村庄宿主，再将本目录 `Implementation/Source/` 内的专属实现合入同名源文件。`Integration/` 保存共享加载与存档代码的局部补丁。`ArtIntegration/` 的三个补丁分别接入村外坡地、路缘种植和生物群落过渡；`TreeCandidate.cpp.inc` 是需要替换的成树选址函数，目标为 `Source/FPSGAME/WorldGeneration/TemperateHillsVegetation.cpp`。应用范围是完整 UE 宿主，仓库单独检出的构建状态未验证。

1. 在 UE 5.8.2 完整宿主中恢复前置场景与授权资产，接入本次源码，然后后台构建 Win64 Development 的 `FPSGAMEEditor`。这一版模块提供固定地图烘焙入口、采石场碎片与湿岸幼树的独立资产字段。
2. 需要重做石灰岩低模时，使用 Blender 后台执行 `Tools/WorldGeneration/prepare_hills_ground_palette.py`。恢复了两份正式低模 FBX 的工程可以直接导入。
3. 用 UE 后台 Python commandlet 执行 `Tools/WorldGeneration/install_hills_scenery_palette.py`。该入口调用同目录的 `hills_ground_palette.py`、`build_hills_alder_canopy.py`、`build_hills_wet_saplings.py`，制作模型后统一保存 `DA_TemperateHillsStreaming`。既有资产数组保持原槽顺序，以便沿用水线石和可采收资源的标识。
4. 地形、选址或采石场摆放发生变化时，运行 `UnrealEditor-Cmd.exe FPSGAME.uproject -run=BakeTemperateHillsLayout -unattended -NullRHI -nosound -nop4`，使地图、碰撞和水面读到同一版数据。最后在已落盘的资产与地图数据上构建 `FPSGAME` 和 `FPSGAMEEditor`，两端使用相同的丘陵内容签名。

## 交付状态

本轮正式 Game、Editor 开发构建均成功。湿岸幼树的四级三角数分别为 3,692 / 1,476 / 628 / 240 和 2,878 / 1,152 / 490 / 188。两种远树代理各 8 个三角面。新增或追加的 13 个变体均已写入正式植被配置。本轮没有最终版本晴雨路线的 P95、超过 50 ms 的帧数或同机位实机截图。

逐项制作结果见[烘焙与构建记录](Evidence/BuildAndBake.json)和[植被配置记录](Evidence/SceneryPalette.json)。工程及临时目录的 2,171 个文件移入项目 trash，E 盘制作缓存的 6,643 个文件移入同盘 trash。项目内的逐文件清单记录原路径、恢复位置和 SHA-256。[归档摘要](Evidence/ArchiveSummary.json)
