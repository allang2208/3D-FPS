# 丘陵村工匠与酒馆的本机资产恢复

源码提供运行入口和制作配方。恢复 UE 内容时，在有相应素材使用权的机器上备齐下表输入，再恢复角色和村庄子关卡。表中路径相对 FPSGAME 工程根目录，`/Game` 对应 `Content`。

| 恢复对象 | 所需本机输入与接入位置 |
| --- | --- |
| Jason 强壮版 R4 母版 | 原版 Jason 身体、骨架与材质来自 `/Game/AsianMale_Jason`。R4 可编辑源为 `SourceAssets/JasonStrong20261117/R4_PoseRefined/Jason_StrongTall_R4.blend`，同目录 `variant_saved.json` 记录母版、骨架和修正图。重新制作时，`Tools/JasonStrongVariant/r4_save.py` 还读取 R3 身体与 R4 的形态输入；直接恢复成品时保留 R4 身体和绑定的后处理蓝图。 |
| 铁匠与木匠 | 两人的身体、呼吸与铁匠工作服从 `Content/Characters/VillageBlacksmithNPC20261118` 恢复，木匠头和工装从 `Content/Characters/VillageCarpenterNPC` 恢复。保留铁匠的 `BodyOutfit/ABP_Smith_R4_Correctives`、两套头发/皮肤/布料依赖和原生骨架。铁匠修订作者源在 `SourceAssets/VillageBlacksmithNPC20261118/FinishR2`，木匠源在 `SourceAssets/VillageCarpenterNPC/Head` 和 `Outfit`。 |
| 村庄与酒馆 | 村庄子关卡为 `/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage`。恢复原有 Normandy 构件、木匠地板与铁匠铺木料，再恢复 `Content/WorldGeneration/VillageTavern` 中的家具、牌、灶与烟道、厨房隔断、备菜洗涤台、碗筷和勺；食品陈设还用到既有食物网格，火光复用既有灯火材质。柜台对应本批的 `SM_TavernCounter`。房壳与窗见 `Tools/WorldGeneration/AbandonedVillage/tavern_shell.py`，陈设制作源见 `SourceAssets/HillsVillageTavern`。两态模型的引用、阻挡标记和在室内的安装位置以 `FHillsTavernInterior` 为准。 |
| 商店图标与教学 | 恢复 `Content/ColdSteelData/Icons` 中实际售卖装备的目录 PNG，包括 `ue_frost_crystal_sword.png`。工坊另需原有锻造与木工配方及候选物品资产。背包、商店和实际工作台分别读取这些输入。 |

原版人脸、原生骨架、Meshy 原件、密集形态/蒙皮数据、纹理、UE 包及正式存档均从合法本机来源恢复。共享身体的运行部件见 `FVillageArtisanAppearance`。带实景引用的村庄仍需恢复其上游资产；本清单未重新构建或运行公开检出。
