# 收集物图标朝向

> 本页旧图、原图备份及已被替代的批量脚本已移入 `trash/search-collectibles-20261013`；当前R2批次及归档映射见 [整理发布](../Publication/SearchCollectibles20261013/README.md)。本页保留当时规则与制作证据。

> 此页保留最初左上 45° 版本的记录。当前采用 [条状物居中与显卡 2×1](collection-icon-layout-r2-20261013.md)，宽幅物品恢复原背包图标构图。

2026-10-13。按用户要求统一已制作的收集物图标，适用文件材料、检修材料、机房设备，共 17 件。武器与可穿戴装备沿用原有图标。

默认朝向为屏幕左上 45°：物件主轴从左上延伸到右下。锻造合金坯（1×2）与层压木条（1×3）保持垂直。其他 15 件使用统一的斜向构图。物品占格、价格、稀有度及堆叠数不变，玩家主动旋转背包占格的交互也沿用原规则。

图标直接从当前活动 GLB 模型生成，显卡、内存和 SSD 使用 CS 原创标识版。保留各件已经建立的俯视角与材质灯光；先求主轴在摄像机中的投影，再调整摄像机滚转到统一朝向。按照旋转后的完整边界重新构图，保留 10% 的画幅余量，不拉伸物件。

统一制作函数为 [collection_icon_orientation.py](../../Tools/AssetPipeline/collection_icon_orientation.py)，已接入文件材料、检修材料、原始机房设备及新版 CS 硬件的四套制作脚本。此次交付批次使用当前物品目录对应的模型，避免重新使用已经替换的参考品牌版本。

PNG 安装到既有 `Content/ColdSteelData/Icons` 路径，物品目录和旧存档中的图标路径不变，不需要新增存档迁移或原生构建。游戏已加载的纹理会缓存，重新启动游戏后读取新版图片。

原图保存在 [PreviousIcons](../../SourceAssets/CollectionIconOrientation20261013/PreviousIcons)，本轮成品保存在 [Icons](../../SourceAssets/CollectionIconOrientation20261013/Icons)，制作与安装状态记录在 [installation.json](../../SourceAssets/CollectionIconOrientation20261013/Receipts/installation.json)。本次只生成交付用图标；未启动 UE 图形编辑器、游戏或测试，显示效果由用户测试。
