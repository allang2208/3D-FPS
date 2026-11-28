# 丘陵村防 · 智能机枪塔、引雷塔、热油与工坊—塔楼融合 · 2026-11-28

本批收录 2026-11-26 至 11-28 对话产出：符文引雷塔、智能机枪塔（16 款主战长枪挂载、工坊第 5 设施 54 阶升级、冷钢挂载抽屉）、城防设施多人伤害浮字、热油锅持锅／火海与模型升级、工坊升级面板改版、冷钢金色脉冲滚动条、高墙内扩 1/3、机械工坊与东门塔楼一体化去穿模、工坊麻绳白模修复，以及本轮联机与性能审查修复。

## 1. 本批公开内容

- **独立 C++ 模块（整文件）**：`AVillageSmartTurret`、`SSmartTurretDrawer`、`ColdSteelScrollBar`、`AVillageLightningSpire`、`UVillageOilArmsMeshComponent`、`VillageOilArmSolver`、`VillageSiegeUpgrades.h`、`VillageDefenseCombat`、`VillageSiegeControl`、`VillageSiegeEngine`、`VillageOilCarry`、`VillageOilFireFront`、`SSiegeWorkshopMarket` 等，及配套 `VillageSiegePreviewTests.inl`（`FPSGAME.Village.Siege` 4 项）。
- **小幅宿主补丁（整文件，差分全部来自本对话）**：建造／放置（`VoxelBuild*`、`VillageBuildDefense`、`VillageDefenseFootprint`）、弹道与特效（`FPSBallisticsComponent`、`FPSWeaponEmission`、`FPSWeaponFXComponent`）、`RangedAttackQuery`、各面板滚动条接入等。
- **制作脚本**：`SourceAssets/HillsVillageHighWall20261120/{SmartTurret,LightningSpire,HotOil,GarrisonWorkshop}/*.py|*.ps1`、`Tools/WorldGeneration/HighVillageDefense/{curtain_wall.py,chapel_gatehouse.py,author_siege_range_indicator.py,Publish-ChapelGatehouse.ps1}`、`Tools/WorldGeneration/MasterArtisan/workshop_plates.py`。生成的 `.meshzip`、贴图 PNG 与 UE `.uasset` 不随公开 Git 再分发。
- **共享宿主文件**：与并行分支交叉的文件只登记接点，见 [Integration/shared-host-hooks.md](Integration/shared-host-hooks.md)。

## 2. 本轮联机与性能审查修复（2026-11-28）

- 机枪塔每发不再改写复制结构体 `MountedWeapon.Magazine`；`OnRep_MountedWeapon` 按 `InstanceId|Definition|Data` 指纹防重建枪模；换弹改为一次性复制 `ReloadEndServerTime` / `ReplicatedReloadDuration`。
- 记录挂载者 `MountedOwnerPawn` / `MountedOwnerState`，打爆／拆除／坍塌 `BeginFall`／`EndPlay` 四处退回原主（客机阵亡期间经 `ShadowModel`），再兜底掉落。
- 客机射击补本地射线曳光，音效与光学态缓存；服务端缓存村庄世界、武器数值和目标骨骼，非开火帧 LOS 限频 `0.10 s`，空置炮塔 `0.25 s` 低频 Tick。
- 城防浮字覆盖野生动物与秒杀目标；挂载抽屉实时栏脏检查；金色滚动条专服跳过并按祖先链可见性与几何尺寸门控。

## 3. 本地内容依赖与验证

- UE 资产已在本机发布：`/Game/WorldGeneration/TemperateHills/{HighVillageDefense/SmartTurret,HighVillageDefense/LightningSpire,HotOil,VillageMechanicalWorkshop}/`；最近两次工坊发布回执与 `Before/` 恢复包位于本机 `F:/FPSGAMEData/ArtProduction/HighVillageDefense/GarrisonWorkshop-{TowerMerge-20261127,RopeFix-20261128}/`。
- 本机全量工作区 `FPSGAMEEditor Win64 Development` 编译成功；`FPSGAME.Village.Siege` 4/4 通过；`TemperateVillageCheck -DefenseBlocks -BuildParity` 207 项通过（2 项既有 `Stone gate` 用例未改）。
- **未实机验证**：双人 Listen/Dedicated PIE（客机挂枪、坍塌退枪、客机曳光）与工坊麻绳实机近景。

## 4. 清理归档

本对话一次性脚本、无头日志与隔离存档、审图截图与概念图、`ArtReviews` 媒体文件及发布宿主 `Saved/Intermediate` 共 `685` 个文件（`312.05 MB`）已逐文件 SHA-256 校验移入 D 盘 `trash/VillageDefenseTurretWorkshop-20261128/` 与 F 盘 `F:/FPSGAMEData/trash/VillageDefenseTurretWorkshop-20261128/`；`Before/`、`published.json`、结构化 JSON／日志与全部目录联接保留。公开摘要见 [cleanup-summary.json](cleanup-summary.json)，逐文件清单在本机 `F:/FPSGAMEData/ArtProduction/HighVillageDefense/Closeout-VillageDefenseTurretWorkshop-20261128/cleanup-manifest.json`。

## 5. 沉淀 SKILL

- [挂载物品的城防设施联机同步](../../../skills/ue5-multiplayer-netcode/references/mounted-item-defense-facility-sync.md)
- [冷钢金色脉冲滚动条与实时面板脏检查](../../../skills/ue5-ui-umg-slate/references/gold-pulse-scrollbar-and-live-panels.md)
- [附属建筑贴合共享预制件](../../../skills/ue5-pcg-building/references/annex-joined-to-shared-prefab.md)
- [程序化麻绳](../../../skills/asset-model-workflow/references/procedural-braided-rope.md)
