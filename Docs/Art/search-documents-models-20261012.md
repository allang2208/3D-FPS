# 文件材料四件收集品模型交付

2026-10-12。四件收集品已完成可编辑 Blender 源模型、FBX、带材质 GLB 和 UE 静态网格制作，配套 4 个材质与 12 张纹理已保存并安装到主工程 `Content/Items/SearchDocuments20261012`。本次同时把汽水、法棍面包调整到绿色 `uncommon` 档，并增加读取旧存档时的稀有度同步。

## 四件模型

| 物品 | 既定稀有度与售卖设计 | 背包占格 | 实际外廓 cm | 制作细节 | 可查看的带材质模型 |
| --- | --- | --- | --- | --- | --- |
| U盘 | 稀有·蓝，360 灵魂 | 1×1 | 5.93×1.92×0.99 | 拉丝金属外壳、装配缝、中空 USB 接头、锁定孔、绝缘舌片和四条金属触点、贯通挂绳孔、螺钉与底部序号 | [USB GLB](../../SourceAssets/SearchDocuments20261012/Export/SM_Search_USBDrive.glb) |
| 档案备份磁带 | 史诗·紫，800 灵魂 | 1×1 | 10.99×10.04×2.05 | 注塑上下壳、底部单卷轴凹槽与驱动环、滑动口、写保护滑块、防滑筋、固定螺钉和编号标签 | [磁带 GLB](../../SourceAssets/SearchDocuments20261012/Export/SM_Search_ArchiveTape.glb) |
| 加密行政资料盒 | 神话·金，1600 灵魂 | 2×2 | 23.42×18.13×6.06 | 有内腔的箱体、密封条、铰链销、金属锁扣、空心提手、加强筋、橡胶脚、封签；源文件保留泡棉、编号介质和密封文件袋 | [资料盒 GLB](../../SourceAssets/SearchDocuments20261012/Export/SM_Search_EncryptedCase.glb) |
| 签章行政档案 | 史诗·紫，900 灵魂 | 2×2 | 32.00×24.00×3.07 | 硬纸封面、23 层有厚度的纸束、轻微错页与翘曲、布质书脊、分页签、黄铜孔环、棉质装订绳、原创签章与封条 | [档案 GLB](../../SourceAssets/SearchDocuments20261012/Export/SM_Search_CertifiedArchive.glb) |

售价和占格沿用 [V2 物品设计](../Gameplay/search-item-catalog-v2-20261012.md)，不代表本次已经实现收购逻辑。资料盒交付为闭合静态收集品；源文件分件可编辑，本次未制作开盖动画。

## 材质与几何

采用精确硬表面建模、真实厚度和边缘倒角，金属、塑料、橡胶、纸张分别设置粗糙度与金属度。表面有克制的拉丝、注塑颗粒、纸纤维及印刷细节，不用稀有度颜色给模型整体染色。

每件一套 BaseColor、ORM、Normal 图集；ORM 通道为 R 环境遮蔽、G 粗糙度、B 金属度。USB 与磁带使用 2K，资料盒与档案使用 4K。法线源为 OpenGL +Y，UE 导入翻转绿色通道；BaseColor 使用 sRGB，ORM 与 Normal 使用线性数据。UE 材质按主工程 Substrate 管线制作。

| 网格 | 三角面 | 材质槽 | 碰撞 |
| --- | ---: | ---: | --- |
| SM_Search_USBDrive | 7,916 | 1 | 作者提供的 UCX 简单盒体 |
| SM_Search_ArchiveTape | 21,914 | 1 | 作者提供的 UCX 简单盒体 |
| SM_Search_EncryptedCase | 27,898 | 1 | 作者提供的 UCX 简单盒体 |
| SM_Search_CertifiedArchive | 24,276 | 1 | 作者提供的 UCX 简单盒体 |

当前网格保留近景结构，未另制 LOD；Nanite 关闭。Blender 源按厘米制作，导出 FBX 使用厘米约定，GLB 使用米。原点沿用底部居中的建模基准，+Z 向上。倒角表面在求值后重新映射至各自图集区域，FBX 显式三角化并输出切线；修正后的导入完成，未再报告首轮的近零切线/副法线警告。

## UE 与源文件路径

四件 UE 模型路径分别为：

- `/Game/Items/SearchDocuments20261012/Meshes/SM_Search_USBDrive.SM_Search_USBDrive`
- `/Game/Items/SearchDocuments20261012/Meshes/SM_Search_ArchiveTape.SM_Search_ArchiveTape`
- `/Game/Items/SearchDocuments20261012/Meshes/SM_Search_EncryptedCase.SM_Search_EncryptedCase`
- `/Game/Items/SearchDocuments20261012/Meshes/SM_Search_CertifiedArchive.SM_Search_CertifiedArchive`

对应的可编辑源位于 `SourceAssets/SearchDocuments20261012/Authored`；FBX 和 GLB 位于 `Export`；PBR 源纹理位于 `Textures`。`Scripts/prepare_textures.py`、`author_models.py`、`import_assets.py` 保留制作与导入逻辑，`model_manifest.json` 记录各件身份、尺寸、部件及文件位置。

首轮主工程 commandlet 在执行导入脚本前遇到 `Cast of Package /Script/FPSGAME to SkeletalMeshComponent failed`。本批改用同版本 UE 5.8 的独立内容工程导入，再将保存的资源包安装到主工程完全相同的 `/Game` 路径。资源只依赖本批静态网格、材质和贴图，不依赖主工程的自定义角色类；本任务未改动引发启动错误的代码。

实际保存结果见 [导入记录](../../SourceAssets/SearchDocuments20261012/Receipts/ue-import.json)，安装的 20 个包见 [安装记录](../../SourceAssets/SearchDocuments20261012/Receipts/installation.json)。独立内容工程和首次失败日志保留在源资产目录。

## 汽水与法棍稀有度

`Content/ColdSteelData/items.json` 中 `soda_can`、`baguette_bread` 改为 `uncommon`，即用户指定的绿色优质档；现有 UI 对该档的文字为“优秀”。两件物品的效果、价格、占格和数量规则保持原值。相应源制作脚本与 V2 设计清单同步更新，避免以后重建覆盖稀有度。

`ColdSteelProfileRuntime.cpp` 的旧实例迁移会在下次读取存档时同步这两件物品的 `rarity`，已有 `grade` 时同步该字段；保留物品身份、数量和存放位置。构建状态单独记录在 [交付记录](../../SourceAssets/SearchDocuments20261012/delivery.json)。

模型制作阶段的 Editor 构建曾被联机模块 `ColdSteelPlayerState` 的编译错误阻塞，Game 构建随之未执行，本任务保留了联机模块的现有改动。背包接入阶段重新执行必要构建，Editor 与 Game 均已成功；旧存档稀有度迁移将在使用本次构建程序读档时执行，未运行读档测试。

## 背包占格与图标接入

用户确认第二件口称“硬盘”的对象为档案备份磁带；没有新增或改动机房设备的机械硬盘。四件物品已写入正式 `Content/ColdSteelData/items.json`，归文件材料，均不堆叠。

| 物品 | 占格 | 正式透明图标 |
| --- | --- | --- |
| U盘 | 1×1 | [PNG](../../Content/ColdSteelData/Icons/SearchDocuments20261012/search_usb_drive.png) |
| 档案备份磁带 | 1×1 | [PNG](../../Content/ColdSteelData/Icons/SearchDocuments20261012/search_archive_tape.png) |
| 加密行政资料盒 | 2×2 | [PNG](../../Content/ColdSteelData/Icons/SearchDocuments20261012/search_encrypted_archive_case.png) |
| 签章行政档案 | 2×2 | [PNG](../../Content/ColdSteelData/Icons/SearchDocuments20261012/search_certified_admin_archive.png) |

图标为同源模型直接渲染的 512×512 RGBA PNG，使用透明背景，保持物体比例，U盘沿对角方向布局。`ue_icon` 绑定既有文件图标加载与缓存，底色由既有稀有度界面绘制，图标不包含背景色、占格线或文字徽标。四件物品采用方形占格，沿用现有方格物品不旋转规则；本次为首次创建正式物品定义，无需迁移此前不存在的背包实例。

掉落分支补齐这四件物品的 `world_mesh` 绑定，并为模型目录加入 Cook 引用。PNG 沿用 `FPSGAME.Build.cs` 中整个 `ColdSteelData` 的 UFS 打包规则，不需要另导入 UI Texture2D。制作记录见 [图标清单](../../SourceAssets/SearchDocuments20261012/inventory_icons.json) 和 [目录接入记录](../../SourceAssets/SearchDocuments20261012/Receipts/inventory-integration.json)。

本轮必要构建记录为 `Receipts/build-inventory-FPSGAMEEditor.log` 与 `Receipts/build-inventory-FPSGAME.log`，两者均为 `Result: Succeeded`。未打开 UE 编辑器、启动游戏或追加背包运行测试。

## 来源与交付范围

几何、标签、虚构编号和签章均为本次制作；标签字体复用工程的 Noto Sans SC。未复制产品品牌标识或第三方模型、贴图。结构资料参考 [Kingston USB 存储产品资料](https://www.kingston.com/datasheets/DTR30_en.pdf) 与 [IBM 磁带写保护开关说明](https://www.ibm.com/docs/en/ts4300-tape-library?topic=media-write-protect-switch)，用于理解现实物体结构，成品是游戏原创道具。

本次完成模型资产、正式物品定义、背包占格和透明图标。容器搜索池尚未投放，未向玩家背包自动发放物品；`sell_souls` 保留既定收购设计值，未增加售卖系统。首次交付未渲染；随后按用户“给我图片预览”的要求，用已交付 GLB 在 Blender Cycles 中生成每件两个角度，共 8 张 1600×1200 图片，见 [预览文件](../../SourceAssets/SearchDocuments20261012/Previews/preview_manifest.json)。图片为模型棚拍预览；未启动游戏或运行玩法测试，实际引擎外观与玩法由用户测试。
