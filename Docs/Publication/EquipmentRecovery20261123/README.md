# 11 月装备恢复与高倍镜成像

本批对应 10 月 26 日至 11 月 20 日的 58 条发布记录，以及 11 月 21–22 日写回正式工程的修复。[发布逐项核对和 M249 单列结果](release-audit.json)保留现用替代、原件恢复、配方重构与仍缺项的区别。[本地文件指纹](local-inputs.json)登记可编辑源、清单和证据 ZIP。

| 功能 | 恢复时使用的版本和入口 |
| --- | --- |
| 山脊靴与袍摆 | N005–N012 按旧包名重构，Jason 和 Kaitlin 沿用各自的袍摆靴。见[八个槽的记录](../../../SourceAssets/ModernTacticalSet20261113/RidgeBootsR2/Wear/robe-hem-recovery-20261121.json)。 |
| 普通斧刃 | 三款早期 R2 有配方重构件，初版 15 项保留缺项。轻型钩月现用原厂表面修订，宽月牙、短后钩及一道浅叶脊见[制作源](Recipes/OneHandAxe/SwiftCrescentFactoryFinish20261122)和[安装记录](Receipts/SwiftCrescentFactoryFinish20261122/installed.json)。重劈三方向概念图仍待定稿。[R2 记录](../../../SourceAssets/OneHandAxe20261101/BladeVariants20261102/HistoricalRecovery20261121/recovery.json) |
| 高地双手剑 | 刃根与护手接头、重刃四个材质槽按[接头回执](Receipts/HighlandClaymoreJunction20261121/installed.json)恢复。普通柄与长柄使用[V85/R6b 检视](Receipts/HighlandInspectR6b20261121/installed.json)。退役剑首和护手仍有 27 项历史缺件。 |
| 雷神之锤 | 贯雷锤座使用 V13，重击蓄力沿用 V6 的连续握柄举锤，投出随挥沿用 V7。改造详情只列直接属性和专属机制。[恢复与卡片回执](Receipts/RecoveryAndCopy20261121/delivery.json) |
| 主手手枪与副手 | 整组拔枪和已持枪时新增副手分别进入对应动作。斧头从镜头下方举起；弯刀使用复原的左腕与刀体配合。[弯刀](Receipts/PistolEquipRecovery20261121/delivery.json) · [斧头](Receipts/PistolHatchetRaise20261121/delivery.json) |
| 双手锤和破军 | 普通锤与破军采用 V8 柄尾打击，尖刺锤座采用 V7 前刺及 Rhythm V2 节奏。监听房主、客机和旁观者按动作身份取样。[节奏与配套资源](Receipts/PojunAndConical20261121/delivery.json) |
| M249 | 从 [11 月 9 日基础包](../M24920261109/README.md)和 [11 月 12 日增量](../Conversation20261112/README.md)恢复。现役枪匠条目含七个配件槽，286 个包按各自的原件、重制或版本替代情况登记。[逐包清单](Receipts/ApprovedRecovery20261121/recovery.json) |
| 星律腰带与骨架枪托 | 腰带掉落件沿用 KeeperFixR2。SVD、SVCh 分别按枪身接头和水平轴做 VisualFitR2。[腰带](Receipts/BeltAndSniperStocks20261122/installed.json) · [两个枪托](Receipts/VisualFitR2_20261122/installed.json) |
| 高倍镜与热像 | 分划随镜体移动，缩放只改变镜内景物。弓镜保留绿色，1–6× 恢复红色荧光细十字；热像分别呈现地形、怪物和火源。第三人称装备读取开镜前的原材质。见[按镜型的制作说明](../../../SourceAssets/SharedPhysicalOptics20261030/README.md)和[正式构建回执](Receipts/OpticsHammerNetworkFix20261122/installed.json)。 |

## 取回与整合

[共享源码清单](native-integration.json)给出每份补丁的工程目标、生产基线位置及补丁前后的 LF SHA-256。补丁从工程根应用，先对照基线并运行 `git apply --check <补丁>`。角色、界面和武器共用宿主在公开分支与生产工程间存在版本差异，标为 `patch` 的条目需与对应生产基线合并。独立热像火源筛选、瞳距和副手举斧轨迹已写入可直接更新的正式源码路径。

[枪匠与近战配置字段](catalog-fields.json)按装备和选项 ID 列出 81 个字段，M249 单独恢复了完整枪匠条目。[配方位置表](recipe-locations.json)给出外置作者脚本及其配套数据原目录，使用时还需对应的本机模型、贴图与 UE 宿主。弯刀的 56 帧左腕样本可在包含原动画的制作宿主中用 [pistol_kukri_wrist.py](../../../SourceAssets/OffhandBladeDraw20261104/pistol_kukri_wrist.py) 的 `export(output)` 生成，目标为 `Source/FPSGAME/Weapons/Kukri/PistolKukriDrawWrist.h`。弯刀反向旋风的编辑器工具描述保存在本机，其校验值见原件清单。构建记录对应 11 月 22 日的本地正式 DLL，本次整理仅检查归档和发布内容。

## 退役文件

每个移入 trash 的文件都有原路径、目标、大小、SHA-256、原因和保留替代物。截图、录制检查副本、缓存及已交付的暂存件见[仓库内逐文件恢复清单](archived-files.jsonl)、[路径根目录与分类表](cleanup-summary.json)及[本机完整路径清单](F:/FPSGAMEData/ArtProduction/StorageLayout/EquipmentRecovery-20261123/archive-manifest.jsonl)。正式资产、可编辑原件、发布回执及不同版本的回退文件继续保留在原功能目录。
