# 检修材料模型与背包图标

五件检修搜索物沿用已确定的 V2 清单，完成写实模型、PBR 纹理、透明背包图标和正式物品目录接入。原料、零件包装与整组库存单位保持一致，模型里的螺钉或单根木条不会变成额外拾取条目。

## 制作内容

| 物品 | 稀有度 | 占格 | 最大堆叠 | 模型细节 | 背包图标 |
| --- | --- | --- | ---: | --- | --- |
| 锻造合金坯 | 稀有·蓝 | 1×2 | 4 | 倒角坯体、端面切削纹、中段保护纸、折边与批次标签 | [PNG](../../Content/ColdSteelData/Icons/SearchMaintenance20261012/search_forging_alloy_blank.png) |
| 装配组件盒 | 稀有·蓝 | 2×1 | 3 | 有厚度的纸盒、六格隔板、局部纸套、压缩弹簧、定位销、螺栓与垫圈 | [PNG](../../Content/ColdSteelData/Icons/SearchMaintenance20261012/search_assembly_component_box.png) |
| 树脂胶包 | 优秀·绿 | 1×1 | 5 | 双腔鼓起的铝塑袋、中央隔带、压封纹、真实撕口、贴合曲面的标签 | [PNG](../../Content/ColdSteelData/Icons/SearchMaintenance20261012/search_resin_adhesive.png) |
| 层压木条 | 优秀·绿 | 1×3 | 5 | 成束木条、连续纵向木纹、端面分层纹理、轻微错位和两道环绕纸带 | [PNG](../../Content/ColdSteelData/Icons/SearchMaintenance20261012/search_laminated_strip.png) |
| 精密机件组 | 稀有·蓝 | 2×1 | 3 | 金属保护托、开槽泡棉、空心衬套、轴承圈与滚珠、阶梯轴、齿形件和定位环 | [PNG](../../Content/ColdSteelData/Icons/SearchMaintenance20261012/search_precision_mechanism.png) |

图标从交付 GLB 直接渲染，使用透明 RGBA PNG，不叠加背景、地面阴影、文字徽标或稀有度色块。合金坯和木条以竖向展示，两类零件盒横向展示；图片宽高比与占格一致，物体保持实际比例。图标通过既有 `ue_icon` 加载与缓存进入背包、仓库和物品详情。

## 尺寸与材质

| 网格 | 导出外廓 cm | 三角面 | 图集 |
| --- | --- | ---: | --- |
| SM_Search_Alloy | 27.73×7.01×4.01 | 4,448 | 2K |
| SM_Search_Assembly | 20.00×13.21×5.11 | 27,026 | 4K |
| SM_Search_Resin | 12.00×8.00×1.66 | 15,044 | 2K |
| SM_Search_Wood | 54.86×6.04×3.01 | 5,488 | 2K |
| SM_Search_Precision | 18.00×12.03×3.81 | 27,222 | 4K |

各件采用独立 BaseColor、ORM 和切线法线图集，ORM 分别存储环境遮蔽、粗糙度、金属度；法线源为 OpenGL +Y，导入 UE 时翻转绿色通道。金属、牛皮纸、木材、泡棉和胶袋分别设置表面参数。两个近景零件盒保留真实内部分件，其余物品以轮廓和材料特征为主。当前交付为 LOD0，各件一个材质槽和一个作者提供的 UCX 简单碰撞盒；未进行游戏性能测试。

源文件保留可编辑部件与倒角修改器，FBX 显式三角化、输出切线，游戏导出原点位于底部中心。Blender 源按厘米制作，FBX 按厘米导入，GLB 使用米。模型和标签均为本项目原创，字体沿用工程内的 Noto Sans SC。

## 配方对应

沿用 [V2 配方设计](../Gameplay/search-item-catalog-v2-20261012.md) 中的映射：

- 锻造合金坯：铁匠台高地双手剑使用 1 块，符文剑与寒晶剑各使用 2 块。
- 装配组件盒：枪械组装台十一种枪械配方使用 1 至 3 盒。
- 树脂胶包、层压木条：木工台木制弓臂各使用 1 个库存单位。
- 精密机件组：ASH-12、SVD 各使用 1 组，PKM、201 轻机枪各使用 2 组。

这部分仍为设计映射。本次制作模型、图标和正式物品定义，不修改制作台的运行时扣料配方，也不投放容器搜索池。目录保留既定设计售卖值 320、360、60、90、240 灵魂，未新增售卖系统。

## 保存与接入

正式模型目录为 `/Game/Items/SearchMaintenance20261012/Meshes`，同目录下的 `Materials`、`Textures` 存放依赖资源，共 5 个静态网格、5 个材质、15 张纹理。导入通过同版本 UE 5.8 的独立内容工程执行，再将资源包安装至主工程相同 `/Game` 路径；期间保留用户正在运行的 UE 会话。

背包图标位于 `Content/ColdSteelData/Icons/SearchMaintenance20261012`；源目录为 `SourceAssets/SearchMaintenance20261012`，包含 `Authored`、`Export`、`Textures`、制作脚本和导入回执。模型目录加入 Cook 引用，PNG 由现有 `ColdSteelData` UFS 规则打包。

`ColdSteelPickupConsumable.cpp` 增加五件检修物的模型绑定，复用现有掉落与拾取通路。正式物品定义为新 ID，不改已有玩家实例、不自动向背包发放物品。当前游戏实例需要在下次初始化目录后才能读取这些新定义。

实际导入与安装分别记录在 [UE 导入回执](../../SourceAssets/SearchMaintenance20261012/Receipts/ue-import.json) 和 [安装回执](../../SourceAssets/SearchMaintenance20261012/Receipts/installation.json)。必要构建状态见 [交付记录](../../SourceAssets/SearchMaintenance20261012/delivery.json)。本次只渲染交付所需背包图标，未额外生成预览、启动游戏或运行测试。

本次 `FPSGAMEEditor` 与 `FPSGAME` Development 构建均为 `Result: Succeeded`，记录分别位于 `Receipts/build-FPSGAMEEditor.log` 与 `Receipts/build-FPSGAME.log`。期间用户原有编辑器会话结束后才进行常规构建，本任务未关闭或重新打开 UE。
