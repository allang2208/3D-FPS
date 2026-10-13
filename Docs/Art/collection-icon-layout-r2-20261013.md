# 收集物图标：按占格居中与显卡 2×1

> 收尾更新：后续搜索池批次已完成包含本次迁移的 Editor/Game 构建；本文末尾的Game阻塞是该制作阶段的历史记录。旧图快照已带散列移入trash，当前恢复链及Git发布边界见 [整理发布](../Publication/SearchCollectibles20261013/README.md)。

2026-10-13。本版替代此前收集物一律左上 45° 的图标规则，覆盖同一批 17 件文件、检修与机房收集物。沿用 CS 原创标识和网卡、阵列卡、处理器的白银黑配色。

## 当前构图

| 构图 | 物品 |
| --- | --- |
| 水平居中（8 件） | U盘、装配组件盒、精密机件组、服务器内存条、服务器网卡、机械硬盘、固态硬盘、显卡 |
| 垂直居中（2 件） | 锻造合金坯、层压木条 |
| 原背包图标构图（7 件） | 档案备份磁带、加密行政资料盒、签章行政档案、树脂胶包、服务器处理器、阵列控制卡、计算加速模块 |

2×1 等单行物品水平摆放，1×2、1×3 等单列物品垂直摆放；1×1 中外形细长的 U 盘和内存条也水平摆放。2×2、3×2 等宽幅物品恢复各自原有的立体展示相机视角。构图保留物件厚度和材质层次，采用正交投影、等比适配和边缘留白。

制作规则集中在 [collection_icon_orientation.py](../../Tools/AssetPipeline/collection_icon_orientation.py)。当前制作批次为 [CollectionIconLayoutR2_20261013](../../SourceAssets/CollectionIconLayoutR2_20261013)，保留本轮修改前的 PNG、制作参数与回执。既有模型图标入口也使用同一函数，U 盘和内存条按实际长宽识别为细长形态。

## 显卡占格

显卡从 3×2 改为 **2×1**，图标画幅从 768×512 改为 512×256，采用水平居中构图。原有三风扇模型尺寸、稀有度、每件 2400 灵魂的售价和堆叠上限不变；设计表每格收益随之更新为 1200 灵魂。

运行目录、设计表和活动模型制作清单均已同步 2×1。旧实例在既有 `MigrateAuthoredGridFootprints` 中迁移：写回 `grid_w/grid_h`，保留旋转方向、物品身份、数量及当前位置；旋转后的显卡占 1×2。原有 A/B 存档读取、背包、夹层和仓库落位流程继续负责提交迁移。本次不直接修改玩家存档文件。

## 接入记录

17 张 PNG 安装到现有正式图标路径；三件白银黑硬件对应的旧图标路径也同步更新。旧图备份位于本批 `PreviousIcons`。原版模型、材质和武器／装备图标未被此轮改动。

图标安装见 [installation.json](../../SourceAssets/CollectionIconLayoutR2_20261013/Receipts/installation.json)，占格变更见 [footprint.json](../../SourceAssets/CollectionIconLayoutR2_20261013/Receipts/footprint.json)，必要构建见 [native-build.json](../../SourceAssets/CollectionIconLayoutR2_20261013/Receipts/native-build.json)，最终交付状态见 [delivery.json](../../SourceAssets/CollectionIconLayoutR2_20261013/delivery.json)。

Editor 后台构建已成功，包含本轮显卡占格迁移。Game 构建遇到现有木工模块的类型声明错误及 `ColdSteelStationNetwork.cpp` 的 `CreateNetworkSession` 参数不匹配，本次保留这些并行源码，独立 Game 二进制尚未更新。

更新后的 Editor 进程在加载存档时执行占格迁移；图标纹理也需要重新启动后加载。未打开 UE 图形编辑器、运行游戏、测试或追加预览渲染，由用户测试。
