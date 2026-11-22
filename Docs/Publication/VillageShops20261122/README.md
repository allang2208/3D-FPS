# 丘陵村庄店铺与居民交接

此批对应六家店铺的陈设、照明与风雨招牌，修女后颈发束及交互描边、枪匠头颈和绑骨、城门内外的路灯、店内床凳和教堂长椅。正式村庄子关卡使用 `/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage`。本机工程以 `Content/` 访问 F 盘正式资产；恢复相同外观需要相应版本的地图、网格、材质、骨架和原始授权资产。

## 制作与接入

- 面包房和枪店的石墙、木地板取自已有房屋的模块与材质槽。[房屋模块配方](../../../Tools/WorldGeneration/AbandonedVillage/shop_house_modules.py)。木工坊木屑、堆料、五金、洗具水桶与工具箱分别见[院落配方](../../../Tools/WorldGeneration/VillageCarpenter/YardDetail)和[室内配方](../../../Tools/WorldGeneration/VillageCarpenter/Interior)。
- 六店共用的双面行标按门面和岔路放置。铁匠铺另有侧吹炉、煤床、烟道和独立铁件。[店面行标](../../../Tools/WorldGeneration/AbandonedVillage/trade_sign_layout.py) · [炉床、吊挂与木纹](../../../Tools/WorldGeneration/VillageBlacksmith/ForgeR2) · [行业图案](../../../SourceAssets/HillsVillageTradeSigns)。
- [修女发束](../../../Tools/ChapelNun/author_nape_hair.py)、[NPC 轮廓与店主高光](../../../Tools/ResidentInteraction)和[枪匠头部与骨架配方](../../../Tools/VillageGunsmith)分别维护。枪匠使用获选三视图、Meshy 头模及整身绑骨、工程内 Jason 身体骨架。需要重制时从本机 `SourceAssets/VillageGunsmith` 取批准的参考、网格、蒙皮和组装数据。公开配方通过运行环境取得凭据。
- 家具的网格、槽位、进出位置与动作见[村庄家具配置](../../../Content/ColdSteelData/village_furniture_rest.json)。两套角色的教堂坐卧动作和相机键位见[共享配置目录](Integration/config-keys.json)。室内灯取法杖光照配置，室外路灯跟随修复状态及昼夜时钟。
- [完整工程的功能源码快照](Implementation/Source/FPSGAME)按原工程路径组织。同名共享文件要按功能合并。[共享宿主的函数与接入位置](Integration/host-hooks.json)标明函数摘录及宿主调用；使用它们时保留当前工程的其他分支。此前的村民与工匠宿主见[工匠系统](../ArtisanVillage20261119/README.md)和[店员系统](../ConversationDelivery20261120/README.md)。

## 本机恢复点

| 内容 | 位置 |
| --- | --- |
| 六店各阶段的正式关卡、修改前版本、模型制作源和发布记录 | `F:/FPSGAMEData/ArtProduction/HillsVillageShops/` 各批次的 `Before`、`Saved` 与发布回执 |
| 面包房与枪店的墙地面、柜台和枪匠 | `F:/FPSGAMEData/ArtProduction/HillsVillageBakery/`、`F:/FPSGAMEData/ArtProduction/VillageGunshop/` |
| 店主反光、丘陵进图分批、主路灯具 | `F:/FPSGAMEData/ArtProduction/ResidentInteraction/ShopResponse-20261122/`、`F:/FPSGAMEData/ArtProduction/HillsEntryLoading/20261121-ResidentBatches/`、`F:/FPSGAMEData/ArtProduction/VillageRoadLamp/MainStreet-20261121-233526/` |
| 修女后颈发束 | `SourceAssets/ChapelNun20261115/NapeHairR10/` 和 `/Game/Characters/ChapelNun20261115/NapeHairR10/` |
| 凳面碰撞、材质与源码恢复版本 | `F:/FPSGAMEData/ArtProduction/HillsVillageShops/ShopNetworkAndDistance-20261122/sources.zip` 与同目录 `sources.json`；材质修复配方见 [MaterialRepair](MaterialRepair/) |
| 一次性文件的原位置、trash 位置、散列和已解除的宿主联接 | `F:/FPSGAMEData/ArtProduction/HillsVillageShops/Closeout-20261122/trash-manifest.json`。原来的 D、F 盘分别保管各自的 `trash/VillageShopsCloseout-20261122/` |

## 已有检查记录

[交付记录](delivery.json)保留地图版本、联机结果和存储清单摘要。隔离模块下，双人离场与返回 27 项、教堂长椅 7 项、工匠交易和重连 58 项通过。客户端的装饰裁剪、外观释放和整村关卡卸载各有自己的条件。上一次 D3D12 采样没有完成近村与远村的显存对照；当次正式编辑器构建遇到手持木火把接口缺失。本次 Git 整理沿用这些历史结果。
