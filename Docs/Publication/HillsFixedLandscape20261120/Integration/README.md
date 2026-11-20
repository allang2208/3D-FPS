# 固定丘陵地图的共享宿主接入

适用基线为 2026 年 11 月 19 日湖岸阶段保存的完整工程源码快照。该基线已有河湖生成、分段载入、村庄选址、采石场传送和内容签名。公开仓库按阶段归档，单独检出公开主分支时可能缺少这些宿主版本。每个文件的 `index` 行给出按 UTF-8、LF 计算的修改前后 Git blob ID，便于与完整工程或备份核对。[前一轮丘陵地编接入](../../HillsScenery20261118/README.md)

| 补丁 | 接入位置与用途 |
| --- | --- |
| [01 地图身份、存档和内容签名](01-map-identity-and-save.patch) | `TemperateHillsWorld.h/.cpp` 与 `TemperateHillsTerrain.cpp` 接入固定地形种子、独立档案种子、测绘锚点、采石场道路和带种子的村外坡脚整形。湿岸幼树、坡岸碎石、烘焙入口与分段载入方法在世界宿主声明。`HillsNightPersistence.cpp`、`HillsNightRaidSubsystem.cpp` 沿用旧档天气及袭击序列；新档使用各自的 `PlaythroughSeed`。`FPSGAME.Build.cs` 把 `Hills.layout`、`Quarry.dressing`、`Hills.terrain` 加入构建依赖和内容签名。 |
| [02 地块载入与采石场准备](02-terrain-and-quarry-streaming.patch) | `TemperateHillsStreaming.cpp`、`TemperateHillsStreamingPrivate.h` 接入固定的河湖选址、地块读取和采石场阶段状态。`TemperateHillsQuarryTravel.cpp` 与 `TemperateHillsStreamingVisit.cpp` 在传送前准备资源，到达后对准入口机位。`UI/ColdSteelHillsMap.cpp` 将岸坡排水信息写入地图预览的对应 UV 层。 |
| [03 植被预加载和岩石占位](03-vegetation-and-preload.patch) | `TemperateHillsStreamingPreparation.cpp` 把湿岸幼树加入预加载，记录编辑器编译轮询进度，采石场专用模型由采石场按需载入。`TemperateHillsPlacement.cpp` 把固定掉块纳入植被遮罩，`TemperateHillsProduction.cpp` 通过采石场组件标签识别景观物件。 |

从完整工程根目录执行以下命令。补丁基线采用 UTF-8 与 LF。遇到宿主上下文差异时，根据每段函数和 `index` 前像定位对应改动，保留该宿主已集成的其它功能。已合入的版本可用 `git apply --reverse --check <补丁>` 核对。

```powershell
$patches = (Get-ChildItem 'Docs/Publication/HillsFixedLandscape20261120/Integration/*.patch' | Sort-Object Name).FullName
git apply --check $patches
if ($LASTEXITCODE -eq 0) { git apply $patches }
```

PCG 跨帧生成及垃圾回收引用、地块几何构建、植被贴地和分行处理的完整实现，分别恢复到源码树相同位置。采石场状态机使用同目录归档的 `TemperateHillsWhiteCliffs.cpp`、`TemperateQuarryFixedDressing.*`；地块流送使用 `TemperateHillsFixedLayout.*` 和 `HillsFixedTerrainCells.*`。制作资产、UFS 配置与同批三份烘焙数据的恢复步骤见本轮总说明。[PCG 实现](../Implementation/Source/FPSGAME/WorldGeneration/TemperateHillsPCG.cpp) · [地块几何](../Implementation/Source/FPSGAME/WorldGeneration/TemperateHillsStreamingMesh.cpp) · [植被贴地](../Implementation/Source/FPSGAME/WorldGeneration/TemperateVegetationPlacement.cpp) · [本轮总说明](../README.md)

归档时在隔离目录将三份补丁应用到湖岸阶段快照，核对了 14 个宿主的结果字节。该项检查覆盖补丁还原；实机性能记录见本轮总说明。
