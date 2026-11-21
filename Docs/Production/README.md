# FPSGAME 制作目录与功能索引

## 已登记的功能

| 功能 | 编辑与接入入口 | 正式路径与恢复线索 |
|---|---|---|
| 丘陵村庄 · 城墙、城门与石阶 `HillsVillageDefenses` | [村防专属源码与制作目录](../Publication/HillsVillageRepair20261121/Defense/source-index.json)、[多人修复和建造接入](../Publication/HillsVillageRepair20261121/defense.md)。 | 正式 UE 资产盘为 `F:/FPSGAMEData/Content/`。墙身、门楼、铁闸、石阶、图标和入口地图的原包及恢复路径见[本机资产回执](../Publication/HillsVillageRepair20261121/Defense/local-recovery.json)。 |
| 丘陵村庄 · 铁匠铺、木工坊与草药铺 `HillsVillageShops` | [炉火与铁砧照明](../Publication/HillsVillageRepair20261121/ShopSurfaces/HillsBlacksmith.cpp)、[驱动水晶材质](../../SourceAssets/WoodworkingCrystalBench/Surfaces/author.py)、[药瓶材质](../../Tools/WorldGeneration/VillageHerbalist/vessel_finishes.py)、[炼药台材质槽绑定](../Publication/HillsVillageRepair20261121/ShopSurfaces/herbalist-workbench.patch) | 丘陵村庄修复后的店铺使用 `/Game/Building/WoodworkingCrystalBench/Surfaces/M_WorkshopDriveCrystal` 和 `/Game/Building/PotionWorkbench20261015/V1/HerbalistVessels/`。[水晶制作批次与原包](F:/FPSGAMEData/ArtProduction/WoodworkingCrystalBench/20261121-Facets)、[药瓶发布回执](F:/FPSGAMEData/ArtProduction/VillageHerbalist/VesselFinish20261121/published.json)、[同机位对比与原图归档](F:/FPSGAMEData/trash/HillsVillageShops-20261121/ArtReviews/HillsVillageShops/20261121-Materials)、[村庄修复系统与制作源恢复说明](../Publication/HillsVillageRepair20261121/README.md)。本轮版本待 NAS 备份。 |
| 丘陵村庄 · 草药铺药瓶 `VillageHerbalist` | [瓶身与药液材质配方](../../Tools/WorldGeneration/VillageHerbalist/vessel_finishes.py)、[炼药台材质槽接入](../Publication/HillsVillageRepair20261121/ShopSurfaces/herbalist-workbench.patch) | `/Game/Building/PotionWorkbench20261015/V1/HerbalistVessels/` 已发布 6 个材质实例及 2 个父材质。[本地发布清单与 SHA-256](F:/FPSGAMEData/ArtProduction/VillageHerbalist/VesselFinish20261121/published.json)。本版 NAS 待备份。 |
