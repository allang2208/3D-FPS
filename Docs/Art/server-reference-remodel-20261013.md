# 显卡 内存条 SSD 参考图重制

> 归档更新：本页品牌版本的模型、纹理、导入宿主和脚本已移入 `trash/search-collectibles-20261013/SourceAssets/ServerReferenceRemodel20261013`；原始参考照片保留原位。当前生产恢复使用原创标识版本，见 [整理发布](../Publication/SearchCollectibles20261013/README.md)。

> 此页记录历史参考版本。当前活动版本已按用户后续要求替换品牌图案、细化显卡并更新图标，见 [机房硬件原创标识与显卡细化](server-original-marks-20261013.md)。下文的品牌字样、资产路径和构建阻塞状态均属于当时记录。

2026-10-13。按用户提供的三张参考图重做 `search_graphics_card`、`search_ram_module`、`search_ssd` 的外观，并同步透明背包图标。沿用原物品 ID、稀有度、价值、堆叠数和占格，其他五件机房设备保持原模型。

## 三件重制模型

| 物品 | 新外观与结构 | 实际尺寸 cm | 三角面 | 游戏导出 |
| --- | --- | --- | ---: | --- |
| 显卡 | 三枚大风扇、银灰切面端罩与黑色中框、复合弧面扇叶、轮毂标识、密集鳍片、五根导热管、带开窗的背板、显示接口和凹入供电口 | 32.47×11.94×5.13 | 86,316 | [GLB](../../SourceAssets/ServerReferenceRemodel20261013/Export/SM_Search_TripleFanGPU_RefR2.glb) |
| 内存条 | 黑色 DDR4 散热马甲、阶梯折边、顶部真实开槽、刻线与银白印刷、双面金手指及定位缺口 | 13.40×3.33×0.80 | 11,330 | [GLB](../../SourceAssets/ServerReferenceRemodel20261013/Export/SM_Search_FuryRAM_RefR2.glb) |
| SSD | 80×22 mm 级 M.2 裸板、黑色窄长标签、控制芯片、两侧密集贴片元件、M-key 缺口、双面金触点和半圆安装孔 | 8.01×2.20×0.27 | 8,172 | [GLB](../../SourceAssets/ServerReferenceRemodel20261013/Export/SM_Search_M2SSD_RefR2.glb) |

显卡增加的几何主要用于三组九叶风扇、复合弧面厚度、密集散热结构、开孔护罩与接口。内存面字直接映射到实际散热片表面，避免矩形印刷面跨过开槽；SSD 以板厚、元件高度和标签层次表现薄型硬件。当前交付为 LOD0，未进行性能采样或运行验收。

## 材质与参考还原

三件各使用独立 4K BaseColor、ORM、Normal 图集，区分细砂银灰金属、石墨色涂层、哑光塑料、平滑扇叶、黑色阻焊层、焊锡、镀金触点及标签。金属与非金属采用分别设定的粗糙度和金属度，表面颗粒保持克制；写实细节依靠轮廓、厚度、开口和微表面共同体现。

显卡采用参考图中的三风扇前脸与轮毂标识，内存复现 HyperX、FURY、DDR4 的可见文字布局，SSD 复现 Samsung 990 的长条黑色标签身份。参考图中的商品包装盒不属于拾取物模型。背面和不可见内部按合理硬件结构补全，不宣称逐面精确复刻。用户参考图片保存在 `SourceAssets/ServerReferenceRemodel20261013/Reference`；品牌标识依据该次外观请求制作，未据此推定第三方素材的公开再分发许可。

ORM 通道为 R 环境遮蔽、G 粗糙度、B 金属度；BaseColor 为 sRGB，其他纹理为线性数据。法线源使用 OpenGL +Y，UE 导入翻转绿色通道。源文件为厘米尺度，FBX 按厘米导入，GLB 为米；游戏导出底部居中，每件一个材质槽和 UCX 简单碰撞盒。

## 接入与保留

正式资源采用新目录 `/Game/Items/ServerReferenceRemodel20261013`，以独立包替换目录引用，旧版模型、贴图、图标和制作源保留。目录修改仅涉及三件物品的 `world_mesh`、`ue_icon`、`icon`、`desc`。显卡仍占 3×2、内存条仍占 1×1、SSD 仍占 2×1。

| 物品 | 新版透明背包图标 |
| --- | --- |
| 显卡 | [PNG](../../Content/ColdSteelData/Icons/ServerReferenceRemodel20261013/search_graphics_card.png) |
| 内存条 | [PNG](../../Content/ColdSteelData/Icons/ServerReferenceRemodel20261013/search_ram_module.png) |
| SSD | [PNG](../../Content/ColdSteelData/Icons/ServerReferenceRemodel20261013/search_ssd.png) |

旧实例由 `ColdSteelProfileRuntime.cpp` 在读取存档时同步模型、图标和介绍，保持实例身份、数量、位置与玩法数据。该迁移需要本轮原生构建成功后再读档；当前运行中的游戏不会因目录文件更新自动重建已有物品。精确构建状态见 [交付记录](../../SourceAssets/ServerReferenceRemodel20261013/delivery.json)。

实际制作结果见 [模型清单](../../SourceAssets/ServerReferenceRemodel20261013/model_manifest.json)、[导入回执](../../SourceAssets/ServerReferenceRemodel20261013/Receipts/ue-import.json)、[安装回执](../../SourceAssets/ServerReferenceRemodel20261013/Receipts/installation.json) 和 [引用切换记录](../../SourceAssets/ServerReferenceRemodel20261013/Receipts/publication.json)。本次仅渲染交付所需的背包图标，未生成额外预览、启动游戏或运行测试。

三件静态网格、三个材质和九张纹理共十五个 UE 资源包已保存并安装，后台导入零错误、零警告。Editor 原生构建被现有 `FPSPlayerBodyTypes.h` 的 `GENERATED_BODY` 声明错误 C4430 阻塞，Game 构建随之未执行。本次保留角色模块现有源码；旧档外观迁移已写入源码，尚未交付新的迁移二进制。
