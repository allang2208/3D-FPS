# 员工生活区主题：来源与恢复边界

本批规则建筑、家具、床铺、柜体、淋浴设备、餐桌/娱乐设施、标识和 V1 织物纹理由本机作者脚本制作，
可编辑源在 `SourceAssets/DungeonStaffLiving20261002/Authored`。

复用本工程此前保存的资产与制作助手：

- `DungeonTileFracture20260922` 的认可剥落瓷砖，通过 `DungeonRoomShells20260922/Scripts/corridor_surfaces.py` 继承几何、UV 和材质槽。
- `WallUpgrade20260924` 的混凝土/砂浆，以及 `SeamMetal20260923` 的金属、管件表面；继续受其原素材来源和授权约束。
- `AtmosphereV2/RoomInteriors/WorkbenchKit` 的扫描木材实例；本批只引用已安装材质，不重新下载或复制第三方贴图。
- 标识使用本机 Windows 的 Microsoft YaHei 字体栅格化；没有导出或分发字体文件。

没有下载新的第三方模型，没有恢复被用户否决的地牢 5080 候选。
作者脚本/轻量配置、实际 Blender/FBX/纹理、已安装 UE 包和本机制作回执是不同的恢复层。
本轮没有执行 Git 发布；继承资产及二进制原件继续遵循工程现有来源与再分发边界。

## 精修 V3 复用来源

- 深蓝地毯使用已安装的 `GodSpaceLayout20260927` 地毯 V2，继承 `SubstrateMaterials/Textures/02_Upholstery/Textiles/T_Carpet_01` 的来源与原工程授权。新材质只改本批投影与遮罩；未改主神空间资产。高度仍为由法线近似重建的表面场，并非原始扫描高度。
- 床品、毛巾及洗衣篮布品引用已有 Hospital Bed 的 LinenBaseColor / LinenNormal / LinenMR，使用图集中干净的布料区域；新几何由本机制作。署名：This work is based on [Hospital Bed](https://sketchfab.com/3d-models/hospital-bed-f8c13a19e84343e7b644c19f7b9488d3) by [loxfear](https://sketchfab.com/loxfear), licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). 原始记录：`SourceAssets/HospitalBed20260929/license.txt`。
- 细纤维法线复用工程内的 `SubstrateMaterials/Textures/02_Upholstery/Textiles/T_TextilePlain_N`，沿用原资产库授权。
- 排水格栅直接复用 `DungeonRoomShells20260922/Scripts/room_detail_geometry.py` 的 `grate` 制作函数；钢件、法兰与紧固件继续引用工程既有材质。
- V3 告示内容由本批作者脚本编排，Microsoft YaHei 仅栅格化进入公告纹理，未复制字体文件。

精修源在 `SourceAssets/DungeonStaffLiving20261002/RefinementV3/Authored`；没有新增第三方下载。

## 物件与厕所 V5

V5 马桶、厕所隔墙与门、球拍、冰箱与台下柜活动门、水壶、咖啡机及杯子均由本地 Blender 尺寸化脚本制作。
卫生间标识为本地编排文字，Microsoft YaHei 与 Arial 仅栅格化，未分发字体文件。
台球桌台呢复制既有员工区地毯 PBR 图并创建独立绿色实例，沿用上面的地毯素材授权和近似高度说明。
毛巾筐继续引用已有 Hospital Bed / 工程细织物材质；水桶继续引用 V4 本地制作材质。
没有新增第三方模型或素材下载，未修改原素材库包。可编辑源在 `RoomDetailsV5/Authored`。

## 墙内厕所、水壶与字体 V6

墙体裁门、内部结构、水壶、电线、插座和插头为本地尺寸化建模；水壶不锈钢与聚合物表面为本地程序材质。
公告继续使用 V3 自编内容，全部标牌按实际比例重新栅格化 Microsoft YaHei 字形，未分发字体文件。
马桶复用 V5 原创模型，洗手盆与镜子复用 V4，本轮没有第三方模型或贴图下载。


## 咖啡机 V7

咖啡机外壳、开放出杯空腔、接水盘、仪表、旋钮、萃取头、蒸汽管与厚壁杯子均由本地 Blender 尺寸化建模。
不锈钢与橡胶复用 V6 本地程序材质；涂层、陶瓷釉面、咖啡油脂和状态显示为本轮本地新制材质。
没有新增第三方模型、纹理、字体或其他下载，未更改已有资产库源包。
完整源在 `CoffeePolishV7/Authored`。
