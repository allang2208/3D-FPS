# 丘陵村庄两层店铺与建设卡片

三间店共用子关卡 `/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage`。每家都保留默认破败状态、修复后才出现的陈列，以及与楼梯连通的二层。地块编号与坐标见[三店布局记录](Shops/layout.fragment.json)；工作台局部位置、灯具、窗和货架清单见[原始关卡保存回执摘录](Shops/assembly-receipts.json)。

| 地块 | 地面层与工作台 | 二楼和窗 | 编辑入口 |
|---|---|---|---|
| 01 铁匠铺 | 半开放炉房、铁砧与淬火位，复用 `casting_station`。冷侧成品架陈列斩马刀、唐刀与战锤，台面摆放短刀和锉刀。破败木料移至箱位前沿，留出楼梯口。 | 360 cm 高的卧室，双跑回转梯，三扇用独立铰点转动的窗。炉后使用 R5 烟道和 R8 烟囱。 | [房壳与家具](../../../Tools/WorldGeneration/VillageBlacksmith/LoftR3/assemble.py)、[架子与陈列两态](../../../Tools/WorldGeneration/VillageBlacksmith/forge_weapon_display.py)、[店铺总入口](../../../Tools/WorldGeneration/VillageBlacksmith/author_shop.py) |
| 04 木工工坊 | 木料院、手工桌、木弓和法杖陈列架。修复后启用 `woodworking_bench`、梁下吊灯与补板，破败状态保留断板和散落石块。 | 360 cm 高的起居层和三扇独立铰点窗；楼上书桌有自己的阅读灯。 | [房壳、楼梯和窗](../../../Tools/WorldGeneration/VillageCarpenter/carpenter_shell.py)、[工作台与室内陈设](../../../Tools/WorldGeneration/VillageCarpenter/carpenter_shop.py)、[武器架](../../../Tools/WorldGeneration/VillageCarpenter/carpenter_weapon_display.py)、[梁下吊灯](../../../Tools/WorldGeneration/VillageCarpenter/carpenter_pendant.py) |
| 03 草药铺 | 修补屋顶、地板、外墙和窗洞；修复后恢复 `potion_workbench`、药材架、晒药架、街窗陈列和壁上火炬。 | 360 cm 高的卧室；两跑楼梯通向有护栏的平台。卧床侧有窗，另有起居灯。此处使用房壳窗墙和百叶陈列。 | [两态房屋、窗和工作台](../../../Tools/WorldGeneration/VillageHerbalist/author_shop03.py)、[楼梯与楼板](../../../Tools/WorldGeneration/VillageHerbalist/herbalist_loft.py)、[室内陈列](../../../Tools/WorldGeneration/VillageHerbalist/dressing.py)、[火炬](../../../Tools/WorldGeneration/VillageHerbalist/herbalist_lights.py) |

## 复用作者工程

1. 以已有村庄关卡、对应的 `SourceAssets/TemperateHillsVillage/layout.json`、`house-pieces.json` 和 `RoadMask.png` 为底。布局记录只含三个地块；合并时按房号、工作区 `owner` 和道路入口房号匹配。三家房壳键分别为 `SL_Blacksmith_LoftR3`、`SL_Carpenter_Workshop`、`SL_Packed_House_TypeA_00B`。首次将 04 旧宅替换为工坊时还需要 `SL_Packed_HouseTypeC_00A`。原工程中的 Normandy 套件、Quixel 陈设、酒馆家具与招牌底图、武器网格和既有工作台须按原包名挂载。
2. 铁匠铺沿用已发布的 `ArtPassR2`、`LoftR3`、`MasonryR5`、`DetailR6`、`WindowR7`、`ChimneyR8` 部件。当前装配由 `LoftR3/publish_revision.py` 调入 `author_shop.build_shop`。已有铁匠铺只更新武器架时，使用 `save_weapon_display.py`。这些入口需要先有木工道具的铁和黄铜表面。窗体使用 R7b 窗扇网格和 R7 开洞墙，原生铰点与摆动碰撞的增量以 Git 版本 `e8b7284d` 下的 `ColdSteelWindow.h/.cpp` 为基线。[窗体补丁](Shops/authored-window-hinges.patch)
3. 木工工坊的 `Props/author_props.py` 与 `Props/surfaces.py` 生成专用道具和表面，`Props/import_props.py` 负责 UE 包。先按 `Save-GroundDeck.ps1` 和 `author_ground_deck.py` 的配方取得完整地板、磨损板和拼补板；03 草药铺也依赖这些部件。已有 04 店铺用 `Save-Workshop.ps1` 调用 `publish.py`。从旧宅初次布置时，`prepare_plot.py` 还会调用完整村庄作者工程的 `draw_plan.py` 生成地面与道路数据。陈列架从正式 `bows.json`、`staffs.json` 和 `staff-gunsmith.json` 读取装备。[木工道具配方](../../../Tools/WorldGeneration/VillageCarpenter/Props/author_props.py)
4. 草药铺用 Blender 执行 `author_supplies.py` 生成晒药架、篮筛、窗盆、药束和架沿，`dressing.py` 导入这些 FBX 并按材质槽绑定。招牌脚本 `paint_sign.py` 借用已有酒馆招牌图集的侧边与五金区域，重画两态牌面；接着由 `Save-Workshop.ps1 -Herbalist` 调用 `VillageHerbalist/publish.py`。铁匠铺的 R7 开洞墙、木工地板、草药材质和已有炼药台都需在原包名可用。[药具模型配方](../../../SourceAssets/HillsVillageHerbalist/author_supplies.py)、[草药铺保存入口](../../../Tools/WorldGeneration/VillageHerbalist/publish.py)
5. 独立保存脚本导入 `Tools/WorldGeneration/AbandonedVillage/layout_geometry.py`。有完整作者工程时沿用该模块；从发布包恢复独立三店工具时，可将截取的三个函数放回同路径。全村制作流程另有房壳分派、房内采光、院内预留与道路绘制的接入位置。[共享几何函数](Shops/layout_geometry.shop.py)、[全村脚本接入片段](Shops/village-authoring-excerpts.md)

## 运行时工作台

铁匠铺的两态组件由 `VillageShop.*` 标识，另两家分别使用 `VillageCarpenter.*` 与 `VillageHerbalist.*`。屋内固定工作台以 `DA_VoxelBuildPalette` 中各自的预制件条目取得网格。村庄修复同步后，工作台宿主切换显示与碰撞，并按可用性注册到 `AVoxelBuildWorld`。原生宿主与共享外墙灯分别收录在[11 月 19 日工匠发布](../ArtisanVillage20261119/README.md)和[11 月 20 日村庄集成](../ConversationDelivery20261120/README.md)。

恢复木工坊原生文件时，在 19 日的 `HillsCarpenterWorkshop.cpp` 上合并 20 日的同名补丁。草药铺 C++ 实现沿用 20 日的快照。对已接入 `AVoxelBuildPrefabActor::IsSceneStation()` 的工程，两个宿主头文件各有一行固定场景工作台覆盖声明；铁匠铺的完整头文件和最终炉火照明已在本批材质目录留存。[两个宿主头文件增量](Shops/workshop-headers.patch)、[铁匠铺与工作台材质](README.md)

## 建设卡片

村庄建设面板按项目 ID 从 `Content/UI/VillageConstruction/` 读取同名 PNG。项目在 `Config/DefaultGame.ini` 中以 `DirectoriesToAlwaysStageAsUFS` 随包收录该目录。三张原图都是 1254 × 1254 的透明图。铁匠铺与木工坊采用 Windows WPF Fant 滤镜，将原图等比缩至 244 像素后居中写入 256 像素画布。草药铺先按 alpha 大于 16 的范围裁切，用 Pillow Lanczos 缩至 240 像素，再居中写入同尺寸画布。[原图文件名、恢复依据与正式散列](Shops/construction-cards.json)

两种配方均接受原图目录与输出目录。PowerShell 使用 `artisan-cards.ps1 -SourceDirectory <原图目录> -OutputDirectory <输出目录>`；Python 使用 `python herbalist-card.py <原图目录> <输出目录>`。本机 `F:/FPSGAME-Recovery-Work-20261120/VillageShopThread20261121/OriginalIcons/` 保存三张正式卡片，其中铁匠铺和木工坊来自删除前的原始 PNG 字节，草药铺按原图和配方重建，MD5 与 UE 导入记录一致。[铁匠铺与木工坊卡片配方](Shops/artisan-cards.ps1)、[草药铺卡片配方](Shops/herbalist-card.py)

本批归档三家店的作者源码、独立保存入口、项目自有布局和共享代码片段。已保存的关卡、原模型、第三方素材与正式图片留在本机完整工程及相应备份中。此次归档未重新生成关卡、导入资产或运行游戏。[按工程原路径发布的源码清单](Shops/normal-paths.json)
