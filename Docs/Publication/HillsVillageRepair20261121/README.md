# 丘陵村庄修复、建造与店铺材质

正式村庄子关卡为 `/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage`。修复状态由丘陵世界保存。恢复已有村庄时应沿用对应版本的关卡、修复位和网络宿主。三间店铺的材质记录、两项正式构建结果和六个可重复使用的相机位置在[店铺发布清单](ShopSurfaces/released.json)中。

## 店铺制作与恢复

[两层店铺与建设卡片的恢复说明](shops.md)列出了三间店铺使用的建筑配方、陈列、窗口和破败／修复变体。[村防源码与接入说明](defense.md)记录城墙、高墙、城门、楼梯、建造提示及多人修理的恢复入口。

- **铁匠铺。** 将[实现文件](ShopSurfaces/HillsBlacksmith.cpp)和[头文件](ShopSurfaces/HillsBlacksmith.h)恢复到本机 `Source/FPSGAME/WorldGeneration/`。工作侧火把和炉箅火光随店铺修复状态切换。配套建筑、工匠和居民依赖见[工匠村庄发布包](../ArtisanVillage20261119/README.md)及[后续居民集成](../ConversationDelivery20261120/README.md)。
- **木工坊。** [工作台模型配方](../../../SourceAssets/WoodworkingCrystalBench/author.py)、[导入脚本](../../../SourceAssets/WoodworkingCrystalBench/import_bench.py)和[材质配方](../../../SourceAssets/WoodworkingCrystalBench/Surfaces/author.py)共用 `CrystalCore` 槽。复制恢复时，保留旧台体的相对变换及 `DriveStrength` 参数。正式模型引用的槽位、LOD 与碰撞见[工作台安装记录](../../../SourceAssets/WoodworkingCrystalBench/installed.json)。Blender 原场景、FBX 和原工程纹理在本机制作目录。
- **草药铺。** [药瓶制作配方](../../../Tools/WorldGeneration/VillageHerbalist/vessel_finishes.py)生成 2 个父材质和 6 个材质实例。[工作台补丁](ShopSurfaces/herbalist-workbench.patch)基于 `e8b7284d` 的 `Source/FPSGAME/Building/PotionWorkbenchVisualComponent.cpp`。在具备 `AHillsHerbalistWorkshop` 的完整工程中，从仓库根用 `git apply --unidiff-zero` 应用。原始台体和交互台体都按槽名绑定。资产目录为 `/Game/Building/PotionWorkbench20261015/V1/HerbalistVessels/`。

灯光与材质的制作方法已归入[场景灯光](../../../skills/ue5-pcg-building/references/fixture-lighting-standard.md#铁匠铺的铁砧与炉膛)和[店铺工作台近景](../../../skills/ue5-pcg-building/references/reusable-interior-assemblies.md#村庄店铺的工作台近景)。用户要求再次同机位拍摄时，清单中的位置和目标点以铁匠铺房屋局部坐标厘米为单位。各自按记录的时间和水平视场角复拍。

## 本机资产与交付范围

正式 UE 包位于工程 `Content` 对应的 `F:/FPSGAMEData/Content/`。水晶旧包和发布回执保存在 `F:/FPSGAMEData/ArtProduction/WoodworkingCrystalBench/20261121-Facets/`，药瓶清单在 `F:/FPSGAMEData/ArtProduction/VillageHerbalist/VesselFinish20261121/published.json`。误删后使用的城防、图标和关卡导航恢复清单保存在 `Saved/Recovery/HillsVillage20261121/`，应按清单比对实际包散列。关卡导航按原配方重建。

本轮三店铺的 `FPSGAMEEditor` 和 `FPSGAME` 均已编译，三家修复后的店铺已在单机离屏拍摄。已有弱网建造、并发修理和重置工作台等用例有独立回执；本轮材质调整后没有重新执行工作台交互、联机画面对照或公网测试。

F6 重置会使营业中的店面回到破败形态。恢复这一交互时，场景工作台需要向所属建造世界注销，玩家会话也要确认注册在该锚点的仍是原来的工作台。相同坐标随后可以出现另一张工作台。[工作台会话源码片段](WorkshopSessions/station-reset.cpp.inc)和[目标文件及适用范围](WorkshopSessions/methods.json)给出生产宿主的接入位置。标为 `method prefix` 的记录仅覆盖指定的函数前段。木工锯在驱动切换时设置水晶亮度的改动在[常规组件](../../../Source/FPSGAME/Building/WoodworkingSawVisualComponent.cpp)中。

完整检测图片、GIF（如有）、运行宿主和构建中间件移入各自磁盘的本地 `trash`。[归档清单索引](retirement.json)记录各批数量和可恢复的位置。

已有[多人建造与重置结果](WorkshopSessions/network-receipts.json)保留了三客机争修、弱网、两类城门快速重建和 F6 重置时已投料工件的回执。需按原机位再拍时，完整工程的 [HillsBlacksmithReview.cpp](WorkshopSessions/HillsBlacksmithReview.cpp) 提供开发版取景入口，目标路径为 `Source/FPSGAME/WorldGeneration/`。
