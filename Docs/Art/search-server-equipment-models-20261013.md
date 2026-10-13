# 机房设备八件收集物模型交付

2026-10-13。服务器内存条、网卡、机械硬盘、固态硬盘、处理器、显卡、阵列控制卡和计算加速模块均已完成写实模型与 PBR 材质制作。八件模型共用一致的工业设计语言，通过板型、连接器、外壳和散热结构区分身份。

显卡、内存条、SSD 后续按用户提供的三张图片重制为三风扇显卡、黑色散热马甲 DDR4 内存和 M.2 SSD。当前正式外观与新版图标见 [参考图重制](server-reference-remodel-20261013.md)；下方三件的初版文件保留，其他五件继续沿用。

## 八件模型

| 物品 | 制作细节 | 可查看的带材质模型 |
| --- | --- | --- |
| 服务器内存条 | 双面颗粒、注册控制芯片、独立金手指、定位缺口、卡扣边槽、序号贴纸、贴片电容和 PCB 走线 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_ServerRAM.glb) |
| 服务器网卡 | 双口屏蔽连接器、凹入接点、指示灯透镜、金属挡板、散热片、控制芯片与板载元件 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_ServerNIC.glb) |
| 机械硬盘 | 厚铸造底壳、冲压顶盖与卷边、浅压盘形结构、螺钉、侧面安装位、底部控制板和分组后接头 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_HardDisk.glb) |
| 固态硬盘 | 薄金属上下壳、装配缝、沉入式连接器与定位键、金属接点、角部固定螺钉和容量标签 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_SSD.glb) |
| 服务器处理器 | 镍色金属顶盖、绿色封装基板、底部接触阵列、定位标记、旁路元件与开窗防静电保护托 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_ServerCPU.glb) |
| 显卡 | 双风扇、真实弧形叶片、贯通风扇孔、内部鳍片、铜色导热管、背板、独立供电插座和多接口挡板 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_GraphicsCard.glb) |
| 阵列控制卡 | 主散热片、架高缓存小板、支柱与螺钉、存储颗粒、内部数据接口、释放卡扣和缓存储备模块 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_RAIDController.glb) |
| 计算加速模块 | 开口被动散热通道、长条鳍片、保护侧轨、厚背板、通风挡板、供电插座和长条设备编号 | [GLB](../../SourceAssets/SearchServerEquipment20261013/Export/SM_Search_ComputeAccelerator.glb) |

连接器开口、安装孔、卡扣槽和风扇弧面采用真实几何；PCB 走线、丝印、标签和微表面使用原创纹理。物品外观保持材料本色，稀有度沿用玩法设计表。

## 尺寸与资源

| 网格 | 实际外廓 cm | 三角面 | PBR 图集 |
| --- | --- | ---: | --- |
| SM_Search_ServerRAM | 13.80×3.00×0.51 | 9,066 | 2K |
| SM_Search_ServerNIC | 14.51×7.91×1.98 | 14,738 | 4K |
| SM_Search_HardDisk | 14.85×10.05×2.71 | 23,878 | 2K |
| SM_Search_SSD | 9.98×6.98×0.88 | 9,154 | 2K |
| SM_Search_ServerCPU | 6.00×6.00×0.86 | 7,854 | 2K |
| SM_Search_GraphicsCard | 27.94×11.68×3.95 | 48,208 | 4K |
| SM_Search_RAIDController | 17.90×11.86×2.50 | 23,014 | 4K |
| SM_Search_ComputeAccelerator | 29.88×11.96×4.92 | 17,126 | 4K |

每件一个材质槽、一个作者提供的 UCX 碰撞盒，当前交付为 LOD0。显卡的额外几何用于双风扇弧面、鳍片、管路、开孔外壳和接口；细小金手指保留厚度，省去不影响识别的微小圆角。未进行运行性能测试。

各件包含 BaseColor、ORM 和切线法线。BaseColor 使用 sRGB；ORM 为线性 R 环境遮蔽、G 粗糙度、B 金属度；法线源为 OpenGL +Y，UE 导入翻转绿色通道。金属、塑料、芯片封装、板材与纸标签使用分别设定的表面参数，标签图集按实际贴附面的宽高比制作。

可编辑源位于 `SourceAssets/SearchServerEquipment20261013/Authored`，FBX 和 GLB 位于 `Export`。Blender 源采用厘米尺度，FBX 按厘米导入，GLB 按米导出；游戏网格原点位于底部中心。源文件保留分件和倒角修改器。

## UE 保存状态

正式目录为 `/Game/Items/SearchServerEquipment20261013`，包含 `Meshes`、`Materials` 和 `Textures`。共保存并安装 8 个静态网格、8 个材质、24 张纹理，即 40 个 UE 资源包。资产通过同版本 UE 5.8 的独立内容工程导入后安装至主工程相同包路径，后台 commandlet 记录为零错误、零警告。

文件与包路径分别记录在 [模型清单](../../SourceAssets/SearchServerEquipment20261013/model_manifest.json)、[UE 导入记录](../../SourceAssets/SearchServerEquipment20261013/Receipts/ue-import.json) 和 [安装记录](../../SourceAssets/SearchServerEquipment20261013/Receipts/installation.json)。[交付记录](../../SourceAssets/SearchServerEquipment20261013/delivery.json) 区分资产保存与玩法接入状态。

模型和材质已保存到 UE，八张透明背包图标及正式物品定义也已接入；搜索池尚未投放。本次沿用已定稿的稀有度、售价、占格和堆叠数。未打开 UE、启动游戏、生成额外预览或运行测试。

## 背包图标与物品接入

| 物品 | 占格 | 堆叠上限 | 稀有度 | 设计售卖价值 | 正式图标 |
| --- | --- | ---: | --- | ---: | --- |
| 服务器内存条 | 1×1 | 2 | 稀有·蓝 | 450 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_ram_module.png) |
| 服务器网卡 | 2×1 | 1 | 稀有·蓝 | 600 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_network_card.png) |
| 机械硬盘 | 2×1 | 1 | 稀有·蓝 | 700 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_hard_disk.png) |
| 固态硬盘 | 2×1 | 1 | 史诗·紫 | 1000 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_ssd.png) |
| 服务器处理器 | 1×1 | 1 | 史诗·紫 | 1500 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_processor.png) |
| 显卡 | 3×2 | 1 | 史诗·紫 | 2400 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_graphics_card.png) |
| 阵列控制卡 | 2×2 | 1 | 神话·金 | 3600 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_raid_controller.png) |
| 计算加速模块 | 3×2 | 1 | 传说·红 | 6400 | [PNG](../../Content/ColdSteelData/Icons/SearchServerEquipment20261013/search_compute_accelerator.png) |

图标直接从同源 GLB 渲染，为真实透明背景的 RGBA PNG。正方形占格采用 512×512，2×1 采用 512×256，3×2 采用 768×512；物体保持实际比例，内存条斜放以提高单格识别度。图标不包含背景色或稀有度边框，底色由既有背包界面绘制。

八个新 ID 已写入 `Content/ColdSteelData/items.json`，沿用 `material` 非装备分类，显示类型为“机房设备”。`ue_icon` 复用现有缓存和绘制入口，PNG 随 `ColdSteelData` UFS 规则打包；模型目录加入 Cook 引用。`ColdSteelPickupConsumable.cpp` 补齐这八件收集物的世界模型绑定，丢弃与拾取沿用原有通路。

本次是正式物品的首次接入，没有旧实例占格迁移，不改玩家现有背包内容。目录在下次游戏初始化时加载；`sell_souls` 保留设计收购价值，本次未新增出售系统、制作配方或掉落概率。必要编译结果记录在 `Receipts/build-inventory-FPSGAMEEditor.log`、`Receipts/build-inventory-FPSGAME.log` 与交付记录，未执行运行测试。

本轮 Editor 构建失败于现有 `ColdSteelSharedInventorySubsystem.cpp`：`ColdSteelCompartment` 未声明，且 `StampProductionDrop` 为私有成员。Game 构建因此未执行。本任务保留了联机模块源码；物品目录与八张图标已落盘，新增掉落模型分支目前仅完成源码，需后续成功构建后生效。

## 结构参考与原创范围

长条内存的结构比例、缺口和金手指参考 [Kingston DIMM 资料](https://www.kingston.com/dataSheets/KF556C40BBK2-32.pdf)；网卡端口与挡板布局参考 [Intel I350 产品资料](https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ethernet-i350-server-adapter-brief.pdf)；阵列卡的独立散热和内部连接器布局参考 [Broadcom 阵列控制卡资料](https://www.broadcom.com/products/storage/raid-controllers/megaraid-9560-16i)。

本批为按游戏规格设计的原创道具，不是上述产品的精确复刻。未复制第三方网格、贴图或商标；PCB 线路为非功能性视觉图案，设备型号、序号和印刷标签为虚构项目内容。字体沿用工程已有 Noto Sans SC。
