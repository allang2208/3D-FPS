# 共享宿主接点（未整文件发布）

以下文件在本机同时承载本对话与并行分支（马厩 R45–R54 后续、仓库 R2、采石场 `QuarryCamp-R1`、全村交互门 `VillageDoorsR1`、地图与物品浮窗重构等）的未收口修改。按 `WORKFLOW.md` §8 第 3 条，本批**不整文件推送**，只在此登记本对话在其中的接点，合并时按函数名定位。

| 文件 | 本对话接点 |
|---|---|
| `Source/FPSGAME/UI/SColdSteelWorldMap.cpp`、`ColdSteelItemTooltip.cpp`、`ColdSteelItemTooltipLayout.cpp`、`ColdSteelWarehouseHUD.cpp`、`ColdSteelInventoryRules.cpp`、`ColdSteelDungeonTracker.cpp`、`SColdSteelMapMarkerEditor.cpp`、`ColdSteelProfileItems.cpp`、`ColdSteelProfileLoading.cpp` | 滚动区改用 `ColdSteelUI::ApplyGoldScroll(...)` / `ConfigureGoldScrollBox(...)`（`#include "ColdSteelScrollBar.h"`），不改动其余布局与数据逻辑 |
| `Source/FPSGAME/UI/SWarehouseUpgradeMarket.cpp` | 右上灵魂胶囊高度 `28 px` 对齐关闭按钮；升级列表接入金色滚动条 |
| `Source/FPSGAME/UI/ColdSteelCrosshair.cpp`、`ColdSteelStaminaHUD.cpp` | 守备器械操作准星的磁吸／装填／超距着色；器械装填进度沿用体力条上方动作栏 |
| `Source/FPSGAME/UI/ColdSteelHUDConstruction.cpp`、`ColdSteelWorldInteraction.cpp` | 智能机枪塔、引雷塔、热油锅的 E 键提示与可交互判定 |
| `Source/FPSGAME/FPSGAMECharacterInput.cpp`、`FPSGAMECharacterReloadInput.cpp`、`FPSGAMECharacterActionAvailability.cpp`、`Weapons/WoodenTorchComponent.cpp` | 端热油锅期间屏蔽开火／换弹／火把镭射，动作占用沿用现有可用性表 |
| `Source/FPSGAME/WorldGeneration/TemperateHillsWorld.h/.cpp`、`TemperateVillagePlans.cpp`、`NPC/ChapelDialogueComponent.h/.cpp` | `FRanks` 64+64 位工坊等级的存档／复制（`SiegeRanks`、`SiegeExtraRanks`、`GetAllSiegeRanks()`），工坊第 4／5 设施购买路由 |
| `Source/FPSGAME/WorldGeneration/ForestVillageGrassCover.cpp`、`TemperateVillageGround.cpp`、`TemperateVillagePlanting.cpp` | 高墙内扩 `+67 cm` 后的草皮／碎石／种植净空：`FTemperateVillageSite::InsideWidenedHighWallFootprint(Local, Margin)` |
| `Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.cpp` | 静态木屑贴花移位前后临时切换 `EComponentMobility::Movable`（消除 PIE 移动性警告） |
| `Source/FPSGAME/Monsters/FPSCombatHealthComponent.cpp` | 测试世界卸载时的 `EndPlay` 空指针保护 |

以下共享文件只发布了本对话**整块独立**的差分（`hunk` 级选择性应用到 `origin/main`），其余并行改动保留在本机：`Docs/Production/README.md`、`Content/ColdSteelData/items.json`、`Docs/Fluids/village-hot-oil.md`、`Source/FPSGAME/WorldGeneration/VillageMechanicalWorkshop.cpp`、`TemperateVillageSite.h`、`TemperateVillagePerimeter.cpp`、`Source/FPSGAME/FPSGAMEPlayerController.cpp` 及 4 个 `SKILL.md`。选择性差分可能依赖本机未收口的宿主符号；公开主线本身不承诺单独可编译。
