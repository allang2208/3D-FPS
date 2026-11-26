# 东门马厩 2026-11-26/27 综合迭代与整理发布（R45–R54）

本批延续 [2026-11-25 东门马厩发布](../HillsVillageStable20261125/README.md)，公开 2026-11-26 至 2026-11-27 对东门马厩、战马运动与贴地、UI 交互抽屉、管理员小屋与陈列马、照明与道路 PCG、4 件 3A 蒙皮马具、20 项随机词条与马匹空间背包、永久解散转移以及马厩防卡阻原地踏步的全部原创源码、制作配方、原创 PNG 图标与 SKILL 沉淀。

## 发布范围

1. **源码真源（直接合入 `Source/FPSGAME/`）**：
   - 马厩/坐骑专属 C++ 32 份（含新增 `StableHorseAffixes.h`、`StableMarketShowcaseSubsystem.h/.cpp`、`ColdSteelMarketCardStyle.h`，以及更新后的 `StableRidingHorse`、`StableHorseGroundMesh`、`StableHorseFollowing`、`StableHorseGear`、`StableHorseTraits`、`HorseRosterTypes`、`HorseRiderComponent`、`ColdSteelMount*`、`SColdSteelHorseMarket`、`SHorseMarketPlate`、`HorseMarketCardsReviewCommandlet`）。
   - 与公共主线无并行交织的 23 份共享源码与地形数据（战斗光环、联机 `MountRelease`/共享掉落/孤儿马匹背包保护、人物面板光环浮窗、变行马匹背包容量缓存、`FPSBodyGrounding` 玩家台阶防抖、前院高度场与道路 PCG 跟随表等）。
   - 其余 10 份与本地并行工作（火把/焚化/强化/伐木场/瞬步等）存在多版本前置交织的共享宿主文件，按工程规范以带 `origin/main` 基线与源码摘录的定向接入清单保存于 [Integration/](Integration/shared-host-hooks.md)，未把未验收并行功能夹带进公开主线。
2. **制作与导入配方（`Tools/WorldGeneration/VillageStable/` 与 `ForestVillage/`）**：
   - 新增与更新 20 份 Python 脚本，涵盖前院细化（R45）、无扭曲奔跑/步行解剖求解与重导（R47）、管理员小屋与陈列马安装（R49）、栏间照明与零穿模校验（R50）、道路主体 PBR 与 PCG（R51）、4 件 3A 蒙皮马具建模/贴图/导入/D3D12 审计（R52/R52b）以及 20 枚冷钢词条图标生成器（R53）。
3. **原创图标与物品目录**：
   - `Content/ColdSteelData/Icons/HorseTack/stable_*.png`（4 张 Cycles 棚拍 512×512 透明底马具图标）与 `Content/ColdSteelData/Icons/HorseAffixes/*.png`（20 张代码生成 256×256 词条图标）；对应 `.uasset` 保留本机。
   - `Content/ColdSteelData/items.json` 仅更新 4 条 `stable_*` 马具条目（售价、套装归属与世界网格路径）。
4. **沉淀 SKILL**：
   - [mounted-view-and-resident-gaze.md](../../../skills/ue5-cpp-gameplay/references/mounted-view-and-resident-gaze.md)（同步 `_shared`）：凹凸地形防东倒西歪、蒙皮坐骑装备与 `CPD` 遮蔽、2D 脊柱走廊防原地踏步。
   - [roster-cards-and-equipment-detail.md](../../../skills/ue5-ui-umg-slate/references/roster-cards-and-equipment-detail.md)：卡片高亮/详情侧栏滑出解耦、变行附属空间背包与容量缓存、词条浮点舍入与图标缓存。
   - [server-authority-receipts.md](../../../skills/ue5-multiplayer-netcode/references/server-authority-receipts.md)：确定性词条与零堆分配缓存、权威名册覆盖孤儿马袋保护、永久解散原子转移与纯本地陈列实体联机边界。

## 本地内容依赖（不随公开 Git 再分发）

- UE 正式资产包（`.uasset` / `.umap`）：`/Game/WorldGeneration/TemperateHills/VillageStable/{Horses,PropsR43,HorseTackR52,GroundDetailR4}`、`/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap` 及 `/Game/ColdSteelData/Icons/{HorseTack,HorseAffixes}/*.uasset`。
- 高模母版、2K PBR 源贴图与 FBX：`SourceAssets/HillsVillageStable/{PropsR43,HorseTackR52}`（`.blend`、`.fbx`、`.png`）与 `F:/FPSGAMEData/ArtProduction/HillsVillageStable/{PropsR44,ForecourtR45,HorseGaitsR47,StablePolishR49,StableLightsR50,StableRoadPCGR51,HorseTackR52,HorseAffixAndBagR53,HorseAntiStuckR54}-20261126/` 下的 `Before/` 回退包与 `published.json`。

## 验证与未测边界

- **已完成自动化验证**：R47/R48/R51/R52b 均通过 `FPSGAMEEditor Win64 Development` 编译与 `HorseGroundContactReview`（20,736 帧 + 116 帧 59° 骑乘冲坡，0 穿地）；R53/R53b 通过 `FPSGAMEEditor Win64 Development`（`BUILD_EXIT=0`）与 D3D12 离屏 `HorseMarketCardsReview`（`REVIEW_EXIT=0`，6,000 样本 20 词条+图标、`多面手`/`战马`/`灵驹`/`身经百战`、0/2/4/6/8 排边界、孤儿校验拦截与满包仓库转移）。
- **R54 编译状态**：本批新增的 3 份源码（`StableRidingHorse.h/.cpp`、`StableHorseFollowing.cpp`）均 0 错 0 警编出 `.obj`；整库 `UnrealEditor-FPSGAME.dll` 最终链接因工作区并行任务的 `WitchRebuiltMonster.cpp` 未定稿暂缓，本公开提交不包含该无关文件。
- **未实机测试**：所有批次均按后台交付规则未启动交互式编辑器或双端 PIE 试玩，实机手感与真双端联机待用户验证。

## 清理归档

- 182 份本次迭代产生的检测截图、GIF、对比图、构建/复核日志、Blender 自动备份（`.blend1`）及 R52 退役刚性马具 FBX（合计 91.23 MB）已逐文件核对 SHA-256 移入本机 `trash`（`F:/FPSGAMEData/trash/HillsVillageStable-20261127/` 与 `D:/FPS3D/FPSGAME/trash/HillsVillageStable-20261127/`），摘要见 [cleanup-summary.json](cleanup-summary.json)，逐文件散列清单保留于本机 `F:/FPSGAMEData/ArtProduction/HillsVillageStable/CloseoutR54-20261127/cleanup-manifest.json`。
