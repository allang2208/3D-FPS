# 双手武器钢材与旋风外观恢复

斩马刀 V3 是大马士革钢的外观基准。9 把可安装该改造的武器共用钢纹场，曲刃按刃线弧长铺纹，战锤按锤面朝向投影。魔晶双手剑使用自己的晶体材质。装备实例 ID 决定钢纹，改造预览、手持和旁观者使用同一种子。旋风换装后，角色恢复当前装备的常态材质。

## 制作与恢复

- [通用钢材制作源](../../../SourceAssets/SharedTwoHandMaterials20261101)保存活动材质清单、斩马刀 V3 着色参数和恢复配方。锻钢双手剑通过[专属表面制作器](../../../SourceAssets/ForgedSteelGreatsword20261120/CommonMods/install_surface.py)接入。符文剑使用陨铁、时砂秘金各自的 V2 配方。斩马刀的七个旋风材质通过[普通刃面配对恢复](../../../SourceAssets/ZhanmadaoDamascus20261111/temporal_finishes.py)。
- 在隔离制作宿主中运行 [重建入口](../../../SourceAssets/SharedTwoHandMaterials20261101/rebuild_registered.py)。按 [材质配对表](../../../SourceAssets/SharedTwoHandMaterials20261101/damascus-v3-surfaces.json) 准备普通表面与依赖；待重建的九个旧旋风包在隔离宿主中留空，制作器会从各自的普通表面生成新包。已升级的宿主可以直接复用现有包。
- [正式包清单](packages.json)按 UE 包名列出 52 个最终材质及其改前、改后 SHA-256。恢复整套外观还需要对应的原厂模型、普通与旋风材质、符文及贴图依赖，维持原有的 `/Game/Weapons` 和 `/Game/Skills` 路径。公开仓库存放制作配方、参数和运行时源码。正式 UE 包、原始模型与编译产物保存在本机资产库。
- 工程入口的 `Content/` 指向 `F:/FPSGAMEData/Content/`。本批原包与发布回执位于 `F:/FPSGAMEData/ArtProduction/SharedTwoHandMaterials/` 下的 `DamascusV3-20261122`、`ZhanmadaoTemporal-20261122`、`AzureNative-20261122`。三个符文剑材质有两级回滚，先撤销专属钢材恢复，再撤销通用大马士革。按各批回执中的哈希区分版本。

## 历史检查与本机归档

完整本机工程的游戏、编辑器目标已于材质制作期间编译成功。4,474 种组合的 121,068 项绑定检查和 73 项旋风专项检查均为零失败。9 把武器的原厂表面以及锻钢的镂空、处刑剑身有同机位离屏对照。旁观者检查在进程内重建装备描述，未运行真实双端联网。本次整理只检查发布内容与归档完整性。

检测图、中间导出、临时宿主及其构建产物已转入 `F:/FPSGAMEData/trash/SharedTwoHandMaterials-20261122/`。其中 `inventory.json` 记录原路径、归档路径、大小、SHA-256 和保留的替代物，`cleanup-manifest.json` 登记移动后的校验与回滚包。制作证据和正式包的本机总入口位于 `F:/FPSGAMEData/ArtReviews/SharedTwoHandMaterials/AllFinishes-20261122/summary.json`。
