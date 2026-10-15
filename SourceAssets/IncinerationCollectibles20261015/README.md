# 焚化区收集物

当前活动美术版本为 [VisualRefineV2](VisualRefineV2/README.md)：六件模型、PBR 和背包图标已逐件精修并安装。稳定网格路径仍为 V1/Meshes，活动材质与纹理在 V2；当前源文件以 `model_manifest.json` 指向的 VisualRefineV2 配方和导出为准。下文初始制作与 IconLayoutV2 保留为恢复记录。

用户要求只做蓝色及以上的收集物。本批新增六件物品，并为焚化区现有普通搜索容器绑定专属掉落池。运行工程为 `D:/FPS3D/FPSGAME`。

| 物品 | 稀有度 | 占格 | 售价（灵魂） | 目录 ID |
| --- | --- | --- | --- | --- |
| 密封呼吸滤罐 | 蓝色／rare | 1×1 | 450 | search_sealed_respirator_filter |
| 耐火陶瓷组件 | 蓝色／rare | 2×1 | 620 | search_refractory_ceramic_module |
| 高温热电偶 | 蓝色／rare | 2×1 | 850 | search_high_temperature_thermocouple |
| 工业过滤芯 | 蓝色／rare | 1×2 | 780 | search_industrial_filter_cartridge |
| 封存焚化事故档案 | 紫色／epic | 2×2 | 1900 | search_sealed_incineration_archive |
| 烟气净化催化芯 | 紫色／epic | 2×2 | 2400 | search_flue_gas_catalytic_core |

六件均为可携带、丢弃、拾取和出售的非装备收集物，采用既有背包、共享容器和商店事务。未增加呼吸防护、装备功能、维修操作或制作配方。蓝色及以上限制只作用于本批物品与焚化区五类普通搜索池；其他区域、通用宝箱、怪物掉落保持原配置。

## 资产与恢复

精确几何由后台 Blender 制作，分件源保存在 `Authored`，游戏 FBX/GLB 在 `Export`。包含滤罐螺纹与运输封盖、陶瓷通道与钢托架、热电偶探杆及导线、过滤芯真实褶皱与支撑圈、分层档案页与封条、催化芯蜂窝通道和提手。六件共用 4096×4096 BaseColor、ORM、Normal 图集，原创 CS 标识。

模型保留 `/Game/Items/IncinerationCollectibles20261015/V1/Meshes`，精修 PBR 保存至 `/Game/Items/IncinerationCollectibles20261015/V2`。物品目录为 `Content/ColdSteelData/items.json`；六张透明图标由当前活动 GLB 渲染，生产路径为 `Content/ColdSteelData/Icons/IncinerationCollectibles20261015`。单行／单列物品沿占格方向居中，图标每格 512 像素。`ColdSteelPickupConsumable.cpp` 接入原生地面模型分支，`DefaultGame.ini` 包含 Cook 目录。

制作顺序：`setup_pipeline.py` → `prepare_textures.py` → Blender `author_models.py` → Blender `render_icons.py` 与 `import_staged.ps1` → `install_staged.py` → `integrate_data.py` → `update_catalog_metadata.py` → `build_native.ps1`。Setup 复用发电区作者工具；本批新增物品几何独立编写。已安装资产不盲目重跑导入，后续精修使用独立修订目录。这里只渲染交付所需背包图标，未制作验收预览或游戏截图。

## 掉落分配

绑定全部 40 个候选 ContainerId，每局实际选出 17–20 个实体箱柜、22–25 个搜索入口。耐热柜上层抽屉、下层柜门与档案柜三层抽屉各自独立搜索。三间房搜索入口分别为 4–5、10–11、8–9。

全部五池 `count_weights=[0,100,0,0]`，首次搜索固定生成一件，因此下列权重也就是该池单次出现百分比。

| 容器／池 | 单次搜索内容及概率 |
| --- | --- |
| 检修工具箱／incineration_maintenance | 精密机件组 25%、装配组件盒 20%、锻造合金坯 20%、高温热电偶 15%、工业数字万用表 12%、精密检修工具组 6%、充电式冲击扳手 2% |
| 防护用品柜／incineration_protection | 密封呼吸滤罐 70%、高温热电偶 10%、工业过滤芯 10%、精密检修工具组 10% |
| 耐热柜与抽屉／incineration_heat | 耐火陶瓷组件 45%、高温热电偶 30%、锻造合金坯 15%、功率控制模块 8%、烟气净化催化芯 2% |
| 停尸间档案柜／incineration_records | U盘 65%、档案备份磁带 25%、封存焚化事故档案 8%、签章行政档案 2% |
| 滤芯运输箱／incineration_filters | 工业过滤芯 65%、密封呼吸滤罐 25%、烟气净化催化芯 10% |

无白色或绿色条目，无食物饮水混入。第三间房独立宝箱继续使用通用地牢池；本批没有修改场景几何、宝箱或刷怪配置。

## 联机与存档

复用 `ColdSteelSceneLoot` 的服务器一次生成逻辑，使用既有 RunId、完整容器身份、共享库存版本及事务处理。客机不生成独立掉落；个人搜索揭示进度不改变共享实物。已生成、已取空、已保存的容器不重置补刷，不修改玩家存档。既有未结算空柜沿现有首次生成流程处理。

掉落表由进程首次读取后缓存。已运行的游戏需要下次启动加载新数据；新一轮地牢使用新容器状态。后续增加候选点时，需把新增稳定 ContainerId 同步加入绑定表；外观相同不会自动继承掉落。

## 交付状态

素材导出、UE 保存／安装、目录接入与正式构建分别记录在 `model_manifest.json`、`presentation.json`、`Receipts/ue-import.json`、`Receipts/installation.json`、`Receipts/data-installation.json`、`Receipts/build.json`。最终收尾状态见 `delivery.json`。

按用户规则未运行自动化、游戏或主客机测试，没有打开交互编辑器。既有搜索测试的绑定数、池数和物品数预期随新增目录更新，但未执行测试。视觉与玩法由用户测试。

## 图标标准复核与 V2 居中

用户随后要求对照其他收集物复核朝向及背包图标标准。六张图沿用 `collection_icon_orientation.py`，2×1 水平、1×2 竖直、方形采用立体视角，尺寸为每格 512 像素，RGBA 透明背景。

原图按网格包围盒角点取景，热电偶及导线造成的空白体积使其可见轮廓偏左下。现改用交付网格实际顶点在相机中的投影范围，旋转后重新居中和等比留边，重新渲染六张图；模型、材质、占格与朝向规则不变。V2 作者图在 `IconLayoutV2`，已发布到原正式图标路径；旧图及原清单已归档至工程 `trash/m66-incineration-retired-20261015/SourceAssets/IncinerationCollectibles20261015/BeforeIconLayoutV2`。

恢复时，`render_icons.py` 输出 `icon-layout-v2.json`，由 `publish_icon_layout_v2.py` 发布图标及生产清单；首次完整恢复随后运行 `integrate_data.py`。这次按用户要求检查 PNG 尺寸／透明通道、轮廓边距／中心及目录引用，证据为 `Receipts/icon-standard-review.json`；没有打开 UE 或运行游戏。
