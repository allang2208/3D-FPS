# 机房硬件原创标识与显卡细化

> 后续调整：显卡现为2×1，条状图标采用居中布局；详见 [R2布局](collection-icon-layout-r2-20261013.md)。旧CSR3和品牌版制作输出已归档，CSR3B几何仍用于当前CSR3C网格；恢复链见 [整理发布](../Publication/SearchCollectibles20261013/README.md)。

2026-10-13。当前显卡、内存条和 SSD 的模型、4K PBR 图集及透明背包图标采用此版本。资源已保存到 `/Game/Items/ServerOriginalMarks20261013/Final`，物品目录已切换；参考图版本保留为制作历史。

## 标识处理

三件硬件统一使用自行绘制的三条错位短线图案、项目 `COLD STEEL` 字样与 `CS` 编号：显卡 `CS-G3`、内存 `CS-D4`、固态硬盘 `CS-S2`。内存正面与背面、显卡轴心与侧牌、SSD 长条标签、芯片丝印和电路板小字均使用项目文字。参考图片中的品牌、系列字样、厂商零件编号和产地标记已从当前三件资产的生成图案中替换。

网卡、机械硬盘、处理器、RAID 控制器和计算加速卡沿用已有 CS / 设施设备标识。历史照片与旧版源文件保留；旧品牌参考模型目录已移出显式 AlwaysCook 清单。此次处理针对资产上的图案和文字，不作商标检索或法律结论。

## 显卡新增结构

- 复合曲面扇叶按弦向形成厚薄变化；轮毂增加独立的嵌入式原创标牌及环形压边。
- 银灰护罩增加实际凹槽装配缝、沉头固定件与环形垫圈；侧面身份牌有独立承托板。
- 风扇电机下方增加四股包覆线、支架线扣、侧面汇集线束及四针插座。
- 显示接口区分一组双肩斜切外壳与三组单角斜切外壳，并补充绝缘舌片、金色接点和固定弹片。
- 供电口增加卡扣、锁止唇和四个小型检测端子；散热管末端增加封口，背板增加压筋，安装耳有贯通孔。

保留三风扇布局、银灰与石墨黑材质组合。使用金属、涂层、塑料、焊锡、阻焊层、镀金触点和印刷标签各自的粗糙度及金属度。

| 物品 | 实际尺寸 cm | 导出三角面 | 占格 | 背包图标 |
| --- | --- | ---: | --- | --- |
| 显卡 | 32.45 × 11.94 × 5.12 | 118,706 | 3 × 2 | [PNG](../../Content/ColdSteelData/Icons/ServerOriginalMarks20261013/search_graphics_card.png) |
| 内存条 | 13.40 × 3.33 × 0.80 | 11,330 | 1 × 1 | [PNG](../../Content/ColdSteelData/Icons/ServerOriginalMarks20261013/search_ram_module.png) |
| SSD | 8.01 × 2.20 × 0.27 | 7,808 | 2 × 1 | [PNG](../../Content/ColdSteelData/Icons/ServerOriginalMarks20261013/search_ssd.png) |

## 文件和接入

制作源位于 [SourceAssets/ServerOriginalMarks20261013](../../SourceAssets/ServerOriginalMarks20261013)，包含可编辑 Blender 文件、FBX、GLB、BaseColor / ORM / Normal 图集和脚本。三件各一个材质槽、4K 图集、简单 UCX 碰撞，保留原物品 ID、占格、价值、稀有度与堆叠设置。显卡最终 UE 网格为 `SM_Search_TripleFanGPU_CSR3C`，几何沿用 `CSR3B` 导出文件；C 版本使用 UE 重建切线，保留导入的分裂法线。

最终活动资产包含三件网格、三个材质及九张纹理。背包图标来自同批实际模型的透明背景渲染。已有物品快照通过既有存档加载迁移读取当前目录外观；本次 Editor 与 Game 后台构建均成功。重新启动游戏并加载存档后才会应用旧实例外观更新。

导入执行成功，但显卡 FBX 仍报告两条近零切线／副法线警告；最终网格已启用 UE MikkTSpace 重建切线，未运行游戏判断其实际显示。没有打开 UE 图形编辑器、运行测试或追加验收预览，由用户测试。

交付状态见 [delivery.json](../../SourceAssets/ServerOriginalMarks20261013/delivery.json)，资源落盘记录见 [installation.json](../../SourceAssets/ServerOriginalMarks20261013/Receipts/installation.json)，目录引用见 [publication.json](../../SourceAssets/ServerOriginalMarks20261013/Receipts/publication.json)，构建结果见 [native-build.json](../../SourceAssets/ServerOriginalMarks20261013/Receipts/native-build.json)。
