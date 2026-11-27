# 林间伐木场运营升级、方案 A 补给路线特效与可乘载马车专项交付（`LumberMillOps-R58 ～ R62`）

本批公开 2026-11-27 至 2026-11-28 围绕 `L_ForestPathVillage` 伐木场日常作业、工装腋下水密修复、M 键补给路线特效（方案 A 冷钢鎏金丝流）、酒馆东侧泊车/开关门/坐姿以及运木马车可站人随车乘载与联机性能收口完成的全部独立代码、制作脚本、沉淀 SKILL 与清理摘要。

---

## 1. 公开交付范围

1. **可站立乘载运木马车与双端零抖动同步（`R62`）**
   - `Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.{h,cpp}`：以 9 组挂于 `WagonRoot` 的定名 `UBoxComponent` 替换粗盒碰撞（空车床面 `Z=95 cm` / 满载原木顶 `Z=156 cm` 含装木自动托升与东门铁闸净空、两级尾步台阶 `36/72 cm`、`SideGuardL/R` 护栏），配 `TG_PrePhysics` + `AddTickPrerequisiteActor`、`180°` 掉头局部随转 + `SaveBaseLocation()`、客机速度前馈 + PD 纠偏、首包对齐、`12 Hz / 1 Hz` 动态同步频率与停靠零采样。
2. **伐木工 NPC 曲柄刚性握持、木桩裂柴、锯木藏锯与客机平滑同步（`R58 ～ R62`）**
   - `Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.{h,cpp}`、`LumberjackAnimInstance.{h,cpp}`、`LumberMillSupplyRoute.h`、`Tasks/LumberMillQuestTypes.h`：唯一刚性 `AxeInHandR * HandRWorld` 曲柄绑定、全员 `BodyMesh` 槽位 `0/3` `M_Smith_Covered` 遮罩、木桩隐藏静态斧并生成两瓣弹落原木（`SM_LM_SplitLog_HalfL/R`）、锯架 HISM 静态拉锯隐藏与恢复、`OnRep_ReplicatedMovement()` 驾车防快照互抢 + 自由步行平滑插值 + 动态 `10/2 Hz`、以及 `LumberMill.R49` 院落缓存。
3. **角色防地面贴花覆盖（`R58`）**
   - `Source/FPSGAME/Characters/FPSPlayerFirstPersonBody.cpp`、`FPSPlayerBodyComponent.cpp`、`FPSModularOutfitComponent.cpp`：统一补齐 `SetReceivesDecals(false)`，根治木桩木屑贴花投影到玩家鞋腿的问题。
4. **完整离线制作工具链（`R49 ～ R61`）**
   - `Tools/WorldGeneration/ForestVillage/` 下全部 16 份伐木场/马车/动作/工装修复与酒馆坐姿制作脚本（含 `build_lumber_split_log_r58.py`、`repair_lumber_workwear_r59.py`、`bake_workwear_r59.py`、`author_lumber_ops_r60.py`、`repair_master_artisan_workwear_r60.py`、`bake_master_artisan_r60.py`、`author_tavern_sit_r61.py`）。
5. **共享宿主集成说明（未夹带并行未合并会话代码）**
   - `Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.{h,cpp}`、`LumberMillQuestSubsystem.{h,cpp}`、`SColdSteelWorldMap.cpp` 及 `TemperateHillsWorld` / `ColdSteelPlayerState` / `ColdSteelStatusModel` / `VillageDefenseGate` / `HighVillageDefense` / `HillsNightRaidSubsystem` 因与本机并行进行的采石场（`QuarryCamp-R1`）、全村交互门（`VillageDoorsR1`）及仓库重构共享文件，其完整接入挂点记录于 [Integration/shared-host-hooks.md](Integration/shared-host-hooks.md)，严格遵守 `WORKFLOW.md` §7–§8 不夹带并行未收口分支。
6. **沉淀 SKILL（4 项高复用规范）**
   - [连续工装腋下修复与水密门禁](../../../skills/ue5-clothing-workflow/references/workwear-armpit-abduction-repair.md)（接入 `ue5-clothing-workflow`）
   - [3P NPC 曲柄工具刚性绑定、PCHIP 挥动与实测家具坐姿](../../../skills/ue5-fps-arms-animation/references/npc-curved-tool-grip-and-furniture-sit.md)（接入 `ue5-fps-arms-animation`）
   - [Slate GPU 自定义顶点丝带与冷钢地图路线](../../../skills/ue5-ui-umg-slate/references/slate-custom-verts-supply-route.md)（接入 `ue5-ui-umg-slate`）
   - [可站立移动载具与随车 NPC 双端零抖动同步](../../../skills/ue5-multiplayer-netcode/references/ridable-moving-platform-and-npc-sync.md)（接入 `ue5-multiplayer-netcode`）

---

## 2. 本地内容依赖与构建/验证状态

- **UE `.uasset` 二进制资产（不随公开 Git 再分发）**：由上述 Python 工具链生成并已在本机原子发布至 `/Game/ForestPathStudy/VillageRegion/LumberMill/` 与 `/Game/Characters/{VillageCarpenterNPC,VillageMasterArtisan,VillageBlacksmithNPC20261118}/`（`+0.00 MB` 显存增量）；全部改前 SHA-256 回滚原包与 `published.json` 回执保留在本机 `F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R{58,59,60,61}/`。
- **编译与二进制核验**：本机全量工作区已于 `2026-11-27 23:20:59` 零错零警通过 `FPSGAMEEditor Win64 Development` 编译与链接（`BUILD_EXIT=0`，`UnrealEditor-FPSGAME.dll` `58.81 MB`，已二进制确认 R60/R60b/R61/R62 全部新增符号落盘）。
- **验证边界**：遵循全局默认后台开发规则，本次未启动 UE/PIE 实机试玩，状态标记为 **未实机测试 · 待 Y 盘 NAS 备份**。

---

## 3. 冗余与一次性文件清理归档

本次会话产生的全部一次性探针/审图/测试脚本、`kimodo` 探索输出、诊断截图、方案 B 废案参考图、R59–R61 无头重试日志、临时 Stage `Saved/Intermediate` 与 R59 临时 DDC（共 **`746` 个文件、`391.67 MB`**）已逐文件通过迁移前后双 SHA-256 校验移入隔离区（D 盘 `trash/LumberMillOps-20261128/` 与 F 盘 `F:/FPSGAMEData/trash/LumberMillOps-20261128/`），所有目录联接与 `Before/` 回滚备份均完好保留；公开摘要见 [cleanup-summary.json](cleanup-summary.json)，完整逐文件散列还原清单位于本机 `F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillCloseout-20261128/cleanup-manifest.json`。
